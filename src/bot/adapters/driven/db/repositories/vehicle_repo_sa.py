"""SQLAlchemy repository for vehicles."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.bot.domain.errors import ConflictError, ManufacturerNotFound, VehicleNotFound

_COLS = """
    v.id,
    v.manufacturer_id,
    m.name AS manufacturer_name,
    m.country_of_origin,
    v.model,
    v.model_year_start,
    v.model_year_end,
    v.body_type,
    v.fuel_type,
    v.engine_displacement,
    v.soft_delete,
    v.created_at,
    v.updated_at
"""


class VehicleRepoSqlAlchemy:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── CREATE ────────────────────────────────────────────────────────

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        manufacturer_id = payload["manufacturer_id"]
        # Validate manufacturer exists
        exists = self._session.execute(
            text("SELECT 1 FROM manufacturers WHERE id = :id AND soft_delete = false"),
            {"id": manufacturer_id},
        ).one_or_none()
        if exists is None:
            raise ManufacturerNotFound(f"manufacturer {manufacturer_id} not found")

        try:
            row = self._session.execute(
                text(f"""
                    INSERT INTO vehicles
                        (manufacturer_id, model, model_year_start, model_year_end,
                         body_type, fuel_type, engine_displacement)
                    VALUES
                        (:manufacturer_id, :model, :model_year_start, :model_year_end,
                         :body_type, :fuel_type, :engine_displacement)
                    RETURNING id
                """),
                {
                    "manufacturer_id": payload["manufacturer_id"],
                    "model": payload["model"],
                    "model_year_start": payload["model_year_start"],
                    "model_year_end": payload.get("model_year_end"),
                    "body_type": payload["body_type"],
                    "fuel_type": payload.get("fuel_type", "flex"),
                    "engine_displacement": payload.get("engine_displacement"),
                },
            ).mappings().one()
            self._session.commit()
            return self.get_by_id(row["id"])
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("vehicle constraint violation") from exc

    # ── READ ──────────────────────────────────────────────────────────

    def list_vehicles(
        self,
        *,
        manufacturer_id: int | None = None,
        body_type: str | None = None,
        fuel_type: str | None = None,
        country_of_origin: str | None = None,
        year: int | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        is_current: bool | None = None,
        engine: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        where = ["v.soft_delete = false", "m.soft_delete = false"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if manufacturer_id is not None:
            where.append("v.manufacturer_id = :manufacturer_id")
            params["manufacturer_id"] = manufacturer_id

        if body_type:
            where.append("v.body_type = :body_type")
            params["body_type"] = body_type

        if fuel_type:
            where.append("v.fuel_type = :fuel_type")
            params["fuel_type"] = fuel_type

        if country_of_origin:
            where.append("lower(m.country_of_origin) = lower(:country_of_origin)")
            params["country_of_origin"] = country_of_origin

        if year is not None:
            where.append("""
                v.model_year_start <= :year
                AND (v.model_year_end IS NULL OR v.model_year_end >= :year)
            """)
            params["year"] = year

        if year_from is not None:
            where.append("v.model_year_start >= :year_from")
            params["year_from"] = year_from

        if year_to is not None:
            where.append("v.model_year_start <= :year_to")
            params["year_to"] = year_to

        if is_current is True:
            where.append("v.model_year_end IS NULL")
        elif is_current is False:
            where.append("v.model_year_end IS NOT NULL")

        if engine:
            where.append("lower(v.engine_displacement) LIKE lower(:engine)")
            params["engine"] = f"%{engine}%"

        if search:
            where.append("""
                (lower(v.model) LIKE lower(:search)
                 OR lower(m.name) LIKE lower(:search))
            """)
            params["search"] = f"%{search}%"

        rows = self._session.execute(
            text(f"""
                SELECT {_COLS}
                FROM vehicles v
                JOIN manufacturers m ON m.id = v.manufacturer_id
                WHERE {' AND '.join(where)}
                ORDER BY m.name, v.model, v.model_year_start
                LIMIT :limit OFFSET :offset
            """),
            params,
        ).mappings().all()
        return [dict(r) for r in rows]

    def get_by_id(self, vehicle_id: int) -> dict[str, Any]:
        row = self._session.execute(
            text(f"""
                SELECT {_COLS}
                FROM vehicles v
                JOIN manufacturers m ON m.id = v.manufacturer_id
                WHERE v.id = :id AND v.soft_delete = false
            """),
            {"id": vehicle_id},
        ).mappings().one_or_none()
        if row is None:
            raise VehicleNotFound(f"vehicle {vehicle_id} not found")
        return dict(row)

    # ── UPDATE ────────────────────────────────────────────────────────

    def update(self, vehicle_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "manufacturer_id", "model", "model_year_start", "model_year_end",
            "body_type", "fuel_type", "engine_displacement",
        }
        fields = {k: v for k, v in payload.items() if k in allowed}
        if not fields:
            return self.get_by_id(vehicle_id)

        if "manufacturer_id" in fields:
            exists = self._session.execute(
                text("SELECT 1 FROM manufacturers WHERE id = :id AND soft_delete = false"),
                {"id": fields["manufacturer_id"]},
            ).one_or_none()
            if exists is None:
                raise ManufacturerNotFound(f"manufacturer {fields['manufacturer_id']} not found")

        set_clause = ", ".join(f"{col} = :{col}" for col in fields)
        params = {**fields, "id": vehicle_id}

        try:
            result = self._session.execute(
                text(f"""
                    UPDATE vehicles
                    SET {set_clause}, updated_at = now()
                    WHERE id = :id AND soft_delete = false
                    RETURNING id
                """),
                params,
            ).mappings().one_or_none()
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("vehicle constraint violation") from exc

        if result is None:
            raise VehicleNotFound(f"vehicle {vehicle_id} not found")
        self._session.commit()
        return self.get_by_id(vehicle_id)

    # ── DELETE (soft) ─────────────────────────────────────────────────

    def delete(self, vehicle_id: int) -> None:
        result = self._session.execute(
            text("""
                UPDATE vehicles
                SET soft_delete = true, updated_at = now()
                WHERE id = :id AND soft_delete = false
            """),
            {"id": vehicle_id},
        )
        if result.rowcount == 0:
            self._session.rollback()
            raise VehicleNotFound(f"vehicle {vehicle_id} not found")
        self._session.commit()
