from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import psycopg
from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector

from .settings import settings


_pool: Optional[ConnectionPool] = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(conninfo=settings.DATABASE_URL, min_size=1, max_size=5, timeout=10)
    return _pool


def _ensure_vector_registered(conn: psycopg.Connection) -> None:
    # pgvector adapter registration
    register_vector(conn)


def insert_chunk(
    source_id: str,
    source_type: str,
    chunk_text: str,
    embedding: List[float],
    metadata: Dict[str, Any] | None = None,
) -> int:
    pool = get_pool()
    metadata = metadata or {}
    with pool.connection() as conn:
        _ensure_vector_registered(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rag_chunks (source_id, source_type, chunk_text, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                RETURNING id
                """,
                (source_id, source_type, chunk_text, embedding, json.dumps(metadata)),
            )
            new_id = cur.fetchone()[0]
            conn.commit()
            return int(new_id)


def search_chunks(
    query_embedding: List[float],
    top_k: int = 6,
    source_type_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    pool = get_pool()
    with pool.connection() as conn:
        _ensure_vector_registered(conn)
        with conn.cursor() as cur:
            if source_type_filter:
                cur.execute(
                    """
                    SELECT source_id, source_type, chunk_text, metadata,
                           (embedding <=> %s) AS distance
                    FROM rag_chunks
                    WHERE source_type = %s AND embedding IS NOT NULL
                    ORDER BY embedding <=> %s
                    LIMIT %s
                    """,
                    (query_embedding, source_type_filter, query_embedding, top_k),
                )
            else:
                cur.execute(
                    """
                    SELECT source_id, source_type, chunk_text, metadata,
                           (embedding <=> %s) AS distance
                    FROM rag_chunks
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %s
                    LIMIT %s
                    """,
                    (query_embedding, query_embedding, top_k),
                )
            rows = cur.fetchall()

    out = []
    for r in rows:
        out.append({
            "source_id": r[0],
            "source_type": r[1],
            "chunk_text": r[2],
            "metadata": r[3],
            "distance": float(r[4]),
        })
    return out
