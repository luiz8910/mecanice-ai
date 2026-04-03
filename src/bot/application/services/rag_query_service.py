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
    "Você é um especialista em peças automotivas que consulta catálogos técnicos.\n\n"
    "INSTRUÇÕES:\n"
    "1. Os dados fornecidos são extraídos de catálogos PDF e podem estar em formato tabular "
    "   compactado (colunas misturadas em uma linha). Interprete com cuidado.\n"
    "2. Identifique SOMENTE informações que correspondam ao veículo/peça solicitados.\n"
    "3. Dados de catálogos Bosch seguem o padrão: Modelo | Motorização | Combustível | "
    "   Código da vela | Gap | Nº Referência | Código Simplificado | Cabo | Bobina\n"
    "4. Dados de catálogos NGK seguem o padrão: Modelo | Motorização | Combustível | "
    "   Código Convencional | Código Iridium | Gap | Anos | Cabo de ignição\n\n"
    "FORMATO DA RESPOSTA (use markdown):\n"
    "**Veículo:** Nome e variante (ex: Fiat Palio 1.0 8V Fire)\n"
    "**Ano(s):** Período de aplicação\n"
    "**Motor:** Código do motor e detalhes\n"
    "**Combustível:** Gasolina / Flex / Álcool\n\n"
    "**Velas de ignição:**\n"
    "| Marca | Código | Tipo | Gap (mm) |\n"
    "|-------|--------|------|----------|\n"
    "| Bosch | FR 6 D+ | Convencional | 0.8 |\n\n"
    "**Cabos de ignição:** código(s) se disponível\n"
    "**Bobina de ignição:** código(s) se disponível\n\n"
    "REGRAS:\n"
    "- Se encontrou dados para o veículo, apresente TODOS os códigos de peça disponíveis.\n"
    "- Se NÃO encontrou dados exatos, diga claramente e sugira o modelo mais próximo encontrado.\n"
    "- NÃO invente dados. Só apresente o que está nos trechos fornecidos.\n"
    "- Responda SEMPRE em português brasileiro.\n"
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

        # 2. Vector search — over-fetch then diversify across catalogs
        raw_chunks = self._chunk_repo.search_similar(
            query_embedding,
            top_k=top_k * 3,
            manufacturer_id=manufacturer_id,
            catalog_id=catalog_id,
            brand=brand,
        )
        chunks = self._diversify_sources(raw_chunks, top_k)

        if not chunks:
            return {
                "answer": (
                    "Não encontrei informações relevantes nos catálogos disponíveis "
                    "para responder sua pergunta."
                ),
                "sources": [],
            }

        # 3. Build context string with catalog metadata
        context_parts: list[str] = []
        for i, chunk in enumerate(chunks, start=1):
            meta = chunk.get("metadata") or {}
            filename = meta.get("original_filename", "catálogo")
            page = meta.get("page", "?")
            brand = chunk.get("brand") or "Desconhecida"
            similarity = chunk.get("similarity", 0)
            context_parts.append(
                f"[Trecho {i} — Marca: {brand} | Catálogo: {filename} | "
                f"Página: {page} | Relevância: {similarity:.0%}]\n"
                f"{chunk['chunk_text']}"
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

    @staticmethod
    def _diversify_sources(
        chunks: list[dict[str, Any]], top_k: int
    ) -> list[dict[str, Any]]:
        """Pick top_k chunks ensuring multiple catalogs are represented.

        Uses round-robin across catalog_ids so results aren't dominated
        by a single large catalog.
        """
        if len(chunks) <= top_k:
            return chunks

        # Group by catalog_id preserving order (most relevant first)
        from collections import OrderedDict
        by_catalog: OrderedDict[int | None, list[dict[str, Any]]] = OrderedDict()
        for c in chunks:
            cat_id = (c.get("metadata") or {}).get("catalog_id")
            by_catalog.setdefault(cat_id, []).append(c)

        # Round-robin pick from each catalog
        result: list[dict[str, Any]] = []
        iterators = {k: iter(v) for k, v in by_catalog.items()}
        while len(result) < top_k and iterators:
            exhausted = []
            for cat_id, it in iterators.items():
                if len(result) >= top_k:
                    break
                chunk = next(it, None)
                if chunk is None:
                    exhausted.append(cat_id)
                else:
                    result.append(chunk)
            for cat_id in exhausted:
                del iterators[cat_id]

        return result

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
