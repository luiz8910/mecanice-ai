"""SQLAlchemy repository for vendors and workshop/store assignments."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.bot.domain.errors import (
    ConflictError,
    ValidationError,
    VendorNotFound,
)


VENDOR_RETURNING = """\
id,
autopart_id,
name,
email,
active,
soft_delete,
served_workshops_count,
quotes_received_count,
sales_converted_count,
metrics_updated_at,
created_at,
updated_at
"""


class VendorRepoSqlAlchemy:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_vendor(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._autopart_exists(int(payload["autopart_id"])):
            raise ValidationError("autopart not found")

        stmt = text(
            f"""
            INSERT INTO vendors (autopart_id, name, email, active)
            VALUES (:autopart_id, :name, :email, COALESCE(:active, true))
            RETURNING {VENDOR_RETURNING}
            """
        )
        try:
            row = self._session.execute(stmt, payload).mappings().one()
            self._session.commit()
            return dict(row)
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("vendor already exists for this autopart/email") from exc

    def list_vendors(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        autopart_id: int | None = None,
        active: bool | None = None,
    ) -> list[dict[str, Any]]:
        where = ["soft_delete = false"]
        params: dict[str, Any] = {"limit": int(limit), "offset": int(offset)}
        if autopart_id is not None:
            where.append("autopart_id = :autopart_id")
            params["autopart_id"] = int(autopart_id)
        if active is not None:
            where.append("active = :active")
            params["active"] = bool(active)

        stmt = text(
            f"""
            SELECT {VENDOR_RETURNING}
            FROM vendors
            WHERE {' AND '.join(where)}
            ORDER BY id
            LIMIT :limit
            OFFSET :offset
            """
        )
        rows = self._session.execute(stmt, params).mappings().all()
        return [dict(r) for r in rows]

    def get_vendor(self, vendor_id: int) -> dict[str, Any]:
        row = self._session.execute(
            text(
                f"""
                SELECT {VENDOR_RETURNING}
                FROM vendors
                WHERE id = :id
                                    AND soft_delete = false
                """
            ),
            {"id": int(vendor_id)},
        ).mappings().one_or_none()
        if row is None:
            raise VendorNotFound("vendor not found")
        return dict(row)

    def update_vendor(self, vendor_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        allowed = {"name", "email", "active"}
        updates = {k: v for k, v in payload.items() if k in allowed}
        if not updates:
            raise ValidationError("no fields to update")

        set_parts = [f"{k} = :{k}" for k in updates.keys()]
        set_sql = ",\n                    ".join(set_parts)

        stmt = text(
            f"""
            UPDATE vendors
            SET
                {set_sql},
                updated_at = now()
            WHERE id = :id
              AND soft_delete = false
            RETURNING {VENDOR_RETURNING}
            """
        )
        try:
            row = self._session.execute(
                stmt,
                {
                    "id": int(vendor_id),
                    **updates,
                },
            ).mappings().one_or_none()
            if row is None:
                self._session.rollback()
                raise VendorNotFound("vendor not found")
            self._session.commit()
            return dict(row)
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("vendor update conflicts with existing data") from exc

    def delete_vendor(self, vendor_id: int) -> None:
        result = self._session.execute(
            text(
                """
                UPDATE vendors
                SET
                    soft_delete = true,
                    active = false,
                    updated_at = now()
                WHERE id = :id
                  AND soft_delete = false
                """
            ),
            {"id": int(vendor_id)},
        )
        if result.rowcount == 0:
            self._session.rollback()
            raise VendorNotFound("vendor not found")
        self._session.commit()

    def assign_vendor_to_workshop(self, *, workshop_id: int, autopart_id: int, vendor_id: int) -> dict[str, Any]:
        vendor = self._session.execute(
            text(
                """
                SELECT id, autopart_id, name
                FROM vendors
                WHERE id = :vendor_id
                  AND active = true
                                    AND soft_delete = false
                """
            ),
            {"vendor_id": int(vendor_id)},
        ).mappings().one_or_none()
        if vendor is None:
            raise VendorNotFound("vendor not found")
        if int(vendor["autopart_id"]) != int(autopart_id):
            raise ValidationError("vendor must belong to the same autopart")

        if not self._workshop_exists(int(workshop_id)):
            raise ValidationError("workshop not found")
        if not self._autopart_exists(int(autopart_id)):
            raise ValidationError("autopart not found")

        row = self._session.execute(
            text(
                """
                INSERT INTO vendor_assignments (workshop_id, autopart_id, vendor_id)
                VALUES (:workshop_id, :autopart_id, :vendor_id)
                ON CONFLICT (workshop_id, autopart_id)
                DO UPDATE SET
                    vendor_id = EXCLUDED.vendor_id,
                    updated_at = now()
                RETURNING id, workshop_id, autopart_id, vendor_id, created_at, updated_at
                """
            ),
            {
                "workshop_id": int(workshop_id),
                "autopart_id": int(autopart_id),
                "vendor_id": int(vendor_id),
            },
        ).mappings().one()

        self.refresh_vendor_served_workshops_count(int(vendor_id))
        self.record_workshop_assigned(
            vendor_id=int(vendor_id),
            autopart_id=int(autopart_id),
            workshop_id=int(workshop_id),
        )

        self._session.commit()
        return dict(row)

    def list_assignments(
        self,
        *,
        workshop_id: int | None = None,
        autopart_id: int | None = None,
        vendor_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        where = ["1=1"]
        params: dict[str, Any] = {"limit": int(limit), "offset": int(offset)}
        if workshop_id is not None:
            where.append("va.workshop_id = :workshop_id")
            params["workshop_id"] = int(workshop_id)
        if autopart_id is not None:
            where.append("va.autopart_id = :autopart_id")
            params["autopart_id"] = int(autopart_id)
        if vendor_id is not None:
            where.append("va.vendor_id = :vendor_id")
            params["vendor_id"] = int(vendor_id)

        stmt = text(
            f"""
            SELECT
                va.id,
                va.workshop_id,
                w.name AS workshop_name,
                va.autopart_id,
                ap.name AS autopart_name,
                va.vendor_id,
                v.name AS vendor_name,
                va.created_at,
                va.updated_at
            FROM vendor_assignments va
            JOIN workshops w ON w.id = va.workshop_id
            JOIN autoparts ap ON ap.id = va.autopart_id
            JOIN vendors v ON v.id = va.vendor_id
            WHERE {' AND '.join(where)}
                            AND v.soft_delete = false
            ORDER BY va.id
            LIMIT :limit
            OFFSET :offset
            """
        )
        rows = self._session.execute(stmt, params).mappings().all()
        return [dict(r) for r in rows]

    def record_quote_received(
        self,
        *,
        vendor_id: int,
        autopart_id: int,
        workshop_id: int,
        conversation_id: str,
        request_id: str,
    ) -> None:
        self._bump_counter(vendor_id=vendor_id, column_name="quotes_received_count")
        self._record_vendor_metric_event(
            vendor_id=vendor_id,
            autopart_id=autopart_id,
            workshop_id=workshop_id,
            conversation_id=conversation_id,
            request_id=request_id,
            event_type="QUOTE_RECEIVED",
        )
        self._session.commit()

    def record_workshop_assigned(
        self,
        *,
        vendor_id: int,
        autopart_id: int,
        workshop_id: int,
    ) -> None:
        self._record_vendor_metric_event(
            vendor_id=vendor_id,
            autopart_id=autopart_id,
            workshop_id=workshop_id,
            event_type="WORKSHOP_ASSIGNED",
        )

    def refresh_vendor_served_workshops_count(self, vendor_id: int) -> None:
        self._refresh_vendor_served_workshops_count(vendor_id)

    def record_sale_converted(
        self,
        *,
        vendor_id: int,
        autopart_id: int,
        workshop_id: int,
        conversation_id: str,
        request_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._bump_counter(vendor_id=vendor_id, column_name="sales_converted_count")
        self._record_vendor_metric_event(
            vendor_id=vendor_id,
            autopart_id=autopart_id,
            workshop_id=workshop_id,
            conversation_id=conversation_id,
            request_id=request_id,
            event_type="SALE_CONVERTED",
            metadata=metadata or {},
        )
        self._session.commit()

    def get_metric_events(
        self,
        *,
        vendor_id: int | None = None,
        event_type: str | None = None,
        start_ts: str | None = None,
        end_ts: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        where = ["1=1"]
        params: dict[str, Any] = {"limit": int(limit), "offset": int(offset)}
        if vendor_id is not None:
            where.append("vendor_id = :vendor_id")
            params["vendor_id"] = int(vendor_id)
        if event_type is not None:
            where.append("event_type = :event_type")
            params["event_type"] = event_type
        if start_ts is not None:
            where.append("event_ts >= :start_ts::timestamptz")
            params["start_ts"] = start_ts
        if end_ts is not None:
            where.append("event_ts <= :end_ts::timestamptz")
            params["end_ts"] = end_ts

        rows = self._session.execute(
            text(
                f"""
                SELECT
                    id,
                    vendor_id,
                    autopart_id,
                    workshop_id,
                    conversation_id,
                    request_id,
                    event_type,
                    event_ts,
                    metadata
                FROM vendor_metric_events
                WHERE {' AND '.join(where)}
                ORDER BY event_ts DESC, id DESC
                LIMIT :limit
                OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        return [dict(r) for r in rows]

    def _bump_counter(self, *, vendor_id: int, column_name: str) -> None:
        self._session.execute(
            text(
                f"""
                UPDATE vendors
                SET
                    {column_name} = {column_name} + 1,
                    metrics_updated_at = now(),
                    updated_at = now()
                WHERE id = :vendor_id
                """
            ),
            {"vendor_id": int(vendor_id)},
        )

    def _refresh_vendor_served_workshops_count(self, vendor_id: int) -> None:
        self._session.execute(
            text(
                """
                UPDATE vendors v
                SET
                    served_workshops_count = sub.count_workshops,
                    metrics_updated_at = now(),
                    updated_at = now()
                FROM (
                    SELECT vendor_id, COUNT(*)::int AS count_workshops
                    FROM vendor_assignments
                    WHERE vendor_id = :vendor_id
                    GROUP BY vendor_id
                ) sub
                WHERE v.id = sub.vendor_id
                """
            ),
            {"vendor_id": int(vendor_id)},
        )

    def _record_vendor_metric_event(
        self,
        *,
        vendor_id: int,
        autopart_id: int,
        workshop_id: int | None = None,
        conversation_id: str | None = None,
        request_id: str | None = None,
        event_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._session.execute(
            text(
                """
                INSERT INTO vendor_metric_events (
                    vendor_id,
                    autopart_id,
                    workshop_id,
                    conversation_id,
                    request_id,
                    event_type,
                    metadata
                )
                VALUES (
                    :vendor_id,
                    :autopart_id,
                    :workshop_id,
                    :conversation_id,
                    :request_id,
                    :event_type,
                    CAST(:metadata AS jsonb)
                )
                """
            ),
            {
                "vendor_id": int(vendor_id),
                "autopart_id": int(autopart_id),
                "workshop_id": int(workshop_id) if workshop_id is not None else None,
                "conversation_id": conversation_id,
                "request_id": request_id,
                "event_type": event_type,
                "metadata": __import__("json").dumps(metadata or {}),
            },
        )

    def _workshop_exists(self, workshop_id: int) -> bool:
        row = self._session.execute(
            text(
                """
                SELECT 1
                FROM workshops
                WHERE id = :id
                  AND soft_delete = false
                """
            ),
            {"id": int(workshop_id)},
        ).first()
        return row is not None

    def _autopart_exists(self, autopart_id: int) -> bool:
        row = self._session.execute(
            text("SELECT 1 FROM autoparts WHERE id = :id"),
            {"id": int(autopart_id)},
        ).first()
        return row is not None
