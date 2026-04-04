"""OpenAI-compatible embeddings adapter.

Calls the /embeddings endpoint and returns lists of float vectors.
Batches requests to stay within provider limits.
"""

from __future__ import annotations

import httpx

from src.bot.infrastructure.config.settings import Settings
from src.bot.infrastructure.logging import get_logger

logger = get_logger(__name__)

_BATCH_SIZE = 100


class EmbeddingsError(RuntimeError):
    """Raised when the embeddings API call fails."""


class EmbeddingsAdapter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts, batching when len > _BATCH_SIZE."""
        if not texts:
            return []
        results: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            results.extend(await self._call_api(batch))
        return results

    async def embed_text(self, text: str) -> list[float]:
        results = await self.embed_texts([text])
        return results[0]

    # ── private ───────────────────────────────────────────────────────

    async def _call_api(self, texts: list[str]) -> list[list[float]]:
        s = self._settings
        if not s.EMBEDDINGS_API_KEY:
            raise EmbeddingsError("EMBEDDINGS_API_KEY não configurada.")

        url = f"{s.EMBEDDINGS_BASE_URL.rstrip('/')}/embeddings"
        headers = {
            "Authorization": f"Bearer {s.EMBEDDINGS_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {"model": s.EMBEDDINGS_MODEL, "input": texts}

        logger.debug("Embedding %d texts with model=%s", len(texts), s.EMBEDDINGS_MODEL)

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)

        if resp.status_code >= 400:
            raise EmbeddingsError(
                f"Embeddings API error {resp.status_code}: {resp.text[:300]}"
            )

        try:
            data = resp.json()
            # Sort by index to preserve order (OpenAI guarantees this but let's be safe)
            items = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in items]
        except Exception as exc:
            raise EmbeddingsError(f"Failed to parse embeddings response: {exc}") from exc
