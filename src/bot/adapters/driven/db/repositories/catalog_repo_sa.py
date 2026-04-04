"""SQLAlchemy repository for catalog_documents."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.bot.domain.errors import CatalogNotFound
from src.bot.infrastructure.logging import get_logger

logger = get_logger(__name__)

_COLS = """
    id, manufacturer_id, original_filename, stored_filename,
    file_size_bytes, description, status, page_count, chunk_count,
    error_message, brand, is_active, created_at, updated_at
"""


class CatalogRepoSqlAlchemy:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── CREATE ────────────────────────────────────────────────────────

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        row = self._session.execute(
            text(f"""
                INSERT INTO catalog_documents
                  (manufacturer_id, original_filename, stored_filename,
                   file_size_bytes, description, brand, status)
                VALUES
                  (:manufacturer_id, :original_filename, :stored_filename,
                   :file_size_bytes, :description, :brand, 'pending')
                RETURNING {_COLS}
            """),
            {
                "manufacturer_id": payload.get("manufacturer_id"),
                "original_filename": payload["original_filename"],
                "stored_filename": payload["stored_filename"],
                "file_size_bytes": payload.get("file_size_bytes"),
                "description": payload.get("description"),
                "brand": payload.get("brand"),
            },
        ).mappings().one()
        self._session.commit()
        return dict(row)

    # ── READ ──────────────────────────────────────────────────────────

    def get_by_id(self, catalog_id: int) -> dict[str, Any]:
        row = self._session.execute(
            text(f"SELECT {_COLS} FROM catalog_documents WHERE id = :id"),
            {"id": catalog_id},
        ).mappings().one_or_none()
        if row is None:
            raise CatalogNotFound(f"catalog {catalog_id} not found")
        return dict(row)

    def list_catalogs(
        self,
        *,
        manufacturer_id: int | None = None,
        status: str | None = None,
        brand: str | None = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        where = []
        if not include_inactive:
            where.append("is_active = true")
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if manufacturer_id is not None:
            where.append("manufacturer_id = :manufacturer_id")
            params["manufacturer_id"] = manufacturer_id

        if status is not None:
            where.append("status = :status")
            params["status"] = status

        if brand is not None:
            where.append("brand = :brand")
            params["brand"] = brand

        where_sql = " AND ".join(where) if where else "1=1"

        rows = self._session.execute(
            text(f"""
                SELECT {_COLS}
                FROM catalog_documents
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        ).mappings().all()
        return [dict(r) for r in rows]

    # ── UPDATE ────────────────────────────────────────────────────────

    def deactivate_older_duplicates(self, filename: str, keep_id: int) -> int:
        """Deactivate older catalogs with the same filename (except keep_id).

        Called after a new catalog upload so only the latest version is active.
        Returns the number of deactivated catalogs.
        """
        result = self._session.execute(
            text("""
                UPDATE catalog_documents
                SET is_active = false, updated_at = now()
                WHERE original_filename = :filename
                  AND id != :keep_id
                  AND is_active = true
            """),
            {"filename": filename, "keep_id": keep_id},
        )
        if result.rowcount > 0:
            self._session.commit()
            logger.info(
                "Deactivated %d older catalog(s) with filename '%s' (kept id=%d)",
                result.rowcount, filename, keep_id,
            )
        return result.rowcount

    def update_brand(self, catalog_id: int, brand: str) -> None:
        """Update catalog brand during ingestion."""
        self._session.execute(
            text("""
                UPDATE catalog_documents
                SET brand = :brand, updated_at = now()
                WHERE id = :id
            """),
            {"id": catalog_id, "brand": brand},
        )
        self._session.commit()

    def update_status(
        self,
        catalog_id: int,
        status: str,
        *,
        page_count: int | None = None,
        chunk_count: int | None = None,
        error_message: str | None = None,
    ) -> None:
        self._session.execute(
            text("""
                UPDATE catalog_documents
                SET status        = :status,
                    page_count    = COALESCE(:page_count, page_count),
                    chunk_count   = COALESCE(:chunk_count, chunk_count),
                    error_message = :error_message,
                    updated_at    = now()
                WHERE id = :id
            """),
            {
                "id": catalog_id,
                "status": status,
                "page_count": page_count,
                "chunk_count": chunk_count,
                "error_message": error_message,
            },
        )
        self._session.commit()

    # ── DELETE ────────────────────────────────────────────────────────

    def deactivate(self, catalog_id: int) -> None:
        """Soft-delete: mark catalog as inactive (soft-delete)."""
        result = self._session.execute(
            text("""
                UPDATE catalog_documents
                SET is_active = false, updated_at = now()
                WHERE id = :id
            """),
            {"id": catalog_id},
        )
        if result.rowcount == 0:
            self._session.rollback()
            raise CatalogNotFound(f"catalog {catalog_id} not found")
        self._session.commit()

    def delete(self, catalog_id: int) -> None:
        """Hard-delete: physically remove catalog and its chunks."""
        result = self._session.execute(
            text("DELETE FROM catalog_documents WHERE id = :id"),
            {"id": catalog_id},
        )
        if result.rowcount == 0:
            self._session.rollback()
            raise CatalogNotFound(f"catalog {catalog_id} not found")
        self._session.commit()
