"""RAG query service: embed query → vector search → LLM answer.

Steps:
  1. Embed the user query via EmbeddingsAdapter
  2. Search rag_chunks for top-K most similar chunks
  3. Build a context-enriched prompt
  4. Call the chat LLM and return answer + sources
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

from src.bot.infrastructure.config.settings import Settings
from src.bot.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from src.bot.adapters.driven.db.repositories.rag_chunk_repo_sa import (
        RagChunkRepoSqlAlchemy,
    )
    from src.bot.adapters.driven.llm.embeddings_adapter import EmbeddingsAdapter

logger = get_logger(__name__)

_SYSTEM_PROMPT = (
    "Você é um especialista em peças automotivas. "
    "Seu trabalho é extrair informações precisas dos catálogos fornecidos.\n\n"
    "INSTRUÇÕES:\n"
    "1. Analise cuidadosamente os dados fornecidos\n"
    "2. Identifique o MODELO do veículo (ex: Palio, Gol, Uno)\n"
    "3. Extraia os NÚMEROS DE PEÇA (part numbers)\n"
    "4. Liste as ESPECIFICAÇÕES (ano, motor, tipo)\n"
    "5. Cite a PÁGINA DE ORIGEM quando disponível\n"
    "6. Se a pergunta for sobre um modelo específico (ex: Palio 1.0), "
    "   VERIFIQUE se os dados são realmente para esse modelo\n\n"
    "FORMATO DE RESPOSTA:\n"
    "Modelo: [nome do veículo]\n"
    "Aplicações: [lista de configurações (ano, motor, etc)]\n"
    "Números de peça: [lista de part numbers com especificações]\n"
    "Página: [número da página no catálogo]\n\n"
    "Se a informação não corresponder ao modelo solicitado ou não estiver nos catálogos, "
    "INFORME CLARAMENTE que não foi encontrada."
)


class RagQueryService:
    def __init__(
        self,
        chunk_repo: "RagChunkRepoSqlAlchemy",
        embeddings: "EmbeddingsAdapter",
        settings: Settings,
    ) -> None:
        self._chunk_repo = chunk_repo
        self._embeddings = embeddings
        self._settings = settings

    async def query(
        self,
        query: str,
        *,
        manufacturer_id: int | None = None,
        catalog_id: int | None = None,
        brand: str | None = None,
        top_k: int = 6,
    ) -> dict[str, Any]:
        # 1. Embed the query
        query_embedding = await self._embeddings.embed_text(query)

        # 2. Vector search
        chunks = self._chunk_repo.search_similar(
            query_embedding,
            top_k=top_k,
            manufacturer_id=manufacturer_id,
            catalog_id=catalog_id,
            brand=brand,
        )

        if not chunks:
            return {
                "answer": (
                    "Não encontrei informações relevantes nos catálogos disponíveis "
                    "para responder sua pergunta."
                ),
                "sources": [],
            }

        # 3. Build context string
        context_parts: list[str] = []
        for i, chunk in enumerate(chunks, start=1):
            meta = chunk.get("metadata") or {}
            filename = meta.get("original_filename", "catálogo")
            page = meta.get("page", "?")
            context_parts.append(
                f"[Trecho {i} — {filename}, pág. {page}]\n{chunk['chunk_text']}"
            )
        context_text = "\n\n---\n\n".join(context_parts)

        # 4. Call LLM
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"CONTEXTO DO CATÁLOGO:\n{context_text}\n\nPERGUNTA: {query}"
                ),
            },
        ]
        answer = await self._call_llm(messages)

        # 5. Build source list with brand information
        sources: list[dict[str, Any]] = []
        for chunk in chunks:
            meta = chunk.get("metadata") or {}
            sources.append(
                {
                    "catalog_id": meta.get("catalog_id"),
                    "brand": chunk.get("brand"),
                    "filename": meta.get("original_filename"),
                    "page": meta.get("page"),
                    "chunk_text": chunk["chunk_text"][:500],  # Show more context
                    "similarity": float(chunk.get("similarity") or 0),
                }
            )

        return {
            "answer": answer,
            "sources": sources,
            "total_sources": len(sources),
        }

    # ── private ───────────────────────────────────────────────────────

    async def _call_llm(self, messages: list[dict[str, str]]) -> str:
        s = self._settings
        url = f"{s.LLM_BASE_URL.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {s.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": s.LLM_MODEL,
            "messages": messages,
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(timeout=s.LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, headers=headers, json=payload)

        if resp.status_code >= 400:
            raise RuntimeError(
                f"LLM error {resp.status_code}: {resp.text[:300]}"
            )

        return resp.json()["choices"][0]["message"]["content"]
