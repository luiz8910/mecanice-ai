from __future__ import annotations

from typing import List
import anyio

from .models import ContextSource
from .settings import settings
from .embeddings import get_embeddings_provider
from .db import search_chunks


async def retrieve_context(user_text: str) -> List[ContextSource]:
    """Retrieve top-k chunks from Postgres+pgvector."""
    embedder = get_embeddings_provider()
    q_emb = await embedder.embed(user_text)

    # search_chunks is sync; run in a thread for FastAPI async safety
    rows = await anyio.to_thread.run_sync(
        lambda: search_chunks(q_emb, top_k=settings.RAG_TOP_K)
    )

    sources: List[ContextSource] = []
    for row in rows[: settings.RAG_MAX_CHUNKS_IN_PROMPT]:
        sources.append(
            ContextSource(
                source_id=row["source_id"],
                source_type=row["source_type"],
                text=row["chunk_text"],
            )
        )
    return sources
