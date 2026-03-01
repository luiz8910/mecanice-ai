"""SQLAlchemy repository for quotations (cotações)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.bot.domain.errors import (
    ConflictError,
    QuotationNotFound,
    ValidationError,
)


QUOTATION_SELECT = """\
q.id,
q.code,
q.seller_id,
v.name  AS seller_name,
q.workshop_id,
w.name  AS workshop_name,
q.part_number,
q.part_description,
q.vehicle_info,
q.status,
q.is_urgent,
q.offer_submitted,
q.original_message,
q.notes,
q.created_at,
q.updated_at
"""

QUOTATION_FROM = """\
quotations q
JOIN vendors   v ON v.id = q.seller_id
JOIN workshops w ON w.id = q.workshop_id
"""


class QuotationRepoSqlAlchemy:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── helpers ──────────────────────────────────────────────────

    def _vendor_exists(self, vendor_id: int) -> bool:
        row = self._session.execute(
            text("SELECT 1 FROM vendors WHERE id = :id AND soft_delete = false"),
            {"id": vendor_id},
        ).one_or_none()
        return row is not None

    def _workshop_exists(self, workshop_id: int) -> bool:
        row = self._session.execute(
            text("SELECT 1 FROM workshops WHERE id = :id AND soft_delete = false"),
            {"id": workshop_id},
        ).one_or_none()
        return row is not None

    # ── create ───────────────────────────────────────────────────

    def create_quotation(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._vendor_exists(int(payload["seller_id"])):
            raise ValidationError("seller (vendor) not found")
        if not self._workshop_exists(int(payload["workshop_id"])):
            raise ValidationError("workshop not found")

        stmt = text(
            f"""
            INSERT INTO quotations
                (code, seller_id, workshop_id, part_number, part_description,
                 vehicle_info, status, is_urgent, offer_submitted, original_message, notes)
            VALUES
                (:code, :seller_id, :workshop_id, :part_number, :part_description,
                 :vehicle_info, COALESCE(:status, 'NEW'),
                 COALESCE(:is_urgent, false),
                 COALESCE(:offer_submitted, false),
                 :original_message,
                 :notes)
            RETURNING id, code, seller_id, workshop_id, part_number, part_description,
                      vehicle_info, status, is_urgent, offer_submitted, notes,
                      created_at, updated_at
            """
        )
        params = {
            "code": payload["code"],
            "seller_id": int(payload["seller_id"]),
            "workshop_id": int(payload["workshop_id"]),
            "part_number": payload["part_number"],
            "part_description": payload["part_description"],
            "vehicle_info": payload.get("vehicle_info"),
            "status": payload.get("status", "NEW"),
            "is_urgent": payload.get("is_urgent", False),
            "offer_submitted": payload.get("offer_submitted", False),
            "original_message": payload.get("original_message"),
            "notes": payload.get("notes"),
        }
        try:
            row = self._session.execute(stmt, params).mappings().one()
            self._session.commit()
            # Re-read with JOINs to include seller_name / workshop_name
            return self.get_quotation(int(row["id"]))
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("quotation with this code already exists") from exc

    # ── read one ─────────────────────────────────────────────────

    def get_quotation(self, quotation_id: int) -> dict[str, Any]:
        row = self._session.execute(
            text(
                f"""
                SELECT {QUOTATION_SELECT}
                FROM {QUOTATION_FROM}
                WHERE q.id = :id
                  AND q.soft_delete = false
                """
            ),
            {"id": int(quotation_id)},
        ).mappings().one_or_none()
        if row is None:
            raise QuotationNotFound("quotation not found")
        return dict(row)

    # ── list ─────────────────────────────────────────────────────

    def list_quotations(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        seller_id: int | None = None,
        workshop_id: int | None = None,
        status: str | None = None,
        is_urgent: bool | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        where = ["q.soft_delete = false"]
        params: dict[str, Any] = {"limit": int(limit), "offset": int(offset)}

        if seller_id is not None:
            where.append("q.seller_id = :seller_id")
            params["seller_id"] = int(seller_id)
        if workshop_id is not None:
            where.append("q.workshop_id = :workshop_id")
            params["workshop_id"] = int(workshop_id)
        if status is not None:
            where.append("q.status = :status")
            params["status"] = status
        if is_urgent is not None:
            where.append("q.is_urgent = :is_urgent")
            params["is_urgent"] = bool(is_urgent)
        if search is not None:
            where.append(
                "(q.code ILIKE :search OR q.part_number ILIKE :search "
                "OR q.part_description ILIKE :search OR q.vehicle_info ILIKE :search "
                "OR w.name ILIKE :search)"
            )
            params["search"] = f"%{search}%"

        stmt = text(
            f"""
            SELECT {QUOTATION_SELECT}
            FROM {QUOTATION_FROM}
            WHERE {' AND '.join(where)}
            ORDER BY q.created_at DESC
            LIMIT :limit
            OFFSET :offset
            """
        )
        rows = self._session.execute(stmt, params).mappings().all()
        return [dict(r) for r in rows]

    # ── update ───────────────────────────────────────────────────

    def update_quotation(self, quotation_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "part_number",
            "part_description",
            "vehicle_info",
            "status",
            "is_urgent",
            "offer_submitted",
            "original_message",
            "notes",
        }
        updates = {k: v for k, v in payload.items() if k in allowed}
        if not updates:
            raise ValidationError("no fields to update")

        set_parts = [f"{k} = :{k}" for k in updates]
        set_sql = ",\n                    ".join(set_parts)

        stmt = text(
            f"""
            UPDATE quotations
            SET
                {set_sql},
                updated_at = now()
            WHERE id = :id
              AND soft_delete = false
            RETURNING id
            """
        )
        row = self._session.execute(
            stmt,
            {"id": int(quotation_id), **updates},
        ).mappings().one_or_none()

        if row is None:
            self._session.rollback()
            raise QuotationNotFound("quotation not found")
        self._session.commit()
        return self.get_quotation(int(row["id"]))

    # ── delete (soft) ────────────────────────────────────────────

    def delete_quotation(self, quotation_id: int) -> None:
        result = self._session.execute(
            text(
                """
                UPDATE quotations
                SET soft_delete = true,
                    updated_at  = now()
                WHERE id = :id
                  AND soft_delete = false
                """
            ),
            {"id": int(quotation_id)},
        )
        if result.rowcount == 0:
            self._session.rollback()
            raise QuotationNotFound("quotation not found")
        self._session.commit()

    # ── seller inbox helpers ─────────────────────────────────────

    def inbox_list(
        self,
        *,
        seller_id: int,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return (items, total) for the seller inbox with page-based pagination."""

        where = ["q.soft_delete = false", "q.seller_id = :seller_id"]
        params: dict[str, Any] = {"seller_id": int(seller_id)}

        if status is not None:
            where.append("q.status = :status")
            params["status"] = status
        if search is not None:
            where.append(
                "(q.code ILIKE :search OR q.part_number ILIKE :search "
                "OR q.part_description ILIKE :search OR q.vehicle_info ILIKE :search "
                "OR w.name ILIKE :search)"
            )
            params["search"] = f"%{search}%"

        where_sql = " AND ".join(where)

        # total count
        count_stmt = text(
            f"""
            SELECT count(*) AS cnt
            FROM {QUOTATION_FROM}
            WHERE {where_sql}
            """
        )
        total: int = self._session.execute(count_stmt, params).scalar() or 0

        # paginated rows
        safe_page = max(1, page)
        safe_size = max(1, min(page_size, 100))
        offset = (safe_page - 1) * safe_size
        params["limit"] = safe_size
        params["offset"] = offset

        data_stmt = text(
            f"""
            SELECT
                q.id,
                q.code,
                q.seller_id,
                v.autopart_id AS store_id,
                q.workshop_id,
                w.name  AS workshop_name,
                q.part_number,
                q.part_description,
                q.vehicle_info,
                q.status,
                q.is_urgent,
                q.offer_submitted,
                q.created_at,
                q.updated_at
            FROM {QUOTATION_FROM}
            WHERE {where_sql}
            ORDER BY q.created_at DESC
            LIMIT :limit
            OFFSET :offset
            """
        )
        rows = self._session.execute(data_stmt, params).mappings().all()
        return [dict(r) for r in rows], total

    def inbox_get(self, *, quotation_id: int, seller_id: int) -> dict[str, Any]:
        """Return full detail of one quotation, scoped to the seller."""
        row = self._session.execute(
            text(
                f"""
                SELECT
                    q.id,
                    q.code,
                    q.seller_id,
                    v.name          AS seller_name,
                    v.autopart_id   AS store_id,
                    q.workshop_id,
                    w.name          AS workshop_name,
                    w.whatsapp_phone_e164 AS workshop_phone,
                    COALESCE(w.address,
                        CASE WHEN w.city IS NOT NULL
                             THEN w.city || '/' || w.state_uf
                             ELSE NULL END
                    ) AS workshop_address,
                    q.part_number,
                    q.part_description,
                    q.vehicle_info,
                    q.original_message,
                    q.status,
                    q.is_urgent,
                    q.offer_submitted,
                    q.notes,
                    q.created_at,
                    q.updated_at
                FROM {QUOTATION_FROM}
                WHERE q.id = :id
                  AND q.seller_id = :seller_id
                  AND q.soft_delete = false
                """
            ),
            {"id": int(quotation_id), "seller_id": int(seller_id)},
        ).mappings().one_or_none()
        if row is None:
            raise QuotationNotFound("Item não encontrado.")
        return dict(row)

    def inbox_update_status(self, *, quotation_id: int, seller_id: int, new_status: str) -> None:
        """Update the status of an inbox item, scoped to the seller."""
        result = self._session.execute(
            text(
                """
                UPDATE quotations
                SET status     = :status,
                    updated_at = now()
                WHERE id = :id
                  AND seller_id = :seller_id
                  AND soft_delete = false
                """
            ),
            {
                "id": int(quotation_id),
                "seller_id": int(seller_id),
                "status": new_status,
            },
        )
        if result.rowcount == 0:
            self._session.rollback()
            raise QuotationNotFound("Item não encontrado.")
        self._session.commit()
