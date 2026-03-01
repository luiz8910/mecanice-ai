"""SQLAlchemy repository for quotation items and events."""

from __future__ import annotations

from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from src.bot.domain.errors import QuotationNotFound, ValidationError


class QuotationItemRepoSqlAlchemy:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── items ────────────────────────────────────────────────────

    def add_item(self, *, quotation_id: int, seller_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Add an item (part) to a quotation. Scoped to seller."""
        self._assert_quotation_owner(quotation_id, seller_id)

        stmt = text(
            """
            INSERT INTO quotation_items
                (quotation_id, part_number, description, brand, compatibility,
                 price, availability, delivery_time, confidence_score, notes, selected)
            VALUES
                (:quotation_id, :part_number, :description, :brand, :compatibility,
                 :price, :availability, :delivery_time, :confidence_score, :notes, :selected)
            RETURNING *
            """
        )
        row = self._session.execute(
            stmt,
            {
                "quotation_id": quotation_id,
                "part_number": payload["part_number"],
                "description": payload.get("description", ""),
                "brand": payload.get("brand"),
                "compatibility": payload.get("compatibility"),
                "price": payload.get("price"),
                "availability": payload.get("availability", "Em estoque"),
                "delivery_time": payload.get("delivery_time"),
                "confidence_score": payload.get("confidence_score"),
                "notes": payload.get("notes"),
                "selected": payload.get("selected", False),
            },
        ).mappings().one()
        self._session.commit()
        return dict(row)

    def update_item(self, *, item_id: int, quotation_id: int, seller_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Update an item (e.g. set price, select it). Scoped to seller."""
        self._assert_quotation_owner(quotation_id, seller_id)

        allowed = {
            "description", "brand", "compatibility", "price",
            "availability", "delivery_time", "confidence_score",
            "notes", "selected",
        }
        updates = {k: v for k, v in payload.items() if k in allowed and v is not None}
        if not updates:
            raise ValidationError("no fields to update")

        set_parts = [f"{k} = :{k}" for k in updates]
        set_sql = ", ".join(set_parts)

        stmt = text(
            f"""
            UPDATE quotation_items
            SET {set_sql}, updated_at = now()
            WHERE id = :item_id AND quotation_id = :quotation_id
            RETURNING *
            """
        )
        row = self._session.execute(
            stmt,
            {"item_id": item_id, "quotation_id": quotation_id, **updates},
        ).mappings().one_or_none()

        if row is None:
            self._session.rollback()
            raise QuotationNotFound("Item não encontrado.")
        self._session.commit()
        return dict(row)

    def delete_item(self, *, item_id: int, quotation_id: int, seller_id: int) -> None:
        """Remove an item from a quotation. Scoped to seller."""
        self._assert_quotation_owner(quotation_id, seller_id)
        result = self._session.execute(
            text(
                "DELETE FROM quotation_items WHERE id = :item_id AND quotation_id = :quotation_id"
            ),
            {"item_id": item_id, "quotation_id": quotation_id},
        )
        if result.rowcount == 0:
            self._session.rollback()
            raise QuotationNotFound("Item não encontrado.")
        self._session.commit()

    def list_items(self, *, quotation_id: int, seller_id: int) -> list[dict[str, Any]]:
        """List all items for a quotation. Scoped to seller."""
        self._assert_quotation_owner(quotation_id, seller_id)
        rows = self._session.execute(
            text(
                """
                SELECT * FROM quotation_items
                WHERE quotation_id = :quotation_id
                ORDER BY created_at
                """
            ),
            {"quotation_id": quotation_id},
        ).mappings().all()
        return [dict(r) for r in rows]

    # ── events / history ─────────────────────────────────────────

    def list_events(self, *, quotation_id: int, seller_id: int) -> list[dict[str, Any]]:
        """List history events for a quotation. Scoped to seller."""
        self._assert_quotation_owner(quotation_id, seller_id)
        rows = self._session.execute(
            text(
                """
                SELECT * FROM quotation_events
                WHERE quotation_id = :quotation_id
                ORDER BY created_at
                """
            ),
            {"quotation_id": quotation_id},
        ).mappings().all()
        return [dict(r) for r in rows]

    def add_event(self, *, quotation_id: int, event_type: str, description: str) -> dict[str, Any]:
        """Insert a new history event (internal, no seller check)."""
        row = self._session.execute(
            text(
                """
                INSERT INTO quotation_events (quotation_id, event_type, description)
                VALUES (:quotation_id, :event_type, :description)
                RETURNING *
                """
            ),
            {
                "quotation_id": quotation_id,
                "event_type": event_type,
                "description": description,
            },
        ).mappings().one()
        self._session.commit()
        return dict(row)

    # ── submit offer ─────────────────────────────────────────────

    def submit_offer(self, *, quotation_id: int, seller_id: int) -> dict[str, Any]:
        """Mark selected items as the offer and change quotation status to OFFERED."""
        self._assert_quotation_owner(quotation_id, seller_id)

        # Get selected items
        selected = self._session.execute(
            text(
                """
                SELECT id, part_number, description, price
                FROM quotation_items
                WHERE quotation_id = :quotation_id AND selected = true
                """
            ),
            {"quotation_id": quotation_id},
        ).mappings().all()

        if not selected:
            raise ValidationError("Selecione ao menos uma peça para enviar o orçamento.")

        # Check all selected items have a price
        for item in selected:
            if item["price"] is None or float(item["price"]) <= 0:
                raise ValidationError(
                    f"Defina o preço para a peça {item['part_number']} antes de enviar."
                )

        total = sum(float(s["price"]) for s in selected)

        # Update quotation status
        self._session.execute(
            text(
                """
                UPDATE quotations
                SET status = 'OFFERED', offer_submitted = true, updated_at = now()
                WHERE id = :id AND seller_id = :seller_id AND soft_delete = false
                """
            ),
            {"id": quotation_id, "seller_id": seller_id},
        )

        # Add history event
        self._session.execute(
            text(
                """
                INSERT INTO quotation_events (quotation_id, event_type, description)
                VALUES (:quotation_id, 'offer_submitted',
                        :description)
                """
            ),
            {
                "quotation_id": quotation_id,
                "description": f"Orçamento enviado com {len(selected)} item(ns) — Total R$ {total:.2f}",
            },
        )

        self._session.commit()

        return {
            "quotation_id": quotation_id,
            "status": "OFFERED",
            "items_count": len(selected),
            "total": total,
        }

    def confirm_and_send_offer(
        self,
        *,
        quotation_id: int,
        seller_id: int,
        selected_item_ids: list[int],
        note: str | None = None,
    ) -> dict[str, Any]:
        """Persist selected items + prices and set quotation status to CONFIRMED."""
        self._assert_quotation_owner(quotation_id, seller_id)

        unique_ids = sorted({int(item_id) for item_id in selected_item_ids})
        if not unique_ids:
            raise ValidationError("Selecione ao menos uma peça para confirmar o envio.")

        selected_rows = self._session.execute(
            text(
                """
                SELECT id, part_number, price
                FROM quotation_items
                WHERE quotation_id = :quotation_id
                  AND id IN :item_ids
                """
            ).bindparams(bindparam("item_ids", expanding=True)),
            {
                "quotation_id": quotation_id,
                "item_ids": unique_ids,
            },
        ).mappings().all()

        if len(selected_rows) != len(unique_ids):
            raise ValidationError("Uma ou mais peças selecionadas não pertencem à cotação.")

        for item in selected_rows:
            if item["price"] is None or float(item["price"]) <= 0:
                raise ValidationError(
                    f"Defina o preço para a peça {item['part_number']} antes de confirmar."
                )

        total = sum(float(item["price"]) for item in selected_rows)

        self._session.execute(
            text(
                """
                UPDATE quotation_items
                SET selected = false,
                    updated_at = now()
                WHERE quotation_id = :quotation_id
                """
            ),
            {"quotation_id": quotation_id},
        )

        self._session.execute(
            text(
                """
                UPDATE quotation_items
                SET selected = true,
                    updated_at = now()
                WHERE quotation_id = :quotation_id
                  AND id IN :item_ids
                """
            ).bindparams(bindparam("item_ids", expanding=True)),
            {
                "quotation_id": quotation_id,
                "item_ids": unique_ids,
            },
        )

        self._session.execute(
            text(
                """
                UPDATE quotations
                SET status = 'CONFIRMED',
                    offer_submitted = true,
                    notes = COALESCE(NULLIF(CAST(:note AS text), ''), notes),
                    updated_at = now()
                WHERE id = :id
                  AND seller_id = :seller_id
                  AND soft_delete = false
                """
            ),
            {
                "id": quotation_id,
                "seller_id": seller_id,
                "note": note,
            },
        )

        self._session.execute(
            text(
                """
                INSERT INTO quotation_events (quotation_id, event_type, description)
                VALUES (
                    :quotation_id,
                    'quote_confirmed',
                    :description
                )
                """
            ),
            {
                "quotation_id": quotation_id,
                "description": f"Cotação confirmada com {len(unique_ids)} item(ns) — Total R$ {total:.2f}",
            },
        )

        self._session.commit()

        return {
            "quotation_id": quotation_id,
            "status": "CONFIRMED",
            "items_count": len(unique_ids),
            "total": total,
        }

    # ── helpers ──────────────────────────────────────────────────

    def _assert_quotation_owner(self, quotation_id: int, seller_id: int) -> None:
        row = self._session.execute(
            text(
                """
                SELECT 1 FROM quotations
                WHERE id = :id AND seller_id = :seller_id AND soft_delete = false
                """
            ),
            {"id": quotation_id, "seller_id": seller_id},
        ).one_or_none()
        if row is None:
            raise QuotationNotFound("Cotação não encontrada.")
