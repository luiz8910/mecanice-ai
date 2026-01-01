from __future__ import annotations

import hashlib
from typing import List
import httpx

from .settings import settings


class EmbeddingsError(RuntimeError):
    pass


class EmbeddingsProvider:
    async def embed(self, text: str) -> List[float]:
        raise NotImplementedError


class OpenAICompatibleEmbeddings(EmbeddingsProvider):
    async def embed(self, text: str) -> List[float]:
        if not settings.EMBEDDINGS_API_KEY:
            raise EmbeddingsError("EMBEDDINGS_API_KEY não configurada.")
        url = settings.EMBEDDINGS_BASE_URL.rstrip("/") + "/embeddings"
        headers = {
            "Authorization": f"Bearer {settings.EMBEDDINGS_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {"model": settings.EMBEDDINGS_MODEL, "input": text}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code >= 400:
                raise EmbeddingsError(f"Erro embeddings: {r.status_code} - {r.text}")
            data = r.json()
            try:
                return data["data"][0]["embedding"]
            except Exception as e:
                raise EmbeddingsError(f"Resposta embeddings inesperada: {e}")


class DummyEmbeddings(EmbeddingsProvider):
    """Embeddings determinísticas para desenvolvimento local (NÃO use em produção)."""

    def __init__(self, dim: int = 1536):
        self.dim = dim

    async def embed(self, text: str) -> List[float]:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Expand hash bytes into dim floats in [-1, 1]
        out = []
        for i in range(self.dim):
            b = h[i % len(h)]
            out.append((b / 255.0) * 2.0 - 1.0)
        return out


def get_embeddings_provider() -> EmbeddingsProvider:
    provider = (settings.EMBEDDINGS_PROVIDER or "openai_compatible").lower()
    if provider == "dummy":
        return DummyEmbeddings()
    if provider == "openai_compatible":
        return OpenAICompatibleEmbeddings()
    raise EmbeddingsError(f"EMBEDDINGS_PROVIDER inválido: {settings.EMBEDDINGS_PROVIDER}")
