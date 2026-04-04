"""SQLAlchemy repository for manufacturers (montadoras)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.bot.domain.errors import ConflictError, ManufacturerNotFound

_COLS = """
    id, name, country_of_origin, soft_delete, created_at, updated_at
"""


class ManufacturerRepoSqlAlchemy:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── CREATE ────────────────────────────────────────────────────────

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            row = self._session.execute(
                text(f"""
                    INSERT INTO manufacturers (name, country_of_origin)
                    VALUES (:name, :country_of_origin)
                    RETURNING {_COLS}
                """),
                {
                    "name": payload["name"],
                    "country_of_origin": payload["country_of_origin"],
                },
            ).mappings().one()
            self._session.commit()
            return dict(row)
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("manufacturer name already exists") from exc

    # ── READ ──────────────────────────────────────────────────────────

    def list_manufacturers(
        self,
        *,
        country_of_origin: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        where = ["soft_delete = false"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if country_of_origin:
            where.append("lower(country_of_origin) = lower(:country_of_origin)")
            params["country_of_origin"] = country_of_origin

        if search:
            where.append("lower(name) LIKE lower(:search)")
            params["search"] = f"%{search}%"

        rows = self._session.execute(
            text(f"""
                SELECT {_COLS}
                FROM manufacturers
                WHERE {' AND '.join(where)}
                ORDER BY name
                LIMIT :limit OFFSET :offset
            """),
            params,
        ).mappings().all()
        return [dict(r) for r in rows]

    def get_by_id(self, manufacturer_id: int) -> dict[str, Any]:
        row = self._session.execute(
            text(f"""
                SELECT {_COLS}
                FROM manufacturers
                WHERE id = :id AND soft_delete = false
            """),
            {"id": manufacturer_id},
        ).mappings().one_or_none()
        if row is None:
            raise ManufacturerNotFound(f"manufacturer {manufacturer_id} not found")
        return dict(row)

    # ── UPDATE ────────────────────────────────────────────────────────

    def update(self, manufacturer_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        allowed = {"name", "country_of_origin"}
        fields = {k: v for k, v in payload.items() if k in allowed}
        if not fields:
            return self.get_by_id(manufacturer_id)

        set_clause = ", ".join(f"{col} = :{col}" for col in fields)
        params = {**fields, "id": manufacturer_id}

        try:
            row = self._session.execute(
                text(f"""
                    UPDATE manufacturers
                    SET {set_clause}, updated_at = now()
                    WHERE id = :id AND soft_delete = false
                    RETURNING {_COLS}
                """),
                params,
            ).mappings().one_or_none()
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("manufacturer name already exists") from exc

        if row is None:
            raise ManufacturerNotFound(f"manufacturer {manufacturer_id} not found")
        self._session.commit()
        return dict(row)

    # ── DELETE (soft) ─────────────────────────────────────────────────

    def delete(self, manufacturer_id: int) -> None:
        result = self._session.execute(
            text("""
                UPDATE manufacturers
                SET soft_delete = true, updated_at = now()
                WHERE id = :id AND soft_delete = false
            """),
            {"id": manufacturer_id},
        )
        if result.rowcount == 0:
            self._session.rollback()
            raise ManufacturerNotFound(f"manufacturer {manufacturer_id} not found")
        self._session.commit()
