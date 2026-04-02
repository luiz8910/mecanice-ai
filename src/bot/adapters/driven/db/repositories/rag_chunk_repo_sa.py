"""SQLAlchemy repository for rag_chunks — insert and cosine-similarity search."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.bot.infrastructure.logging import get_logger

logger = get_logger(__name__)


class RagChunkRepoSqlAlchemy:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── WRITE ─────────────────────────────────────────────────────────

    def insert_chunks(self, chunks: list[dict[str, Any]]) -> None:
        """Bulk-insert chunks with their embeddings (single transaction)."""
        for chunk in chunks:
            embedding_str = "[" + ",".join(str(v) for v in chunk["embedding"]) + "]"
            self._session.execute(
                text("""
                    INSERT INTO rag_chunks
                      (source_id, source_type, chunk_text, embedding, metadata, brand)
                    VALUES
                      (:source_id, :source_type, :chunk_text,
                       CAST(:embedding_array AS vector), CAST(:metadata AS jsonb), :brand)
                """),
                {
                    "source_id": chunk["source_id"],
                    "source_type": chunk["source_type"],
                    "chunk_text": chunk["chunk_text"],
                    "embedding_array": embedding_str,
                    "metadata": json.dumps(chunk["metadata"]),
                    "brand": chunk.get("brand"),
                },
            )
        self._session.commit()

    def delete_by_catalog_id(self, catalog_id: int) -> None:
        """Remove all rag_chunks that belong to a catalog (by source_id)."""
        self._session.execute(
            text("""
                DELETE FROM rag_chunks
                WHERE source_type = 'catalog'
                  AND source_id   = :source_id
            """),
            {"source_id": str(catalog_id)},
        )
        self._session.commit()

    # ── READ (vector search) ──────────────────────────────────────────

    def search_similar(
        self,
        embedding: list[float],
        *,
        top_k: int = 6,
        manufacturer_id: int | None = None,
        catalog_id: int | None = None,
        brand: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return up to top_k chunks nearest to `embedding` (cosine distance).

        Optional filters:
        - catalog_id: restrict to a single catalog
        - manufacturer_id: restrict to catalogs belonging to that manufacturer
        - brand: restrict to a specific brand
        """
        # Convert embedding to SQL array format for pgvector
        # Handle both list of floats and pre-converted string
        if isinstance(embedding, str):
            embedding_str = embedding
        else:
            embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

        where: list[str] = ["rc.source_type = 'catalog'"]
        params: dict[str, Any] = {"embedding_array": embedding_str, "top_k": top_k}

        if catalog_id is not None:
            where.append("(rc.metadata->>'catalog_id')::bigint = :catalog_id")
            params["catalog_id"] = catalog_id

        if manufacturer_id is not None:
            where.append("""
                (rc.metadata->>'catalog_id')::bigint IN (
                    SELECT id FROM catalog_documents
                    WHERE manufacturer_id = :manufacturer_id
                      AND status = 'ready'
                      AND is_active = true
                )
            """)
            params["manufacturer_id"] = manufacturer_id

        if brand is not None:
            where.append("rc.brand = :brand")
            params["brand"] = brand

        where_sql = " AND ".join(where)

        sql = f"""
                SELECT
                    rc.id,
                    rc.source_id,
                    rc.chunk_text,
                    rc.metadata,
                    1 - (rc.embedding <=> CAST(:embedding_array AS vector)) AS similarity
                FROM rag_chunks rc
                INNER JOIN catalog_documents cd
                  ON (rc.metadata->>'catalog_id')::bigint = cd.id
                WHERE {where_sql}
                  AND cd.is_active = true
                  AND cd.status = 'ready'
                ORDER BY rc.embedding <=> CAST(:embedding_array AS vector)
                LIMIT :top_k
            """

        # Log the WHERE clause to debug
        logger.info("RAG where_sql: '%s'", where_sql)
        logger.debug("RAG params keys: %s", list(params.keys()))

        try:
            rows = self._session.execute(text(sql), params).mappings().all()
        except Exception as e:
            logger.error("RAG search failed: %s", e)
            # Print SQL for debugging
            logger.error("RAG SQL was: %s...", sql[:300])
            raise

        logger.info("RAG search returned %d rows (top_k=%d)", len(rows), top_k)
        return [dict(r) for r in rows]
