"""SQLAlchemy repository for browser-first quotation threads and offers."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.bot.domain.errors import NotFoundError, UnauthorizedError, ValidationError
from src.bot.application.services.recommendation_service import expand_requested_items


THREAD_STATUSES = {"open", "awaiting_seller_response", "offer_received", "closed"}
REQUEST_STATUSES = {"created", "processing", "ready_for_quote"}
MESSAGE_TYPES = {"text", "system", "request_summary", "offer_notice"}
OFFER_STATUSES = {"DRAFT", "SUBMITTED_OPTIONS", "FINALIZED_QUOTE", "proposal_sent", "CANCELLED"}
EDITABLE_OFFER_STATUSES = {"DRAFT", "SUBMITTED_OPTIONS"}
MECHANIC_VISIBLE_OFFER_STATUSES = {"SUBMITTED_OPTIONS", "FINALIZED_QUOTE", "proposal_sent"}


class BrowserThreadRepoSqlAlchemy:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_thread(
        self,
        *,
        mechanic_id: int,
        workshop_id: int,
        payload: dict[str, Any],
        request_status: str,
    ) -> dict[str, Any]:
        if request_status not in REQUEST_STATUSES:
            raise ValidationError("invalid request status")
        self._assert_mechanic_membership(mechanic_id=mechanic_id, workshop_id=workshop_id)

        normalized = self._normalize_thread_payload(payload)
        vehicle = normalized["vehicle"]
        requested_items = normalized["requested_items"]

        thread_row = self._session.execute(
            text(
                """
                INSERT INTO quote_threads (
                    mechanic_id,
                    workshop_id,
                    status,
                    vehicle_plate,
                    vehicle_brand,
                    vehicle_model,
                    vehicle_year,
                    vehicle_engine,
                    vehicle_version,
                    vehicle_notes
                )
                VALUES (
                    :mechanic_id,
                    :workshop_id,
                    'open',
                    :vehicle_plate,
                    :vehicle_brand,
                    :vehicle_model,
                    :vehicle_year,
                    :vehicle_engine,
                    :vehicle_version,
                    :vehicle_notes
                )
                RETURNING
                    id,
                    mechanic_id,
                    workshop_id,
                    status,
                    created_at,
                    updated_at,
                    last_message_at,
                    vehicle_plate,
                    vehicle_brand,
                    vehicle_model,
                    vehicle_year,
                    vehicle_engine,
                    vehicle_version,
                    vehicle_notes
                """
            ),
            {
                "mechanic_id": mechanic_id,
                "workshop_id": workshop_id,
                "vehicle_plate": vehicle.get("plate"),
                "vehicle_brand": vehicle.get("brand"),
                "vehicle_model": vehicle.get("model"),
                "vehicle_year": vehicle.get("year"),
                "vehicle_engine": vehicle.get("engine"),
                "vehicle_version": vehicle.get("version"),
                "vehicle_notes": vehicle.get("notes"),
            },
        ).mappings().one()

        request_row = self._session.execute(
            text(
                """
                INSERT INTO part_requests (
                    thread_id,
                    original_description,
                    requested_items_count,
                    part_number,
                    vehicle_plate,
                    vehicle_brand,
                    vehicle_model,
                    vehicle_year,
                    vehicle_engine,
                    vehicle_version,
                    vehicle_notes,
                    status
                )
                VALUES (
                    :thread_id,
                    :original_description,
                    :requested_items_count,
                    :part_number,
                    :vehicle_plate,
                    :vehicle_brand,
                    :vehicle_model,
                    :vehicle_year,
                    :vehicle_engine,
                    :vehicle_version,
                    :vehicle_notes,
                    :status
                )
                RETURNING *
                """
            ),
            {
                "thread_id": int(thread_row["id"]),
                "original_description": normalized["original_description"],
                "requested_items_count": len(requested_items),
                "part_number": normalized["part_number"],
                "vehicle_plate": vehicle.get("plate"),
                "vehicle_brand": vehicle.get("brand"),
                "vehicle_model": vehicle.get("model"),
                "vehicle_year": vehicle.get("year"),
                "vehicle_engine": vehicle.get("engine"),
                "vehicle_version": vehicle.get("version"),
                "vehicle_notes": vehicle.get("notes"),
                "status": request_status,
            },
        ).mappings().one()

        requested_item_rows: list[dict[str, Any]] = []
        for item in requested_items:
            row = self._session.execute(
                text(
                    """
                    INSERT INTO requested_items (
                        request_id,
                        description,
                        part_number,
                        quantity,
                        notes
                    )
                    VALUES (
                        :request_id,
                        :description,
                        :part_number,
                        :quantity,
                        :notes
                    )
                    RETURNING *
                    """
                ),
                {
                    "request_id": int(request_row["id"]),
                    "description": item["description"],
                    "part_number": item.get("part_number"),
                    "quantity": int(item["quantity"]),
                    "notes": item.get("notes"),
                },
            ).mappings().one()
            requested_item_rows.append(dict(row))

        message_row = self._session.execute(
            text(
                """
                INSERT INTO thread_messages (thread_id, sender_role, sender_user_ref, type, body, metadata_json)
                VALUES (
                    :thread_id,
                    'system',
                    'system',
                    'request_summary',
                    :body,
                    CAST(:metadata_json AS jsonb)
                )
                RETURNING id, thread_id, sender_role, sender_user_ref, type, body, metadata_json, created_at
                """
            ),
            {
                "thread_id": int(thread_row["id"]),
                "body": normalized["original_description"],
                "metadata_json": json.dumps(
                    {
                        "requested_items_count": len(requested_items),
                        "requested_items": [
                            {
                                "description": item["description"],
                                "quantity": item["quantity"],
                                "part_number": item.get("part_number"),
                            }
                            for item in requested_items
                        ],
                    }
                ),
            },
        ).mappings().one()

        self._session.execute(
            text(
                """
                UPDATE quote_threads
                SET last_message_at = :last_message_at,
                    updated_at = now()
                WHERE id = :thread_id
                """
            ),
            {
                "thread_id": int(thread_row["id"]),
                "last_message_at": message_row["created_at"],
            },
        )
        self._fanout_thread_to_sellers(thread_id=int(thread_row["id"]))
        self._session.commit()

        workshop = self._get_workshop_by_id(int(thread_row["workshop_id"]))
        request = self._compose_request(dict(request_row), dict(thread_row), requested_item_rows)
        return {
            "thread": dict(thread_row),
            "workshop": workshop,
            "vehicle": self._vehicle_from_thread(dict(thread_row)),
            "requested_items": requested_item_rows,
            "request": request,
            "messages": [dict(message_row)],
            "suggestions": [],
            "offers": [],
        }

    def _fanout_thread_to_sellers(self, *, thread_id: int) -> None:
        self._session.execute(
            text(
                """
                INSERT INTO seller_offers (thread_id, seller_id, seller_shop_id, status)
                SELECT
                    :thread_id,
                    v.id,
                    v.autopart_id,
                    'DRAFT'
                FROM vendors v
                WHERE v.soft_delete = false
                  AND v.active = true
                ON CONFLICT (thread_id, seller_id) DO NOTHING
                """
            ),
            {"thread_id": int(thread_id)},
        )

    def update_request_status(self, request_id: int, status: str) -> None:
        if status not in REQUEST_STATUSES:
            raise ValidationError("invalid request status")
        self._session.execute(
            text(
                """
                UPDATE part_requests
                SET status = :status
                WHERE id = :id
                """
            ),
            {"id": int(request_id), "status": status},
        )
        self._session.commit()

    def save_suggestions(
        self,
        *,
        thread_id: int,
        request_id: int,
        suggestions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for suggestion in suggestions:
            row = self._session.execute(
                text(
                    """
                    INSERT INTO suggested_parts (
                        thread_id,
                        request_id,
                        requested_item_id,
                        title,
                        brand,
                        part_number,
                        confidence,
                        note,
                        metadata_json
                    )
                    VALUES (
                        :thread_id,
                        :request_id,
                        :requested_item_id,
                        :title,
                        :brand,
                        :part_number,
                        :confidence,
                        :note,
                        CAST(:metadata_json AS jsonb)
                    )
                    RETURNING *
                    """
                ),
                {
                    "thread_id": int(thread_id),
                    "request_id": int(request_id),
                    "requested_item_id": suggestion.get("requested_item_id"),
                    "title": suggestion["title"],
                    "brand": suggestion.get("brand"),
                    "part_number": suggestion.get("part_number"),
                    "confidence": suggestion.get("confidence"),
                    "note": suggestion.get("note"),
                    "metadata_json": json.dumps(suggestion.get("metadata_json") or {}),
                },
            ).mappings().one()
            rows.append(dict(row))
        self._session.commit()
        return rows

    def list_threads(
        self,
        *,
        actor: Any,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if status is not None and status not in THREAD_STATUSES:
            raise ValidationError("invalid thread status")

        where = ["1=1"]
        params: dict[str, Any] = {"limit": int(limit), "offset": int(offset)}

        if getattr(actor, "role", None) == "mechanic":
            where.append("t.mechanic_id = :mechanic_id")
            params["mechanic_id"] = int(actor.mechanic_id)
        elif getattr(actor, "role", None) == "seller":
            where.append(
                """
                (
                    EXISTS (
                        SELECT 1
                        FROM vendor_assignments va
                        WHERE va.workshop_id = t.workshop_id
                          AND va.autopart_id = :shop_id
                          AND va.vendor_id = :vendor_id
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM seller_offers so
                        WHERE so.thread_id = t.id
                          AND so.seller_id = :vendor_id
                    )
                )
                """
            )
            params["shop_id"] = int(actor.shop_id)
            params["vendor_id"] = int(actor.vendor_id)
        elif getattr(actor, "role", None) != "admin":
            raise UnauthorizedError("not allowed")

        if status is not None:
            where.append("t.status = :status")
            params["status"] = status

        rows = self._session.execute(
            text(
                f"""
                SELECT
                    t.id,
                    t.mechanic_id,
                    t.workshop_id,
                    t.status,
                    t.created_at,
                    t.updated_at,
                    t.last_message_at,
                    t.vehicle_brand,
                    t.vehicle_model,
                    t.vehicle_year,
                    pr.id AS request_id,
                    pr.original_description,
                    pr.part_number,
                    pr.requested_items_count,
                    pr.status AS request_status,
                    w.name AS workshop_name,
                    m.name AS mechanic_name,
                    (
                        SELECT count(*)
                        FROM seller_offers so
                        WHERE so.thread_id = t.id
                          AND so.status IN ('SUBMITTED_OPTIONS', 'FINALIZED_QUOTE', 'proposal_sent')
                    ) AS submitted_offer_count
                FROM quote_threads t
                JOIN part_requests pr ON pr.thread_id = t.id
                JOIN workshops w ON w.id = t.workshop_id
                JOIN mechanics m ON m.id = t.mechanic_id
                WHERE {' AND '.join(where)}
                ORDER BY t.last_message_at DESC, t.id DESC
                LIMIT :limit
                OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_thread_detail(self, *, thread_id: int, actor: Any) -> dict[str, Any]:
        thread = self._get_visible_thread(thread_id=thread_id, actor=actor)
        request = self._get_request_by_thread(thread_id=thread_id)
        messages = self.list_messages(thread_id=thread_id, actor=actor, limit=50)
        suggestions = self.list_suggestions(thread_id=thread_id, actor=actor)
        offers = self.list_offers(thread_id=thread_id, actor=actor)
        return {
            "thread": thread,
            "workshop": self._get_workshop_by_id(int(thread["workshop_id"])),
            "vehicle": self._vehicle_from_thread(thread),
            "requested_items": request["requested_items"],
            "request": request,
            "messages": messages,
            "suggestions": suggestions,
            "offers": offers,
        }

    def list_messages(self, *, thread_id: int, actor: Any, limit: int = 100) -> list[dict[str, Any]]:
        self._get_visible_thread(thread_id=thread_id, actor=actor)
        rows = self._session.execute(
            text(
                """
                SELECT id, thread_id, sender_role, sender_user_ref, type, body, metadata_json, created_at
                FROM thread_messages
                WHERE thread_id = :thread_id
                ORDER BY created_at ASC, id ASC
                LIMIT :limit
                """
            ),
            {"thread_id": int(thread_id), "limit": int(limit)},
        ).mappings().all()
        return [dict(row) for row in rows]

    def add_message(
        self,
        *,
        thread_id: int,
        actor: Any,
        sender_role: str,
        sender_user_ref: str,
        type_: str,
        body: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if type_ not in MESSAGE_TYPES:
            raise ValidationError("invalid message type")
        self._get_visible_thread(thread_id=thread_id, actor=actor)

        row = self._session.execute(
            text(
                """
                INSERT INTO thread_messages (thread_id, sender_role, sender_user_ref, type, body, metadata_json)
                VALUES (
                    :thread_id,
                    :sender_role,
                    :sender_user_ref,
                    :type,
                    :body,
                    CAST(:metadata_json AS jsonb)
                )
                RETURNING id, thread_id, sender_role, sender_user_ref, type, body, metadata_json, created_at
                """
            ),
            {
                "thread_id": int(thread_id),
                "sender_role": sender_role,
                "sender_user_ref": sender_user_ref,
                "type": type_,
                "body": body,
                "metadata_json": json.dumps(metadata_json or {}),
            },
        ).mappings().one()

        self._session.execute(
            text(
                """
                UPDATE quote_threads
                SET updated_at = now(),
                    last_message_at = :last_message_at
                WHERE id = :thread_id
                """
            ),
            {"thread_id": int(thread_id), "last_message_at": row["created_at"]},
        )
        self._session.commit()
        return dict(row)

    def get_request(self, *, thread_id: int, actor: Any) -> dict[str, Any]:
        self._get_visible_thread(thread_id=thread_id, actor=actor)
        return self._get_request_by_thread(thread_id=thread_id)

    def list_suggestions(self, *, thread_id: int, actor: Any) -> list[dict[str, Any]]:
        self._get_visible_thread(thread_id=thread_id, actor=actor)
        rows = self._session.execute(
            text(
                """
                SELECT
                    id,
                    thread_id,
                    request_id,
                    requested_item_id,
                    title,
                    brand,
                    part_number,
                    confidence,
                    note,
                    metadata_json,
                    created_at
                FROM suggested_parts
                WHERE thread_id = :thread_id
                ORDER BY created_at ASC, id ASC
                """
            ),
            {"thread_id": int(thread_id)},
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_or_create_offer(self, *, thread_id: int, seller_id: int, seller_shop_id: int) -> dict[str, Any]:
        self._assert_seller_visible(thread_id=thread_id, seller_id=seller_id, seller_shop_id=seller_shop_id)
        row = self._session.execute(
            text(
                """
                SELECT id
                FROM seller_offers
                WHERE thread_id = :thread_id
                  AND seller_id = :seller_id
                """
            ),
            {"thread_id": int(thread_id), "seller_id": int(seller_id)},
        ).mappings().one_or_none()

        if row is None:
            row = self._session.execute(
                text(
                    """
                    INSERT INTO seller_offers (thread_id, seller_id, seller_shop_id, status)
                    VALUES (:thread_id, :seller_id, :seller_shop_id, 'DRAFT')
                    RETURNING id
                    """
                ),
                {
                    "thread_id": int(thread_id),
                    "seller_id": int(seller_id),
                    "seller_shop_id": int(seller_shop_id),
                },
            ).mappings().one()
            self._session.commit()
        return self.get_offer(offer_id=int(row["id"]), actor=self._actor_proxy("seller", seller_id, seller_shop_id))

    def list_offers(self, *, thread_id: int, actor: Any) -> list[dict[str, Any]]:
        self._get_visible_thread(thread_id=thread_id, actor=actor)
        where = ["so.thread_id = :thread_id"]
        params: dict[str, Any] = {"thread_id": int(thread_id)}
        if getattr(actor, "role", None) == "mechanic":
            where.append("so.status IN ('SUBMITTED_OPTIONS', 'FINALIZED_QUOTE', 'proposal_sent')")
        elif getattr(actor, "role", None) == "seller":
            where.append("so.seller_id = :seller_id")
            params["seller_id"] = int(actor.vendor_id)

        rows = self._session.execute(
            text(
                f"""
                SELECT
                    so.id,
                    so.thread_id,
                    so.seller_id,
                    so.seller_shop_id,
                    so.status,
                    so.notes,
                    so.total_amount,
                    so.created_at,
                    so.updated_at,
                    so.submitted_at,
                    so.finalized_at,
                    v.name AS seller_name,
                    ap.name AS seller_shop_name
                FROM seller_offers so
                JOIN vendors v ON v.id = so.seller_id
                JOIN autoparts ap ON ap.id = so.seller_shop_id
                WHERE {' AND '.join(where)}
                ORDER BY so.created_at ASC, so.id ASC
                """
            ),
            params,
        ).mappings().all()
        return [self._offer_with_items(dict(row)) for row in rows]

    def get_offer(self, *, offer_id: int, actor: Any) -> dict[str, Any]:
        row = self._get_offer_row(offer_id)
        actor_role = getattr(actor, "role", None)
        if actor_role == "mechanic":
            self._get_visible_thread(thread_id=int(row["thread_id"]), actor=actor)
            if row["status"] not in MECHANIC_VISIBLE_OFFER_STATUSES:
                raise UnauthorizedError("offer not available")
        elif actor_role == "seller":
            if int(row["seller_id"]) != int(actor.vendor_id):
                raise UnauthorizedError("offer not available")
        elif actor_role != "admin":
            raise UnauthorizedError("offer not available")

        return self._offer_with_items(dict(row))

    def add_offer_item(self, *, offer_id: int, seller_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        offer = self._assert_offer_owner(offer_id=offer_id, seller_id=seller_id)
        self._assert_offer_editable(offer)
        item_payload = self._normalize_offer_item_payload(
            offer_id=offer_id,
            thread_id=int(offer["thread_id"]),
            payload=payload,
        )
        row = self._session.execute(
            text(
                """
                INSERT INTO seller_offer_items (
                    offer_id,
                    requested_item_id,
                    source_type,
                    suggested_part_id,
                    title,
                    brand,
                    part_number,
                    quantity,
                    unit_price,
                    compatibility_note,
                    metadata_json,
                    is_final_choice
                )
                VALUES (
                    :offer_id,
                    :requested_item_id,
                    :source_type,
                    :suggested_part_id,
                    :title,
                    :brand,
                    :part_number,
                    :quantity,
                    :unit_price,
                    :compatibility_note,
                    CAST(:metadata_json AS jsonb),
                    :is_final_choice
                )
                RETURNING *
                """
            ),
            item_payload,
        ).mappings().one()
        self._touch_offer(offer_id)
        self._session.commit()
        return self._serialize_offer_item(dict(row))

    def update_offer_item(
        self,
        *,
        offer_id: int,
        item_id: int,
        seller_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        offer = self._assert_offer_owner(offer_id=offer_id, seller_id=seller_id)
        self._assert_offer_editable(offer)
        current = self._get_offer_item_row(offer_id=offer_id, item_id=item_id)

        merged_payload = {
            "requested_item_id": payload.get("requested_item_id", current.get("requested_item_id")),
            "source_type": current["source_type"],
            "suggested_part_id": current.get("suggested_part_id"),
            "description": payload.get("description", current["title"]),
            "brand": payload.get("brand", current.get("brand")),
            "part_number": payload.get("part_number", current.get("part_number")),
            "quantity": payload.get("quantity", current["quantity"]),
            "unit_price": payload.get("unit_price", current.get("unit_price")),
            "notes": payload.get("notes", current.get("compatibility_note")),
            "metadata_json": payload.get("metadata_json", current.get("metadata_json") or {}),
            "is_final_choice": payload.get("is_final_choice", current.get("is_final_choice", False)),
        }
        normalized = self._normalize_offer_item_payload(
            offer_id=offer_id,
            thread_id=int(offer["thread_id"]),
            payload=merged_payload,
        )

        row = self._session.execute(
            text(
                """
                UPDATE seller_offer_items
                SET requested_item_id = :requested_item_id,
                    title = :title,
                    brand = :brand,
                    part_number = :part_number,
                    quantity = :quantity,
                    unit_price = :unit_price,
                    compatibility_note = :compatibility_note,
                    metadata_json = CAST(:metadata_json AS jsonb),
                    is_final_choice = :is_final_choice,
                    updated_at = now()
                WHERE id = :item_id
                  AND offer_id = :offer_id
                RETURNING *
                """
            ),
            {
                "item_id": int(item_id),
                "offer_id": int(offer_id),
                **normalized,
            },
        ).mappings().one_or_none()
        if row is None:
            raise NotFoundError("offer item not found")
        self._touch_offer(offer_id)
        self._session.commit()
        return self._serialize_offer_item(dict(row))

    def delete_offer_item(self, *, offer_id: int, item_id: int, seller_id: int) -> None:
        offer = self._assert_offer_owner(offer_id=offer_id, seller_id=seller_id)
        self._assert_offer_editable(offer)
        result = self._session.execute(
            text(
                """
                DELETE FROM seller_offer_items
                WHERE id = :item_id
                  AND offer_id = :offer_id
                """
            ),
            {"item_id": int(item_id), "offer_id": int(offer_id)},
        )
        if result.rowcount == 0:
            raise NotFoundError("offer item not found")
        self._touch_offer(offer_id)
        self._session.commit()

    def submit_offer(
        self,
        *,
        offer_id: int,
        seller_id: int,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if (payload or {}).get("close_quote"):
            return self._submit_final_proposal(
                offer_id=offer_id,
                seller_id=seller_id,
                payload=payload,
            )

        offer = self._assert_offer_owner(offer_id=offer_id, seller_id=seller_id)
        self._assert_offer_editable(offer)

        items = self._fetch_offer_item_rows(offer_id=offer_id)
        self._validate_offer_items_for_submission(items)
        groups, _ = self._build_offer_groups(thread_id=int(offer["thread_id"]), item_rows=items)
        summary_text = self._build_offer_summary("SUBMITTED_OPTIONS", groups)

        row = self._session.execute(
            text(
                """
                UPDATE seller_offers
                SET status = 'SUBMITTED_OPTIONS',
                    total_amount = NULL,
                    finalized_at = NULL,
                    submitted_at = now(),
                    updated_at = now()
                WHERE id = :offer_id
                RETURNING *
                """
            ),
            {"offer_id": int(offer_id)},
        ).mappings().one()

        notice_row = self._insert_offer_notice(
            thread_id=int(offer["thread_id"]),
            seller_id=seller_id,
            offer_id=offer_id,
            body=summary_text,
            metadata_json={
                "offer_id": int(offer_id),
                "seller_id": int(seller_id),
                "status": "SUBMITTED_OPTIONS",
            },
        )

        self._session.execute(
            text(
                """
                UPDATE quote_threads
                SET status = 'offer_received',
                    updated_at = now(),
                    last_message_at = :last_message_at
                WHERE id = :thread_id
                """
            ),
            {"thread_id": int(offer["thread_id"]), "last_message_at": notice_row["created_at"]},
        )
        self._session.commit()
        return self._build_submit_response(
            offer_id=int(row["id"]),
            seller_id=seller_id,
            seller_shop_id=int(offer["seller_shop_id"]),
            thread_status="offer_received",
        )

    def _submit_final_proposal(
        self,
        *,
        offer_id: int,
        seller_id: int,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        offer = self._assert_offer_owner(offer_id=offer_id, seller_id=seller_id)
        self._assert_offer_editable(offer)

        items = self._fetch_offer_item_rows(offer_id=offer_id)
        self._validate_offer_items_for_submission(items)
        selected_ids = self._resolve_proposal_item_ids(
            items=items,
            explicit_ids=(payload or {}).get("selected_option_ids"),
        )

        self._session.execute(
            text(
                """
                UPDATE seller_offer_items
                SET is_final_choice = (id = ANY(CAST(:selected_ids AS bigint[]))),
                    updated_at = now()
                WHERE offer_id = :offer_id
                """
            ),
            {"offer_id": int(offer_id), "selected_ids": selected_ids},
        )

        selected_rows = [item for item in items if int(item["id"]) in selected_ids]
        final_total = round(
            sum(int(item["quantity"]) * float(item["unit_price"]) for item in selected_rows),
            2,
        )
        groups, _ = self._build_offer_groups(
            thread_id=int(offer["thread_id"]),
            item_rows=self._fetch_offer_item_rows(offer_id=offer_id),
        )
        summary_text = self._build_offer_summary("proposal_sent", groups)

        row = self._session.execute(
            text(
                """
                UPDATE seller_offers
                SET status = 'proposal_sent',
                    total_amount = :final_total,
                    submitted_at = now(),
                    finalized_at = now(),
                    updated_at = now()
                WHERE id = :offer_id
                RETURNING *
                """
            ),
            {"offer_id": int(offer_id), "final_total": final_total},
        ).mappings().one()
        service_order_id = self._service_order_public_id(int(row["id"]))

        notice_row = self._insert_offer_notice(
            thread_id=int(offer["thread_id"]),
            seller_id=seller_id,
            offer_id=offer_id,
            body=summary_text,
            metadata_json={
                "offer_id": int(offer_id),
                "seller_id": int(seller_id),
                "status": "proposal_sent",
                "total_amount": final_total,
                "service_order_id": service_order_id,
                "selected_option_ids": selected_ids,
            },
        )

        self._session.execute(
            text(
                """
                UPDATE quote_threads
                SET status = 'closed',
                    updated_at = now(),
                    last_message_at = :last_message_at
                WHERE id = :thread_id
                """
            ),
            {"thread_id": int(offer["thread_id"]), "last_message_at": notice_row["created_at"]},
        )
        self._session.commit()
        return self._build_submit_response(
            offer_id=int(row["id"]),
            seller_id=seller_id,
            seller_shop_id=int(offer["seller_shop_id"]),
            thread_status="closed",
            service_order_id=service_order_id,
        )

    def finalize_offer(
        self,
        *,
        offer_id: int,
        seller_id: int,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        offer = self._assert_offer_owner(offer_id=offer_id, seller_id=seller_id)
        self._assert_offer_editable(offer)

        items = self._fetch_offer_item_rows(offer_id=offer_id)
        self._validate_offer_items_for_submission(items)
        selected_ids = self._resolve_final_choice_ids(
            offer_id=offer_id,
            items=items,
            explicit_ids=(payload or {}).get("selected_option_ids"),
        )

        self._session.execute(
            text(
                """
                UPDATE seller_offer_items
                SET is_final_choice = (id = ANY(CAST(:selected_ids AS bigint[]))),
                    updated_at = now()
                WHERE offer_id = :offer_id
                """
            ),
            {"offer_id": int(offer_id), "selected_ids": selected_ids},
        )

        selected_rows = [item for item in items if int(item["id"]) in selected_ids]
        final_total = round(
            sum(int(item["quantity"]) * float(item["unit_price"]) for item in selected_rows),
            2,
        )
        groups, _ = self._build_offer_groups(thread_id=int(offer["thread_id"]), item_rows=self._fetch_offer_item_rows(offer_id=offer_id))
        summary_text = self._build_offer_summary("FINALIZED_QUOTE", groups)

        row = self._session.execute(
            text(
                """
                UPDATE seller_offers
                SET status = 'FINALIZED_QUOTE',
                    total_amount = :final_total,
                    submitted_at = COALESCE(submitted_at, now()),
                    finalized_at = now(),
                    updated_at = now()
                WHERE id = :offer_id
                RETURNING *
                """
            ),
            {"offer_id": int(offer_id), "final_total": final_total},
        ).mappings().one()

        notice_row = self._insert_offer_notice(
            thread_id=int(offer["thread_id"]),
            seller_id=seller_id,
            offer_id=offer_id,
            body=summary_text,
            metadata_json={
                "offer_id": int(offer_id),
                "seller_id": int(seller_id),
                "status": "FINALIZED_QUOTE",
                "final_total": final_total,
                "selected_option_ids": selected_ids,
            },
        )

        self._session.execute(
            text(
                """
                UPDATE quote_threads
                SET status = 'offer_received',
                    updated_at = now(),
                    last_message_at = :last_message_at
                WHERE id = :thread_id
                """
            ),
            {"thread_id": int(offer["thread_id"]), "last_message_at": notice_row["created_at"]},
        )
        self._session.commit()
        return self.get_offer(offer_id=int(row["id"]), actor=self._actor_proxy("seller", seller_id, int(offer["seller_shop_id"])))

    def list_service_orders(self, *, mechanic_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            text(
                """
                SELECT
                    so.id AS offer_id,
                    so.thread_id,
                    so.status,
                    t.status AS thread_status,
                    so.total_amount,
                    so.created_at,
                    so.submitted_at,
                    pr.original_description AS title,
                    w.name AS workshop_name,
                    t.vehicle_brand,
                    t.vehicle_model,
                    t.vehicle_year,
                    t.vehicle_engine,
                    t.vehicle_version,
                    ap.name AS auto_parts_name,
                    v.name AS seller_name
                FROM seller_offers so
                JOIN quote_threads t ON t.id = so.thread_id
                JOIN part_requests pr ON pr.thread_id = t.id
                JOIN workshops w ON w.id = t.workshop_id
                JOIN autoparts ap ON ap.id = so.seller_shop_id
                JOIN vendors v ON v.id = so.seller_id
                WHERE t.mechanic_id = :mechanic_id
                  AND (
                    so.status = 'proposal_sent'
                    OR (so.status = 'SUBMITTED_OPTIONS' AND t.status = 'closed')
                  )
                ORDER BY so.submitted_at DESC NULLS LAST, so.id DESC
                """
            ),
            {"mechanic_id": int(mechanic_id)},
        ).mappings().all()
        return [self._build_service_order_list_item(dict(row)) for row in rows]

    def get_service_order(self, *, service_order_id: str, mechanic_id: int) -> dict[str, Any]:
        offer_id = self._parse_service_order_id(service_order_id)
        row = self._session.execute(
            text(
                """
                SELECT
                    so.id AS offer_id,
                    so.thread_id,
                    so.status,
                    t.status AS thread_status,
                    so.total_amount,
                    so.created_at,
                    so.submitted_at,
                    pr.original_description AS title,
                    w.name AS workshop_name,
                    t.vehicle_brand,
                    t.vehicle_model,
                    t.vehicle_year,
                    t.vehicle_engine,
                    t.vehicle_version,
                    ap.name AS auto_parts_name,
                    ap.whatsapp_phone_e164 AS auto_parts_phone,
                    ap.address AS auto_parts_address,
                    v.name AS seller_name
                FROM seller_offers so
                JOIN quote_threads t ON t.id = so.thread_id
                JOIN part_requests pr ON pr.thread_id = t.id
                JOIN workshops w ON w.id = t.workshop_id
                JOIN autoparts ap ON ap.id = so.seller_shop_id
                JOIN vendors v ON v.id = so.seller_id
                WHERE so.id = :offer_id
                  AND t.mechanic_id = :mechanic_id
                  AND (
                    so.status = 'proposal_sent'
                    OR (so.status = 'SUBMITTED_OPTIONS' AND t.status = 'closed')
                  )
                """
            ),
            {"offer_id": int(offer_id), "mechanic_id": int(mechanic_id)},
        ).mappings().one_or_none()
        if row is None:
            raise NotFoundError("service order not found")

        base = dict(row)
        request = self._get_request_by_thread(thread_id=int(base["thread_id"]))
        items = self._serialize_service_order_items(offer_id=int(base["offer_id"]))
        total_amount = round(float(base["total_amount"]), 2) if base.get("total_amount") is not None else round(
            sum(item["line_total"] for item in items),
            2,
        )
        return {
            "id": self._service_order_public_id(int(base["offer_id"])),
            "thread_id": int(base["thread_id"]),
            "offer_id": int(base["offer_id"]),
            "status": self._normalize_service_order_status(base),
            "title": base["title"],
            "created_at": base["created_at"],
            "submitted_at": base["submitted_at"],
            "workshop_name": base.get("workshop_name"),
            "vehicle_summary": self._vehicle_summary(base),
            "request_notes": self._build_request_notes(request.get("requested_items") or []),
            "auto_parts": {
                "name": base.get("auto_parts_name"),
                "phone": base.get("auto_parts_phone"),
                "address": base.get("auto_parts_address"),
            },
            "seller": {
                "name": base.get("seller_name"),
                "phone": None,
            },
            "items": items,
            "total_amount": total_amount,
        }

    def _build_submit_response(
        self,
        *,
        offer_id: int,
        seller_id: int,
        seller_shop_id: int,
        thread_status: str,
        service_order_id: str | None = None,
    ) -> dict[str, Any]:
        payload = self.get_offer(
            offer_id=offer_id,
            actor=self._actor_proxy("seller", seller_id, seller_shop_id),
        )
        payload["offer_id"] = int(payload["id"])
        payload["thread_status"] = thread_status
        payload["service_order_id"] = service_order_id
        return payload

    def get_comparison(self, *, thread_id: int, mechanic_id: int) -> dict[str, Any]:
        actor = self._actor_proxy("mechanic", mechanic_id, None, mechanic_id=mechanic_id)
        thread = self._get_visible_thread(thread_id=thread_id, actor=actor)
        request = self._get_request_by_thread(thread_id=thread_id)
        offers = self.list_offers(thread_id=thread_id, actor=actor)
        return {
            "thread_id": int(thread["id"]),
            "vehicle": self._vehicle_from_thread(thread),
            "requested_items": request["requested_items"],
            "request": request,
            "offers": [
                {
                    "offer_id": offer["id"],
                    "seller_id": offer["seller_id"],
                    "seller_name": offer["seller_name"],
                    "seller_shop_id": offer["seller_shop_id"],
                    "seller_shop_name": offer["seller_shop_name"],
                    "status": offer["status"],
                    "summary_text": offer["summary_text"],
                    "final_total": offer["final_total"],
                    "total_amount": offer["total_amount"],
                    "submitted_at": offer["submitted_at"],
                    "finalized_at": offer.get("finalized_at"),
                    "groups": offer["groups"],
                    "items": offer["items"],
                    "notes": offer["notes"],
                }
                for offer in offers
            ],
        }

    def seller_inbox_list(
        self,
        *,
        seller_id: int,
        shop_id: int,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_page = max(1, page)
        safe_size = max(1, min(page_size, 100))
        actor = self._actor_proxy("seller", seller_id, shop_id)
        rows = self.list_threads(
            actor=actor,
            status=status,
            limit=safe_size,
            offset=(safe_page - 1) * safe_size,
        )
        if search:
            lowered = search.lower()
            rows = [
                row
                for row in rows
                if lowered in (row.get("original_description") or "").lower()
                or lowered in (row.get("part_number") or "").lower()
                or lowered in (row.get("workshop_name") or "").lower()
            ]
        return rows, len(rows)

    def seller_inbox_get(self, *, thread_id: int, seller_id: int, shop_id: int) -> dict[str, Any]:
        actor = self._actor_proxy("seller", seller_id, shop_id)
        return self.get_thread_detail(thread_id=thread_id, actor=actor)

    def update_thread_status_for_seller(
        self,
        *,
        thread_id: int,
        seller_id: int,
        shop_id: int,
        new_status: str,
    ) -> None:
        if new_status not in THREAD_STATUSES:
            raise ValidationError("invalid thread status")
        self._assert_seller_visible(thread_id=thread_id, seller_id=seller_id, seller_shop_id=shop_id)
        self._session.execute(
            text(
                """
                UPDATE quote_threads
                SET status = :status,
                    updated_at = now()
                WHERE id = :thread_id
                """
            ),
            {"thread_id": int(thread_id), "status": new_status},
        )
        self._session.commit()

    def _normalize_thread_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        requested_items = payload.get("requested_items") or []
        if not requested_items:
            original_description = payload.get("original_description")
            if not original_description:
                raise ValidationError("at least one requested item is required")
            requested_items = [
                {
                    "description": original_description,
                    "part_number": payload.get("part_number"),
                    "quantity": int(payload.get("requested_items_count") or 1),
                    "notes": None,
                }
            ]

        normalized_items: list[dict[str, Any]] = []
        for item in expand_requested_items(requested_items, payload.get("vehicle") or {}):
            description = str(item.get("description") or "").strip()
            if not description:
                raise ValidationError("requested item description is required")
            quantity = int(item.get("quantity") or 0)
            if quantity <= 0:
                raise ValidationError("requested item quantity must be positive")
            normalized_items.append(
                {
                    "description": description,
                    "part_number": item.get("part_number"),
                    "quantity": quantity,
                    "notes": item.get("notes"),
                }
            )

        vehicle = payload.get("vehicle") or {}
        if not vehicle:
            vehicle = {
                "plate": payload.get("vehicle_plate"),
                "brand": payload.get("vehicle_brand"),
                "model": payload.get("vehicle_model"),
                "year": payload.get("vehicle_year"),
                "engine": payload.get("vehicle_engine"),
                "version": payload.get("vehicle_version"),
                "notes": payload.get("vehicle_notes"),
            }

        original_description = payload.get("original_description") or self._build_requested_items_text(normalized_items)
        part_number = normalized_items[0].get("part_number") if len(normalized_items) == 1 else None
        return {
            "requested_items": normalized_items,
            "vehicle": vehicle,
            "original_description": original_description,
            "part_number": part_number,
        }

    @staticmethod
    def _build_requested_items_text(requested_items: list[dict[str, Any]]) -> str:
        parts = []
        for item in requested_items:
            description = str(item["description"]).strip()
            quantity = int(item["quantity"])
            suffix = f" ({quantity}x)" if quantity > 1 else ""
            parts.append(f"{description}{suffix}")
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0]
        if len(parts) == 2:
            return f"{parts[0]} e {parts[1]}"
        return ", ".join(parts[:-1]) + f" e {parts[-1]}"

    def _compose_request(
        self,
        request_row: dict[str, Any],
        thread_row: dict[str, Any],
        requested_items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        request = dict(request_row)
        request["requested_items"] = requested_items
        request["requested_items_count"] = len(requested_items)
        request["part_number"] = requested_items[0].get("part_number") if len(requested_items) == 1 else None
        request["vehicle"] = self._vehicle_from_thread(thread_row)
        request["vehicle_plate"] = thread_row.get("vehicle_plate")
        request["vehicle_brand"] = thread_row.get("vehicle_brand")
        request["vehicle_model"] = thread_row.get("vehicle_model")
        request["vehicle_year"] = thread_row.get("vehicle_year")
        request["vehicle_engine"] = thread_row.get("vehicle_engine")
        request["vehicle_version"] = thread_row.get("vehicle_version")
        request["vehicle_notes"] = thread_row.get("vehicle_notes")
        request["original_description"] = request.get("original_description") or self._build_requested_items_text(requested_items)
        return request

    @staticmethod
    def _vehicle_from_thread(thread_row: dict[str, Any]) -> dict[str, Any]:
        return {
            "plate": thread_row.get("vehicle_plate"),
            "brand": thread_row.get("vehicle_brand"),
            "model": thread_row.get("vehicle_model"),
            "year": thread_row.get("vehicle_year"),
            "engine": thread_row.get("vehicle_engine"),
            "version": thread_row.get("vehicle_version"),
            "notes": thread_row.get("vehicle_notes"),
        }

    def _get_offer_row(self, offer_id: int) -> dict[str, Any]:
        row = self._session.execute(
            text(
                """
                SELECT
                    so.id,
                    so.thread_id,
                    so.seller_id,
                    so.seller_shop_id,
                    so.status,
                    so.notes,
                    so.total_amount,
                    so.created_at,
                    so.updated_at,
                    so.submitted_at,
                    so.finalized_at,
                    v.name AS seller_name,
                    ap.name AS seller_shop_name
                FROM seller_offers so
                JOIN vendors v ON v.id = so.seller_id
                JOIN autoparts ap ON ap.id = so.seller_shop_id
                WHERE so.id = :offer_id
                """
            ),
            {"offer_id": int(offer_id)},
        ).mappings().one_or_none()
        if row is None:
            raise NotFoundError("offer not found")
        return dict(row)

    def _offer_with_items(self, row: dict[str, Any]) -> dict[str, Any]:
        item_rows = self._fetch_offer_item_rows(offer_id=int(row["id"]))
        groups, flat_items = self._build_offer_groups(thread_id=int(row["thread_id"]), item_rows=item_rows)
        final_total = None
        if row["status"] in {"FINALIZED_QUOTE", "proposal_sent"} and row.get("total_amount") is not None:
            final_total = round(float(row["total_amount"]), 2)
        row["seller_store"] = {
            "id": int(row["seller_shop_id"]),
            "name": row["seller_shop_name"],
        }
        row["seller_user"] = {
            "id": int(row["seller_id"]),
            "name": row["seller_name"],
        }
        row["summary_text"] = self._build_offer_summary(row["status"], groups)
        row["groups"] = groups
        row["items"] = flat_items
        row["final_total"] = final_total
        row["total_amount"] = final_total
        return row

    def _build_offer_groups(
        self,
        *,
        thread_id: int,
        item_rows: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        request = self._get_request_by_thread(thread_id=thread_id)
        requested_items = request["requested_items"]
        requested_item_map = {int(item["id"]): item for item in requested_items}
        options_by_requested_item: dict[int, list[dict[str, Any]]] = {int(item["id"]): [] for item in requested_items}
        flat_items: list[dict[str, Any]] = []

        fallback_requested_item_id = int(requested_items[0]["id"]) if len(requested_items) == 1 else None
        for row in item_rows:
            requested_item_id = row.get("requested_item_id")
            if requested_item_id is None:
                requested_item_id = fallback_requested_item_id
            if requested_item_id is None or int(requested_item_id) not in requested_item_map:
                continue
            serialized = self._serialize_offer_item({**row, "requested_item_id": int(requested_item_id)})
            options_by_requested_item[int(requested_item_id)].append(serialized)
            flat_items.append(serialized)

        groups: list[dict[str, Any]] = []
        for requested_item in requested_items:
            item_id = int(requested_item["id"])
            groups.append(
                {
                    "requested_item_id": item_id,
                    "requested_item_description": requested_item["description"],
                    "requested_quantity": int(requested_item["quantity"]),
                    "options": options_by_requested_item[item_id],
                }
            )
        return groups, flat_items

    @staticmethod
    def _serialize_offer_item(row: dict[str, Any]) -> dict[str, Any]:
        description = row.get("title")
        notes = row.get("compatibility_note")
        return {
            "id": int(row["id"]),
            "offer_id": int(row["offer_id"]),
            "requested_item_id": int(row["requested_item_id"]) if row.get("requested_item_id") is not None else None,
            "source_type": row["source_type"],
            "suggested_part_id": int(row["suggested_part_id"]) if row.get("suggested_part_id") is not None else None,
            "description": description,
            "title": description,
            "brand": row.get("brand"),
            "part_number": row.get("part_number"),
            "quantity": int(row["quantity"]),
            "unit_price": None if row.get("unit_price") is None else round(float(row["unit_price"]), 2),
            "notes": notes,
            "compatibility_note": notes,
            "metadata_json": row.get("metadata_json") or {},
            "is_final_choice": bool(row.get("is_final_choice", False)),
            "created_at": row["created_at"],
            "updated_at": row.get("updated_at"),
        }

    def _build_offer_summary(self, status: str, groups: list[dict[str, Any]]) -> str | None:
        if status == "DRAFT":
            return None

        parts: list[str] = []
        for group in groups:
            if status in {"FINALIZED_QUOTE", "proposal_sent"}:
                count = len([option for option in group["options"] if option.get("is_final_choice")])
                noun = "item selecionado" if count == 1 else "itens selecionados"
            else:
                count = len(group["options"])
                noun = "opção" if count == 1 else "opções"
            if count <= 0:
                continue
            parts.append(f"{count} {noun} para {group['requested_item_description']}")

        if not parts:
            return None
        if len(parts) == 1:
            suffix = parts[0]
        elif len(parts) == 2:
            suffix = f"{parts[0]} e {parts[1]}"
        else:
            suffix = ", ".join(parts[:-1]) + f" e {parts[-1]}"

        if status == "FINALIZED_QUOTE":
            return f"Orçamento final consolidado com {suffix}."
        if status == "proposal_sent":
            return f"Orçamento enviado com {suffix}."
        return f"Resposta enviada com {suffix}."

    def _build_service_order_list_item(self, row: dict[str, Any]) -> dict[str, Any]:
        items = self._serialize_service_order_items(offer_id=int(row["offer_id"]))
        total_amount = round(float(row["total_amount"]), 2) if row.get("total_amount") is not None else round(
            sum(item["line_total"] for item in items),
            2,
        )
        return {
            "id": self._service_order_public_id(int(row["offer_id"])),
            "thread_id": int(row["thread_id"]),
            "offer_id": int(row["offer_id"]),
            "status": self._normalize_service_order_status(row),
            "title": row["title"],
            "workshop_name": row.get("workshop_name"),
            "vehicle_summary": self._vehicle_summary(row),
            "total_amount": total_amount,
            "item_count": len(items),
            "created_at": row["created_at"],
            "submitted_at": row["submitted_at"],
            "auto_parts_name": row.get("auto_parts_name"),
            "seller_name": row.get("seller_name"),
        }

    def _fetch_offer_item_rows(self, *, offer_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            text(
                """
                SELECT
                    id,
                    offer_id,
                    requested_item_id,
                    source_type,
                    suggested_part_id,
                    title,
                    brand,
                    part_number,
                    quantity,
                    unit_price,
                    compatibility_note,
                    metadata_json,
                    is_final_choice,
                    created_at,
                    updated_at
                FROM seller_offer_items
                WHERE offer_id = :offer_id
                ORDER BY id ASC
                """
            ),
            {"offer_id": int(offer_id)},
        ).mappings().all()
        return [dict(row) for row in rows]

    def _fetch_service_order_item_rows(self, *, offer_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            text(
                """
                SELECT
                    soi.id,
                    soi.offer_id,
                    soi.requested_item_id,
                    ri.description AS requested_item_label,
                    soi.title,
                    soi.brand,
                    soi.part_number,
                    soi.quantity,
                    soi.unit_price,
                    soi.compatibility_note,
                    soi.is_final_choice
                FROM seller_offer_items soi
                LEFT JOIN requested_items ri ON ri.id = soi.requested_item_id
                WHERE soi.offer_id = :offer_id
                ORDER BY soi.created_at ASC, soi.id ASC
                """
            ),
            {"offer_id": int(offer_id)},
        ).mappings().all()
        items = [dict(row) for row in rows]
        if any(bool(row.get("is_final_choice")) for row in items):
            return [row for row in items if bool(row.get("is_final_choice"))]
        return items

    def _serialize_service_order_items(self, *, offer_id: int) -> list[dict[str, Any]]:
        rows = self._fetch_service_order_item_rows(offer_id=offer_id)
        serialized: list[dict[str, Any]] = []
        for row in rows:
            unit_price = 0.0 if row.get("unit_price") is None else round(float(row["unit_price"]), 2)
            quantity = int(row["quantity"])
            serialized.append(
                {
                    "id": f"line_{int(row['id'])}",
                    "requested_item_id": int(row["requested_item_id"]) if row.get("requested_item_id") is not None else None,
                    "requested_item_label": row.get("requested_item_label"),
                    "description": row["title"],
                    "brand": row.get("brand"),
                    "part_number": row.get("part_number"),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_total": round(quantity * unit_price, 2),
                    "notes": row.get("compatibility_note"),
                }
            )
        return serialized

    def _get_request_by_thread(self, *, thread_id: int) -> dict[str, Any]:
        row = self._session.execute(
            text(
                """
                SELECT
                    pr.*,
                    t.vehicle_plate,
                    t.vehicle_brand,
                    t.vehicle_model,
                    t.vehicle_year,
                    t.vehicle_engine,
                    t.vehicle_version,
                    t.vehicle_notes
                FROM part_requests pr
                JOIN quote_threads t ON t.id = pr.thread_id
                WHERE pr.thread_id = :thread_id
                """
            ),
            {"thread_id": int(thread_id)},
        ).mappings().one_or_none()
        if row is None:
            raise NotFoundError("request not found")

        request_row = dict(row)
        requested_items = self._session.execute(
            text(
                """
                SELECT *
                FROM requested_items
                WHERE request_id = :request_id
                ORDER BY id ASC
                """
            ),
            {"request_id": int(request_row["id"])},
        ).mappings().all()
        return self._compose_request(request_row, request_row, [dict(item) for item in requested_items])

    def _get_workshop_by_id(self, workshop_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            text(
                """
                SELECT
                    id,
                    name,
                    whatsapp_phone_e164 AS phone,
                    address
                FROM workshops
                WHERE id = :workshop_id
                  AND soft_delete = false
                """
            ),
            {"workshop_id": int(workshop_id)},
        ).mappings().one_or_none()
        return None if row is None else dict(row)

    def _assert_offer_owner(self, *, offer_id: int, seller_id: int) -> dict[str, Any]:
        row = self._session.execute(
            text(
                """
                SELECT *
                FROM seller_offers
                WHERE id = :offer_id
                  AND seller_id = :seller_id
                """
            ),
            {"offer_id": int(offer_id), "seller_id": int(seller_id)},
        ).mappings().one_or_none()
        if row is None:
            raise UnauthorizedError("offer not available")
        return dict(row)

    def _assert_offer_editable(self, offer: dict[str, Any]) -> None:
        if offer["status"] not in EDITABLE_OFFER_STATUSES:
            raise ValidationError("only draft or submitted option offers can be edited")

    def _get_offer_item_row(self, *, offer_id: int, item_id: int) -> dict[str, Any]:
        row = self._session.execute(
            text(
                """
                SELECT *
                FROM seller_offer_items
                WHERE id = :item_id
                  AND offer_id = :offer_id
                """
            ),
            {"item_id": int(item_id), "offer_id": int(offer_id)},
        ).mappings().one_or_none()
        if row is None:
            raise NotFoundError("offer item not found")
        return dict(row)

    def _normalize_offer_item_payload(
        self,
        *,
        offer_id: int,
        thread_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        source_type = str(payload["source_type"]).strip().lower()
        if source_type not in {"suggested", "manual"}:
            raise ValidationError("source_type must be manual or suggested")

        requested_items = self._get_request_by_thread(thread_id=thread_id)["requested_items"]
        requested_item_ids = {int(item["id"]) for item in requested_items}
        requested_item_id = payload.get("requested_item_id")
        if requested_item_id is None and len(requested_item_ids) == 1:
            requested_item_id = next(iter(requested_item_ids))
        if requested_item_id is None or int(requested_item_id) not in requested_item_ids:
            raise ValidationError("requested_item_id is required and must belong to the thread")

        quantity = int(payload.get("quantity") or 1)
        if quantity <= 0:
            raise ValidationError("quantity must be positive")

        unit_price = payload.get("unit_price")
        if unit_price is not None and float(unit_price) < 0:
            raise ValidationError("unit_price must be zero or positive")

        title = payload.get("description") or payload.get("title")
        brand = payload.get("brand")
        part_number = payload.get("part_number")
        suggested_part_id = payload.get("suggested_part_id")
        if source_type == "suggested":
            if suggested_part_id is None:
                raise ValidationError("suggested_part_id is required for suggested items")
            suggestion = self._session.execute(
                text(
                    """
                    SELECT id, requested_item_id, title, brand, part_number
                    FROM suggested_parts
                    WHERE id = :id
                      AND thread_id = :thread_id
                    """
                ),
                {"id": int(suggested_part_id), "thread_id": int(thread_id)},
            ).mappings().one_or_none()
            if suggestion is None:
                raise ValidationError("invalid suggested_part_id")
            suggestion_requested_item_id = suggestion.get("requested_item_id")
            if suggestion_requested_item_id is not None and int(suggestion_requested_item_id) != int(requested_item_id):
                raise ValidationError("suggested_part_id does not belong to the requested item")
            title = title or suggestion["title"]
            brand = brand or suggestion["brand"]
            part_number = part_number or suggestion["part_number"]
        if not title:
            raise ValidationError("description is required")

        return {
            "offer_id": int(offer_id),
            "requested_item_id": int(requested_item_id),
            "source_type": source_type,
            "suggested_part_id": int(suggested_part_id) if suggested_part_id is not None else None,
            "title": title,
            "brand": brand,
            "part_number": part_number,
            "quantity": quantity,
            "unit_price": unit_price,
            "compatibility_note": payload.get("notes") or payload.get("compatibility_note"),
            "metadata_json": json.dumps(payload.get("metadata_json") or {}),
            "is_final_choice": bool(payload.get("is_final_choice", False)),
        }

    @staticmethod
    def _validate_offer_items_for_submission(items: list[dict[str, Any]]) -> None:
        if not items:
            raise ValidationError("submitted offer must contain at least one option")
        for item in items:
            quantity = int(item["quantity"])
            if quantity <= 0:
                raise ValidationError("item quantity must be positive")
            if item["unit_price"] is None or float(item["unit_price"]) <= 0:
                raise ValidationError(f"item {item['title']} must have a positive unit price")

    def _resolve_final_choice_ids(
        self,
        *,
        offer_id: int,
        items: list[dict[str, Any]],
        explicit_ids: list[int] | None,
    ) -> list[int]:
        item_map = {int(item["id"]): item for item in items}
        selected_ids = explicit_ids if explicit_ids is not None else [int(item["id"]) for item in items if item.get("is_final_choice")]
        if not selected_ids:
            raise ValidationError("finalized quote must select at least one option")

        seen_requested_items: set[int] = set()
        normalized_ids: list[int] = []
        requested_items = self._get_request_by_thread(thread_id=int(self._get_offer_row(int(offer_id))["thread_id"]))["requested_items"]
        fallback_requested_item_id = int(requested_items[0]["id"]) if len(requested_items) == 1 else None
        for raw_id in selected_ids:
            item = item_map.get(int(raw_id))
            if item is None:
                raise ValidationError("selected option must belong to the offer")
            requested_item_id = item.get("requested_item_id")
            if requested_item_id is None:
                requested_item_id = fallback_requested_item_id
            if requested_item_id is None:
                raise ValidationError("selected option must be linked to a requested item")
            requested_item_id = int(requested_item_id)
            if requested_item_id in seen_requested_items:
                raise ValidationError("only one final choice is allowed per requested item")
            if item["unit_price"] is None or float(item["unit_price"]) <= 0:
                raise ValidationError(f"item {item['title']} must have a positive unit price")
            seen_requested_items.add(requested_item_id)
            normalized_ids.append(int(raw_id))
        return normalized_ids

    @staticmethod
    def _resolve_proposal_item_ids(
        *,
        items: list[dict[str, Any]],
        explicit_ids: list[int] | None,
    ) -> list[int]:
        item_map = {int(item["id"]): item for item in items}
        selected_ids = explicit_ids if explicit_ids is not None else [int(item["id"]) for item in items if item.get("is_final_choice")]
        if not selected_ids:
            selected_ids = [int(item["id"]) for item in items]

        normalized_ids: list[int] = []
        seen_ids: set[int] = set()
        for raw_id in selected_ids:
            item = item_map.get(int(raw_id))
            if item is None:
                raise ValidationError("selected option must belong to the offer")
            if int(raw_id) in seen_ids:
                continue
            if item["unit_price"] is None or float(item["unit_price"]) <= 0:
                raise ValidationError(f"item {item['title']} must have a positive unit price")
            normalized_ids.append(int(raw_id))
            seen_ids.add(int(raw_id))
        return normalized_ids

    @staticmethod
    def _service_order_public_id(offer_id: int) -> str:
        return f"so_{int(offer_id)}"

    @staticmethod
    def _parse_service_order_id(service_order_id: str) -> int:
        value = str(service_order_id).strip()
        if value.startswith("so_"):
            value = value[3:]
        if not value.isdigit():
            raise ValidationError("invalid service order id")
        return int(value)

    @staticmethod
    def _vehicle_summary(row: dict[str, Any]) -> str | None:
        values = [
            row.get("vehicle_brand"),
            row.get("vehicle_model"),
            row.get("vehicle_year"),
            row.get("vehicle_engine"),
            row.get("vehicle_version"),
        ]
        parts = [str(value).strip() for value in values if value]
        return " ".join(parts) if parts else None

    @staticmethod
    def _build_request_notes(requested_items: list[dict[str, Any]]) -> str | None:
        notes = [str(item.get("notes")).strip() for item in requested_items if item.get("notes")]
        if not notes:
            return None
        return " | ".join(notes)

    @staticmethod
    def _normalize_service_order_status(row: dict[str, Any]) -> str:
        if row.get("status") == "SUBMITTED_OPTIONS" and row.get("thread_status") == "closed":
            return "proposal_sent"
        return str(row["status"])

    def _insert_offer_notice(
        self,
        *,
        thread_id: int,
        seller_id: int,
        offer_id: int,
        body: str,
        metadata_json: dict[str, Any],
    ) -> dict[str, Any]:
        return dict(
            self._session.execute(
                text(
                    """
                    INSERT INTO thread_messages (thread_id, sender_role, sender_user_ref, type, body, metadata_json)
                    VALUES (
                        :thread_id,
                        'system',
                        :sender_user_ref,
                        'offer_notice',
                        :body,
                        CAST(:metadata_json AS jsonb)
                    )
                    RETURNING created_at
                    """
                ),
                {
                    "thread_id": int(thread_id),
                    "sender_user_ref": f"seller:{seller_id}",
                    "body": body,
                    "metadata_json": json.dumps({"offer_id": int(offer_id), **metadata_json}),
                },
            ).mappings().one()
        )

    def _touch_offer(self, offer_id: int) -> None:
        self._session.execute(
            text(
                """
                UPDATE seller_offers
                SET updated_at = now(),
                    total_amount = CASE
                        WHEN status IN ('FINALIZED_QUOTE', 'proposal_sent') THEN total_amount
                        ELSE NULL
                    END
                WHERE id = :offer_id
                """
            ),
            {"offer_id": int(offer_id)},
        )

    def _get_visible_thread(self, *, thread_id: int, actor: Any) -> dict[str, Any]:
        row = self._session.execute(
            text(
                """
                SELECT
                    id,
                    mechanic_id,
                    workshop_id,
                    status,
                    created_at,
                    updated_at,
                    last_message_at,
                    vehicle_plate,
                    vehicle_brand,
                    vehicle_model,
                    vehicle_year,
                    vehicle_engine,
                    vehicle_version,
                    vehicle_notes
                FROM quote_threads
                WHERE id = :thread_id
                """
            ),
            {"thread_id": int(thread_id)},
        ).mappings().one_or_none()
        if row is None:
            raise NotFoundError("thread not found")

        actor_role = getattr(actor, "role", None)
        if actor_role == "mechanic" and int(row["mechanic_id"]) != int(actor.mechanic_id):
            raise UnauthorizedError("thread not available")
        if actor_role == "seller":
            self._assert_seller_visible(
                thread_id=thread_id,
                seller_id=int(actor.vendor_id),
                seller_shop_id=int(actor.shop_id),
            )
        elif actor_role not in {"mechanic", "seller", "admin"}:
            raise UnauthorizedError("thread not available")
        return dict(row)

    def _assert_seller_visible(self, *, thread_id: int, seller_id: int, seller_shop_id: int) -> None:
        row = self._session.execute(
            text(
                """
                SELECT 1
                FROM quote_threads t
                WHERE t.id = :thread_id
                  AND (
                    EXISTS (
                        SELECT 1
                        FROM vendor_assignments va
                        WHERE va.workshop_id = t.workshop_id
                          AND va.autopart_id = :shop_id
                          AND va.vendor_id = :seller_id
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM seller_offers so
                        WHERE so.thread_id = t.id
                          AND so.seller_id = :seller_id
                    )
                  )
                """
            ),
            {
                "thread_id": int(thread_id),
                "shop_id": int(seller_shop_id),
                "seller_id": int(seller_id),
            },
        ).one_or_none()
        if row is None:
            raise UnauthorizedError("thread not available")

    def _assert_mechanic_membership(self, *, mechanic_id: int, workshop_id: int) -> None:
        row = self._session.execute(
            text(
                """
                SELECT 1
                FROM mechanics
                WHERE id = :mechanic_id
                  AND workshop_id = :workshop_id
                  AND soft_delete = false
                  AND status = 'active'
                """
            ),
            {"mechanic_id": int(mechanic_id), "workshop_id": int(workshop_id)},
        ).one_or_none()
        if row is None:
            raise UnauthorizedError("mechanic not available")

    @staticmethod
    def _actor_proxy(role: str, user_id: int | None, shop_id: int | None, mechanic_id: int | None = None) -> Any:
        class Actor:
            pass

        actor = Actor()
        actor.role = role
        actor.user_id = user_id
        actor.shop_id = shop_id
        actor.vendor_id = user_id if role == "seller" else None
        actor.mechanic_id = mechanic_id if mechanic_id is not None else (user_id if role == "mechanic" else None)
        return actor
