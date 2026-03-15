from __future__ import annotations

from datetime import datetime, timezone

import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_browser_thread_repo,
)
from src.bot.adapters.driver.fastapi.dependencies.use_cases import (
    get_parts_suggestion_provider,
)
from src.bot.adapters.driver.fastapi.routers.mechanic_service_orders import (
    router as mechanic_service_orders_router,
)
from src.bot.adapters.driver.fastapi.routers.offers import router as offers_router
from src.bot.adapters.driver.fastapi.routers.seller_inbox import router as seller_inbox_router
from src.bot.adapters.driver.fastapi.routers.threads import router as threads_router
from src.bot.domain.errors import NotFoundError, UnauthorizedError, ValidationError
from src.bot.infrastructure.config.settings import settings
from src.bot.infrastructure.errors.http_exceptions import register_exception_handlers


def _dt() -> datetime:
    return datetime(2026, 3, 10, tzinfo=timezone.utc)


def _token(payload: dict) -> str:
    base = {
        "iat": _dt(),
        "exp": datetime(2027, 3, 11, tzinfo=timezone.utc),
    }
    return jwt.encode({**base, **payload}, settings.SELLER_JWT_SECRET, algorithm="HS256")


class FakeSuggestionProvider:
    async def suggest(self, payload: dict) -> list[dict]:
        if payload["part_number"] == "FAIL":
            raise ValidationError("llm failed")
        description = payload["original_description"]
        part_number = payload.get("part_number")
        return [
            {
                "title": description,
                "brand": "Sugestao",
                "part_number": part_number or f"SUG-{payload['requested_item_id']}",
                "confidence": 0.92,
                "note": "Alta confiança",
                "metadata_json": {"source": "fake"},
            }
        ]


class FakeBrowserThreadRepo:
    def __init__(self) -> None:
        self._threads: dict[int, dict] = {}
        self._requests: dict[int, dict] = {}
        self._requested_items: dict[int, list[dict]] = {}
        self._messages: dict[int, list[dict]] = {}
        self._suggestions: dict[int, list[dict]] = {}
        self._offers: dict[int, dict] = {}
        self._offers_by_thread_seller: dict[tuple[int, int], int] = {}
        self._offer_items: dict[int, list[dict]] = {}
        self._thread_seq = 1
        self._request_seq = 1
        self._requested_item_seq = 1
        self._message_seq = 1
        self._suggestion_seq = 1
        self._offer_seq = 1
        self._item_seq = 1
        self._workshops = {
            7: {"id": 7, "name": "Oficina Azul", "phone": "+5511999999999", "address": "Rua Azul, 10"},
            8: {"id": 8, "name": "Oficina Verde", "phone": "+5511888888888", "address": "Rua Verde, 20"},
        }
        self._mechanic_names = {11: "Mecânico A", 12: "Mecânico B"}
        self._seller_shops = {21: 9, 22: 10}
        self._seller_names = {21: "Carlos Silva", 22: "Ana Souza"}
        self._seller_shop_names = {21: "Autopeças Azul", 22: "Autopeças Vermelha"}

    def create_thread(self, *, mechanic_id: int, workshop_id: int, payload: dict, request_status: str) -> dict:
        if mechanic_id not in {11, 12}:
            raise UnauthorizedError("mechanic not available")

        requested_items = payload.get("requested_items") or []
        if not requested_items:
            requested_items = [
                {
                    "description": payload["original_description"],
                    "part_number": payload.get("part_number"),
                    "quantity": payload.get("requested_items_count", 1),
                    "notes": None,
                }
            ]
        vehicle = payload.get("vehicle") or {
            "plate": payload.get("vehicle_plate"),
            "brand": payload.get("vehicle_brand"),
            "model": payload.get("vehicle_model"),
            "year": payload.get("vehicle_year"),
            "engine": payload.get("vehicle_engine"),
            "version": payload.get("vehicle_version"),
            "notes": payload.get("vehicle_notes"),
        }
        requested_items_text = self._build_requested_items_text(requested_items)

        thread_id = self._thread_seq
        self._thread_seq += 1
        request_id = self._request_seq
        self._request_seq += 1

        thread = {
            "id": thread_id,
            "mechanic_id": mechanic_id,
            "workshop_id": workshop_id,
            "status": "open",
            "created_at": _dt(),
            "updated_at": _dt(),
            "last_message_at": _dt(),
            "vehicle_plate": vehicle.get("plate"),
            "vehicle_brand": vehicle.get("brand"),
            "vehicle_model": vehicle.get("model"),
            "vehicle_year": vehicle.get("year"),
            "vehicle_engine": vehicle.get("engine"),
            "vehicle_version": vehicle.get("version"),
            "vehicle_notes": vehicle.get("notes"),
        }
        request = {
            "id": request_id,
            "thread_id": thread_id,
            "original_description": payload.get("original_description") or requested_items_text,
            "requested_items_count": len(requested_items),
            "part_number": requested_items[0].get("part_number") if len(requested_items) == 1 else None,
            "vehicle_plate": vehicle.get("plate"),
            "vehicle_brand": vehicle.get("brand"),
            "vehicle_model": vehicle.get("model"),
            "vehicle_year": vehicle.get("year"),
            "vehicle_engine": vehicle.get("engine"),
            "vehicle_version": vehicle.get("version"),
            "vehicle_notes": vehicle.get("notes"),
            "status": request_status,
            "created_at": _dt(),
        }
        request_items = []
        for item in requested_items:
            request_items.append(
                {
                    "id": self._requested_item_seq,
                    "request_id": request_id,
                    "description": item["description"],
                    "part_number": item.get("part_number"),
                    "quantity": item["quantity"],
                    "notes": item.get("notes"),
                    "created_at": _dt(),
                }
            )
            self._requested_item_seq += 1

        message = {
            "id": self._message_seq,
            "thread_id": thread_id,
            "sender_role": "system",
            "sender_user_ref": "system",
            "type": "request_summary",
            "body": request["original_description"],
            "metadata_json": {},
            "created_at": _dt(),
        }
        self._message_seq += 1
        self._threads[thread_id] = thread
        self._requests[thread_id] = request
        self._requested_items[thread_id] = request_items
        self._messages[thread_id] = [message]
        self._suggestions[thread_id] = []
        for seller_id, shop_id in self._seller_shops.items():
            offer_id = self._offer_seq
            self._offer_seq += 1
            self._offers_by_thread_seller[(thread_id, seller_id)] = offer_id
            self._offers[offer_id] = {
                "id": offer_id,
                "thread_id": thread_id,
                "seller_id": seller_id,
                "seller_shop_id": shop_id,
                "status": "DRAFT",
                "notes": None,
                "total_amount": None,
                "created_at": _dt(),
                "updated_at": _dt(),
                "submitted_at": None,
                "finalized_at": None,
                "seller_name": self._seller_names[seller_id],
                "seller_shop_name": self._seller_shop_names[seller_id],
            }
            self._offer_items[offer_id] = []
        return {
            "thread": thread,
            "workshop": self._workshops[workshop_id],
            "vehicle": self._vehicle_from_thread(thread),
            "requested_items": request_items,
            "request": self._request_with_nested(thread_id),
            "messages": [message],
            "suggestions": [],
            "offers": [],
        }

    def update_request_status(self, request_id: int, status: str) -> None:
        for request in self._requests.values():
            if request["id"] == request_id:
                request["status"] = status
                return
        raise NotFoundError("request not found")

    def save_suggestions(self, *, thread_id: int, request_id: int, suggestions: list[dict]) -> list[dict]:
        rows = []
        for suggestion in suggestions:
            row = {
                "id": self._suggestion_seq,
                "thread_id": thread_id,
                "request_id": request_id,
                "requested_item_id": suggestion.get("requested_item_id"),
                "title": suggestion["title"],
                "brand": suggestion.get("brand"),
                "part_number": suggestion.get("part_number"),
                "confidence": suggestion.get("confidence"),
                "note": suggestion.get("note"),
                "metadata_json": suggestion.get("metadata_json") or {},
                "created_at": _dt(),
            }
            self._suggestion_seq += 1
            rows.append(row)
        self._suggestions[thread_id] = rows
        return rows

    def list_threads(self, *, actor, status=None, limit=20, offset=0):
        rows = []
        for thread_id, thread in self._threads.items():
            if actor.role == "mechanic" and thread["mechanic_id"] != actor.mechanic_id:
                continue
            if actor.role == "seller" and (thread_id, actor.vendor_id) not in self._offers_by_thread_seller:
                continue
            if status and thread["status"] != status:
                continue
            request = self._requests[thread_id]
            rows.append(
                {
                    **thread,
                    "request_id": request["id"],
                    "original_description": request["original_description"],
                    "part_number": request["part_number"],
                    "requested_items_count": len(self._requested_items[thread_id]),
                    "vehicle_brand": thread.get("vehicle_brand"),
                    "vehicle_model": thread.get("vehicle_model"),
                    "vehicle_year": thread.get("vehicle_year"),
                    "request_status": request["status"],
                    "workshop_name": self._workshops[thread["workshop_id"]]["name"],
                    "mechanic_name": self._mechanic_names.get(thread["mechanic_id"], "Mecânico"),
                    "submitted_offer_count": len(
                        [
                            offer
                            for offer in self._offers.values()
                            if offer["thread_id"] == thread_id and offer["status"] in {"SUBMITTED_OPTIONS", "FINALIZED_QUOTE", "proposal_sent"}
                        ]
                    ),
                }
            )
        return rows[offset : offset + limit]

    def get_thread_detail(self, *, thread_id: int, actor):
        thread = self._threads.get(thread_id)
        if thread is None:
            raise NotFoundError("thread not found")
        if actor.role == "mechanic" and thread["mechanic_id"] != actor.mechanic_id:
            raise UnauthorizedError("thread not available")
        if actor.role == "seller" and (thread_id, actor.vendor_id) not in self._offers_by_thread_seller:
            raise UnauthorizedError("thread not available")
        return {
            "thread": thread,
            "workshop": self._workshops[thread["workshop_id"]],
            "vehicle": self._vehicle_from_thread(thread),
            "requested_items": self._requested_items[thread_id],
            "request": self._request_with_nested(thread_id),
            "messages": self._messages[thread_id],
            "suggestions": self._suggestions[thread_id],
            "offers": self.list_offers(thread_id=thread_id, actor=actor),
        }

    def list_messages(self, *, thread_id: int, actor, limit=100):
        self.get_thread_detail(thread_id=thread_id, actor=actor)
        return self._messages[thread_id][:limit]

    def add_message(self, *, thread_id: int, actor, sender_role: str, sender_user_ref: str, type_: str, body: str, metadata_json=None):
        self.get_thread_detail(thread_id=thread_id, actor=actor)
        message = {
            "id": self._message_seq,
            "thread_id": thread_id,
            "sender_role": sender_role,
            "sender_user_ref": sender_user_ref,
            "type": type_,
            "body": body,
            "metadata_json": metadata_json or {},
            "created_at": _dt(),
        }
        self._message_seq += 1
        self._messages[thread_id].append(message)
        return message

    def get_request(self, *, thread_id: int, actor):
        self.get_thread_detail(thread_id=thread_id, actor=actor)
        return self._request_with_nested(thread_id)

    def list_suggestions(self, *, thread_id: int, actor):
        self.get_thread_detail(thread_id=thread_id, actor=actor)
        return self._suggestions[thread_id]

    def get_or_create_offer(self, *, thread_id: int, seller_id: int, seller_shop_id: int):
        if seller_id not in self._seller_shops:
            raise UnauthorizedError("thread not available")
        key = (thread_id, seller_id)
        if key not in self._offers_by_thread_seller:
            offer_id = self._offer_seq
            self._offer_seq += 1
            self._offers_by_thread_seller[key] = offer_id
            self._offers[offer_id] = {
                "id": offer_id,
                "thread_id": thread_id,
                "seller_id": seller_id,
                "seller_shop_id": seller_shop_id,
                "status": "DRAFT",
                "notes": None,
                "total_amount": None,
                "created_at": _dt(),
                "updated_at": _dt(),
                "submitted_at": None,
                "finalized_at": None,
                "seller_name": self._seller_names[seller_id],
                "seller_shop_name": self._seller_shop_names[seller_id],
            }
            self._offer_items[offer_id] = []
        return self.get_offer(
            offer_id=self._offers_by_thread_seller[key],
            actor=_seller_actor(seller_id=seller_id, shop_id=seller_shop_id),
        )

    def list_offers(self, *, thread_id: int, actor):
        offers = []
        for offer in self._offers.values():
            if offer["thread_id"] != thread_id:
                continue
            if actor.role == "mechanic" and offer["status"] not in {"SUBMITTED_OPTIONS", "FINALIZED_QUOTE", "proposal_sent"}:
                continue
            if actor.role == "seller" and offer["seller_id"] != actor.vendor_id:
                continue
            offers.append(self._offer_with_items(offer["id"]))
        return offers

    def get_offer(self, *, offer_id: int, actor):
        offer = self._offers.get(offer_id)
        if offer is None:
            raise NotFoundError("offer not found")
        if actor.role == "seller" and offer["seller_id"] != actor.vendor_id:
            raise UnauthorizedError("offer not available")
        if actor.role == "mechanic":
            thread = self._threads[offer["thread_id"]]
            if thread["mechanic_id"] != actor.mechanic_id or offer["status"] not in {"SUBMITTED_OPTIONS", "FINALIZED_QUOTE", "proposal_sent"}:
                raise UnauthorizedError("offer not available")
        return self._offer_with_items(offer_id)

    def add_offer_item(self, *, offer_id: int, seller_id: int, payload: dict):
        offer = self._offers[offer_id]
        if offer["seller_id"] != seller_id:
            raise UnauthorizedError("offer not available")
        if offer["status"] not in {"DRAFT", "SUBMITTED_OPTIONS"}:
            raise ValidationError("only draft or submitted option offers can be edited")

        requested_item_id = payload.get("requested_item_id")
        if requested_item_id is None:
            if len(self._requested_items[offer["thread_id"]]) == 1:
                requested_item_id = self._requested_items[offer["thread_id"]][0]["id"]
            else:
                raise ValidationError("requested_item_id is required")

        if payload["source_type"] == "suggested":
            if not payload.get("suggested_part_id"):
                raise ValidationError("invalid suggested_part_id")
            suggestion = next(
                (
                    row
                    for row in self._suggestions[offer["thread_id"]]
                    if row["id"] == payload["suggested_part_id"]
                ),
                None,
            )
            if suggestion is None:
                raise ValidationError("invalid suggested_part_id")
            title = payload.get("description") or suggestion["title"]
            brand = payload.get("brand") or suggestion["brand"]
            part_number = payload.get("part_number") or suggestion["part_number"]
        else:
            title = payload.get("description") or payload.get("title")
            brand = payload.get("brand")
            part_number = payload.get("part_number")
        item = {
            "id": self._item_seq,
            "offer_id": offer_id,
            "requested_item_id": requested_item_id,
            "source_type": payload["source_type"],
            "suggested_part_id": payload.get("suggested_part_id"),
            "title": title,
            "brand": brand,
            "part_number": part_number,
            "quantity": payload.get("quantity", 1),
            "unit_price": payload.get("unit_price"),
            "compatibility_note": payload.get("notes") or payload.get("compatibility_note"),
            "metadata_json": payload.get("metadata_json") or {},
            "is_final_choice": payload.get("is_final_choice", False),
            "created_at": _dt(),
            "updated_at": _dt(),
        }
        self._item_seq += 1
        self._offer_items[offer_id].append(item)
        offer["updated_at"] = _dt()
        offer["total_amount"] = None
        return self._serialize_offer_item(item)

    def update_offer_item(self, *, offer_id: int, item_id: int, seller_id: int, payload: dict):
        offer = self._offers[offer_id]
        if offer["seller_id"] != seller_id:
            raise UnauthorizedError("offer not available")
        if offer["status"] not in {"DRAFT", "SUBMITTED_OPTIONS"}:
            raise ValidationError("only draft or submitted option offers can be edited")
        for item in self._offer_items[offer_id]:
            if item["id"] == item_id:
                if "description" in payload:
                    item["title"] = payload["description"]
                if "requested_item_id" in payload:
                    item["requested_item_id"] = payload["requested_item_id"]
                if "brand" in payload:
                    item["brand"] = payload["brand"]
                if "part_number" in payload:
                    item["part_number"] = payload["part_number"]
                if "quantity" in payload:
                    item["quantity"] = payload["quantity"]
                if "unit_price" in payload:
                    item["unit_price"] = payload["unit_price"]
                if "notes" in payload or "compatibility_note" in payload:
                    item["compatibility_note"] = payload.get("notes") or payload.get("compatibility_note")
                if "metadata_json" in payload:
                    item["metadata_json"] = payload["metadata_json"] or {}
                if "is_final_choice" in payload:
                    item["is_final_choice"] = payload["is_final_choice"]
                item["updated_at"] = _dt()
                offer["updated_at"] = _dt()
                offer["total_amount"] = None
                return self._serialize_offer_item(item)
        raise NotFoundError("offer item not found")

    def delete_offer_item(self, *, offer_id: int, item_id: int, seller_id: int):
        offer = self._offers[offer_id]
        if offer["seller_id"] != seller_id:
            raise UnauthorizedError("offer not available")
        if offer["status"] not in {"DRAFT", "SUBMITTED_OPTIONS"}:
            raise ValidationError("only draft or submitted option offers can be edited")
        original_len = len(self._offer_items[offer_id])
        self._offer_items[offer_id] = [item for item in self._offer_items[offer_id] if item["id"] != item_id]
        if len(self._offer_items[offer_id]) == original_len:
            raise NotFoundError("offer item not found")
        offer["updated_at"] = _dt()
        offer["total_amount"] = None

    def submit_offer(self, *, offer_id: int, seller_id: int, payload: dict | None = None):
        offer = self._offers[offer_id]
        if offer["seller_id"] != seller_id:
            raise UnauthorizedError("offer not available")
        if offer["status"] not in {"DRAFT", "SUBMITTED_OPTIONS"}:
            raise ValidationError("offer is not in an editable state")
        items = self._offer_items[offer_id]
        self._validate_items(items)
        if (payload or {}).get("close_quote"):
            selected_ids = (payload or {}).get("selected_option_ids")
            if selected_ids is None:
                selected_ids = [item["id"] for item in items if item.get("is_final_choice")] or [item["id"] for item in items]
            selected_id_set = set(selected_ids)
            for item in items:
                item["is_final_choice"] = item["id"] in selected_id_set
                item["updated_at"] = _dt()
            offer["status"] = "proposal_sent"
            offer["total_amount"] = round(
                sum(item["quantity"] * item["unit_price"] for item in items if item["id"] in selected_id_set),
                2,
            )
            offer["submitted_at"] = _dt()
            offer["finalized_at"] = _dt()
            offer["updated_at"] = _dt()
            self._threads[offer["thread_id"]]["status"] = "closed"
            self._messages[offer["thread_id"]].append(
                {
                    "id": self._message_seq,
                    "thread_id": offer["thread_id"],
                    "sender_role": "system",
                    "sender_user_ref": f"seller:{seller_id}",
                    "type": "offer_notice",
                    "body": self._build_offer_summary(offer_id, finalized=True, proposal_sent=True),
                    "metadata_json": {
                        "offer_id": offer_id,
                        "status": "proposal_sent",
                        "service_order_id": self._service_order_public_id(offer_id),
                    },
                    "created_at": _dt(),
                }
            )
            self._message_seq += 1
            response = self._offer_with_items(offer_id)
            response["offer_id"] = offer_id
            response["thread_status"] = "closed"
            response["service_order_id"] = self._service_order_public_id(offer_id)
            return response
        offer["status"] = "SUBMITTED_OPTIONS"
        offer["total_amount"] = None
        offer["submitted_at"] = _dt()
        offer["updated_at"] = _dt()
        self._threads[offer["thread_id"]]["status"] = "offer_received"
        summary = self._build_offer_summary(offer_id, finalized=False)
        self._messages[offer["thread_id"]].append(
            {
                "id": self._message_seq,
                "thread_id": offer["thread_id"],
                "sender_role": "system",
                "sender_user_ref": f"seller:{seller_id}",
                "type": "offer_notice",
                "body": summary,
                "metadata_json": {"offer_id": offer_id, "status": "SUBMITTED_OPTIONS"},
                "created_at": _dt(),
            }
        )
        self._message_seq += 1
        response = self._offer_with_items(offer_id)
        response["offer_id"] = offer_id
        response["thread_status"] = "offer_received"
        response["service_order_id"] = None
        return response

    def finalize_offer(self, *, offer_id: int, seller_id: int, payload: dict | None = None):
        offer = self._offers[offer_id]
        if offer["seller_id"] != seller_id:
            raise UnauthorizedError("offer not available")
        if offer["status"] not in {"DRAFT", "SUBMITTED_OPTIONS"}:
            raise ValidationError("offer is not in an editable state")
        items = self._offer_items[offer_id]
        self._validate_items(items)
        selected_ids = (payload or {}).get("selected_option_ids")
        if selected_ids is None:
            selected_ids = [item["id"] for item in items if item.get("is_final_choice")]
        if not selected_ids:
            raise ValidationError("finalized quote must select at least one option")
        seen_requested_item_ids: set[int] = set()
        for item in items:
            item["is_final_choice"] = item["id"] in selected_ids
            if item["is_final_choice"]:
                if item["requested_item_id"] in seen_requested_item_ids:
                    raise ValidationError("only one final choice is allowed per requested item")
                seen_requested_item_ids.add(item["requested_item_id"])
            item["updated_at"] = _dt()
        offer["status"] = "FINALIZED_QUOTE"
        offer["total_amount"] = round(
            sum(item["quantity"] * item["unit_price"] for item in items if item["is_final_choice"]),
            2,
        )
        offer["submitted_at"] = offer["submitted_at"] or _dt()
        offer["finalized_at"] = _dt()
        offer["updated_at"] = _dt()
        self._threads[offer["thread_id"]]["status"] = "offer_received"
        summary = self._build_offer_summary(offer_id, finalized=True)
        self._messages[offer["thread_id"]].append(
            {
                "id": self._message_seq,
                "thread_id": offer["thread_id"],
                "sender_role": "system",
                "sender_user_ref": f"seller:{seller_id}",
                "type": "offer_notice",
                "body": summary,
                "metadata_json": {"offer_id": offer_id, "status": "FINALIZED_QUOTE"},
                "created_at": _dt(),
            }
        )
        self._message_seq += 1
        return self._offer_with_items(offer_id)

    def get_comparison(self, *, thread_id: int, mechanic_id: int):
        if self._threads[thread_id]["mechanic_id"] != mechanic_id:
            raise UnauthorizedError("thread not available")
        return {
            "thread_id": thread_id,
            "vehicle": self._vehicle_from_thread(self._threads[thread_id]),
            "requested_items": self._requested_items[thread_id],
            "request": self._request_with_nested(thread_id),
            "offers": [
                {
                    "offer_id": offer["id"],
                    "seller_id": offer["seller_id"],
                    "seller_name": offer["seller_name"],
                    "seller_shop_id": offer["seller_shop_id"],
                    "seller_shop_name": offer["seller_shop_name"],
                    "status": offer["status"],
                    "summary_text": self._build_offer_summary(
                        offer["id"],
                        finalized=offer["status"] in {"FINALIZED_QUOTE", "proposal_sent"},
                        proposal_sent=offer["status"] == "proposal_sent",
                    ),
                    "final_total": offer["total_amount"] if offer["status"] in {"FINALIZED_QUOTE", "proposal_sent"} else None,
                    "total_amount": offer["total_amount"] if offer["status"] in {"FINALIZED_QUOTE", "proposal_sent"} else None,
                    "submitted_at": offer["submitted_at"],
                    "finalized_at": offer["finalized_at"],
                    "groups": self._group_offer_items(offer["id"]),
                    "items": [self._serialize_offer_item(item) for item in self._offer_items[offer["id"]]],
                    "notes": offer["notes"],
                }
                for offer in self._offers.values()
                if offer["thread_id"] == thread_id and offer["status"] in {"SUBMITTED_OPTIONS", "FINALIZED_QUOTE", "proposal_sent"}
            ],
        }

    def list_service_orders(self, *, mechanic_id: int):
        rows = []
        for offer in self._offers.values():
            thread = self._threads[offer["thread_id"]]
            if thread["mechanic_id"] != mechanic_id:
                continue
            if not (
                offer["status"] == "proposal_sent"
                or (offer["status"] == "SUBMITTED_OPTIONS" and thread["status"] == "closed")
            ):
                continue
            rows.append(self._service_order_summary(offer["id"]))
        rows.sort(key=lambda row: (row["submitted_at"], row["offer_id"]), reverse=True)
        return rows

    def get_service_order(self, *, service_order_id: str, mechanic_id: int):
        offer_id = self._parse_service_order_id(service_order_id)
        offer = self._offers.get(offer_id)
        if offer is None:
            raise NotFoundError("service order not found")
        thread = self._threads[offer["thread_id"]]
        if thread["mechanic_id"] != mechanic_id or not (
            offer["status"] == "proposal_sent"
            or (offer["status"] == "SUBMITTED_OPTIONS" and thread["status"] == "closed")
        ):
            raise NotFoundError("service order not found")
        return self._service_order_detail(offer_id)

    def seller_inbox_list(self, *, seller_id: int, shop_id: int, status=None, search=None, page=1, page_size=20):
        actor = _seller_actor(seller_id=seller_id, shop_id=shop_id)
        rows = self.list_threads(actor=actor, status=status, limit=page_size, offset=(page - 1) * page_size)
        return rows, len(rows)

    def seller_inbox_get(self, *, thread_id: int, seller_id: int, shop_id: int):
        return self.get_thread_detail(thread_id=thread_id, actor=_seller_actor(seller_id=seller_id, shop_id=shop_id))

    def update_thread_status_for_seller(self, *, thread_id: int, seller_id: int, shop_id: int, new_status: str):
        self._threads[thread_id]["status"] = new_status

    @staticmethod
    def _build_requested_items_text(items: list[dict]) -> str:
        parts = []
        for item in items:
            suffix = f" ({item['quantity']}x)" if item["quantity"] > 1 else ""
            parts.append(f"{item['description']}{suffix}")
        if len(parts) == 1:
            return parts[0]
        if len(parts) == 2:
            return f"{parts[0]} e {parts[1]}"
        return ", ".join(parts[:-1]) + f" e {parts[-1]}"

    @staticmethod
    def _vehicle_from_thread(thread: dict) -> dict:
        return {
            "plate": thread.get("vehicle_plate"),
            "brand": thread.get("vehicle_brand"),
            "model": thread.get("vehicle_model"),
            "year": thread.get("vehicle_year"),
            "engine": thread.get("vehicle_engine"),
            "version": thread.get("vehicle_version"),
            "notes": thread.get("vehicle_notes"),
        }

    def _request_with_nested(self, thread_id: int) -> dict:
        request = dict(self._requests[thread_id])
        request["vehicle"] = self._vehicle_from_thread(self._threads[thread_id])
        request["requested_items"] = list(self._requested_items[thread_id])
        request["requested_items_count"] = len(self._requested_items[thread_id])
        request["part_number"] = request["requested_items"][0].get("part_number") if len(request["requested_items"]) == 1 else None
        return request

    def _serialize_offer_item(self, item: dict) -> dict:
        return {
            "id": item["id"],
            "offer_id": item["offer_id"],
            "requested_item_id": item["requested_item_id"],
            "source_type": item["source_type"],
            "suggested_part_id": item.get("suggested_part_id"),
            "description": item["title"],
            "title": item["title"],
            "brand": item.get("brand"),
            "part_number": item.get("part_number"),
            "quantity": item["quantity"],
            "unit_price": item.get("unit_price"),
            "notes": item.get("compatibility_note"),
            "compatibility_note": item.get("compatibility_note"),
            "metadata_json": item.get("metadata_json") or {},
            "is_final_choice": item.get("is_final_choice", False),
            "created_at": item["created_at"],
            "updated_at": item["updated_at"],
        }

    def _group_offer_items(self, offer_id: int) -> list[dict]:
        offer = self._offers[offer_id]
        groups = []
        for requested_item in self._requested_items[offer["thread_id"]]:
            options = [
                self._serialize_offer_item(item)
                for item in self._offer_items[offer_id]
                if item["requested_item_id"] == requested_item["id"]
            ]
            groups.append(
                {
                    "requested_item_id": requested_item["id"],
                    "requested_item_description": requested_item["description"],
                    "requested_quantity": requested_item["quantity"],
                    "options": options,
                }
            )
        return groups

    def _build_offer_summary(self, offer_id: int, *, finalized: bool, proposal_sent: bool = False) -> str:
        groups = self._group_offer_items(offer_id)
        parts = []
        for group in groups:
            if finalized:
                count = len([option for option in group["options"] if option["is_final_choice"]])
                noun = "item selecionado" if count == 1 else "itens selecionados"
            else:
                count = len(group["options"])
                noun = "opção" if count == 1 else "opções"
            if count:
                parts.append(f"{count} {noun} para {group['requested_item_description']}")
        joined = parts[0] if len(parts) == 1 else f"{parts[0]} e {parts[1]}" if len(parts) == 2 else ", ".join(parts[:-1]) + f" e {parts[-1]}"
        prefix = "Orçamento enviado com" if proposal_sent else "Orçamento final consolidado com" if finalized else "Resposta enviada com"
        return f"{prefix} {joined}."

    def _offer_with_items(self, offer_id: int) -> dict:
        offer = self._offers[offer_id]
        status = offer["status"]
        final_total = offer["total_amount"] if status in {"FINALIZED_QUOTE", "proposal_sent"} else None
        return {
            **offer,
            "summary_text": None
            if status == "DRAFT"
            else self._build_offer_summary(
                offer_id,
                finalized=status in {"FINALIZED_QUOTE", "proposal_sent"},
                proposal_sent=status == "proposal_sent",
            ),
            "final_total": final_total,
            "total_amount": final_total,
            "seller_store": {"id": offer["seller_shop_id"], "name": offer["seller_shop_name"]},
            "seller_user": {"id": offer["seller_id"], "name": offer["seller_name"]},
            "groups": self._group_offer_items(offer_id),
            "items": [self._serialize_offer_item(item) for item in self._offer_items[offer_id]],
        }

    def _service_order_summary(self, offer_id: int) -> dict:
        offer = self._offers[offer_id]
        thread = self._threads[offer["thread_id"]]
        request = self._requests[offer["thread_id"]]
        items = self._service_order_items(offer_id)
        return {
            "id": self._service_order_public_id(offer_id),
            "thread_id": offer["thread_id"],
            "offer_id": offer_id,
            "status": "proposal_sent" if offer["status"] == "SUBMITTED_OPTIONS" else offer["status"],
            "title": request["original_description"],
            "workshop_name": self._workshops[thread["workshop_id"]]["name"],
            "vehicle_summary": self._vehicle_summary(thread),
            "total_amount": offer["total_amount"] if offer["total_amount"] is not None else round(sum(item["line_total"] for item in items), 2),
            "item_count": len(items),
            "created_at": offer["created_at"],
            "submitted_at": offer["submitted_at"],
            "auto_parts_name": offer["seller_shop_name"],
            "seller_name": offer["seller_name"],
        }

    def _service_order_detail(self, offer_id: int) -> dict:
        offer = self._offers[offer_id]
        thread = self._threads[offer["thread_id"]]
        request = self._request_with_nested(offer["thread_id"])
        workshop = self._workshops[thread["workshop_id"]]
        items = self._service_order_items(offer_id)
        return {
            "id": self._service_order_public_id(offer_id),
            "thread_id": offer["thread_id"],
            "offer_id": offer_id,
            "status": "proposal_sent" if offer["status"] == "SUBMITTED_OPTIONS" else offer["status"],
            "title": request["original_description"],
            "created_at": offer["created_at"],
            "submitted_at": offer["submitted_at"],
            "workshop_name": workshop["name"],
            "vehicle_summary": self._vehicle_summary(thread),
            "request_notes": self._request_notes(request["requested_items"]),
            "auto_parts": {
                "name": offer["seller_shop_name"],
                "phone": "+5511999990000" if offer["seller_id"] == 21 else "+5511888880000",
                "address": "Rua das Peças, 100" if offer["seller_id"] == 21 else "Rua das Peças, 200",
            },
            "seller": {
                "name": offer["seller_name"],
                "phone": None,
            },
            "items": items,
            "total_amount": offer["total_amount"] if offer["total_amount"] is not None else round(sum(item["line_total"] for item in items), 2),
        }

    def _service_order_items(self, offer_id: int) -> list[dict]:
        items = [item for item in self._offer_items[offer_id] if item.get("is_final_choice")]
        if not items:
            items = list(self._offer_items[offer_id])
        requested_item_map = {
            item["id"]: item["description"]
            for item in self._requested_items[self._offers[offer_id]["thread_id"]]
        }
        return [
            {
                "id": f"line_{item['id']}",
                "requested_item_id": item["requested_item_id"],
                "requested_item_label": requested_item_map.get(item["requested_item_id"]),
                "description": item["title"],
                "brand": item.get("brand"),
                "part_number": item.get("part_number"),
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "line_total": round(item["quantity"] * item["unit_price"], 2),
                "notes": item.get("compatibility_note"),
            }
            for item in items
        ]

    @staticmethod
    def _service_order_public_id(offer_id: int) -> str:
        return f"so_{offer_id}"

    @staticmethod
    def _parse_service_order_id(service_order_id: str) -> int:
        value = service_order_id[3:] if service_order_id.startswith("so_") else service_order_id
        if not value.isdigit():
            raise ValidationError("invalid service order id")
        return int(value)

    @staticmethod
    def _vehicle_summary(thread: dict) -> str | None:
        values = [
            thread.get("vehicle_brand"),
            thread.get("vehicle_model"),
            thread.get("vehicle_year"),
            thread.get("vehicle_engine"),
            thread.get("vehicle_version"),
        ]
        parts = [str(value) for value in values if value]
        return " ".join(parts) if parts else None

    @staticmethod
    def _request_notes(requested_items: list[dict]) -> str | None:
        notes = [item["notes"] for item in requested_items if item.get("notes")]
        if not notes:
            return None
        return " | ".join(notes)

    @staticmethod
    def _validate_items(items: list[dict]) -> None:
        if not items:
            raise ValidationError("submitted offer must contain at least one option")
        for item in items:
            if item["quantity"] <= 0:
                raise ValidationError("item quantity must be positive")
            if item["unit_price"] is None or item["unit_price"] <= 0:
                raise ValidationError(f"item {item['title']} must have a positive unit price")


def _seller_actor(seller_id: int = 21, shop_id: int = 9):
    class Actor:
        pass

    actor = Actor()
    actor.role = "seller"
    actor.vendor_id = seller_id
    actor.shop_id = shop_id
    actor.user_id = seller_id
    return actor


@pytest.fixture
def client():
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(mechanic_service_orders_router)
    app.include_router(threads_router)
    app.include_router(offers_router)
    app.include_router(seller_inbox_router)
    repo = FakeBrowserThreadRepo()
    app.dependency_overrides[get_browser_thread_repo] = lambda: repo
    app.dependency_overrides[get_parts_suggestion_provider] = lambda: FakeSuggestionProvider()
    return TestClient(app)


MECHANIC_HEADERS = {
    "Authorization": "Bearer "
    + _token(
        {
            "user_id": 11,
            "role": "mechanic",
            "shop_id": 7,
            "mechanic_id": 11,
            "name": "Mecânico A",
            "email": "mec@test.com",
        }
    )
}

OTHER_MECHANIC_HEADERS = {
    "Authorization": "Bearer "
    + _token(
        {
            "user_id": 12,
            "role": "mechanic",
            "shop_id": 8,
            "mechanic_id": 12,
            "name": "Mecânico B",
            "email": "other@test.com",
        }
    )
}

SELLER_HEADERS = {
    "Authorization": "Bearer "
    + _token(
        {
            "user_id": 21,
            "role": "seller",
            "shop_id": 9,
            "vendor_id": 21,
            "name": "Carlos Silva",
            "email": "seller@test.com",
        }
    )
}

OTHER_SELLER_HEADERS = {
    "Authorization": "Bearer "
    + _token(
        {
            "user_id": 22,
            "role": "seller",
            "shop_id": 10,
            "vendor_id": 22,
            "name": "Ana Souza",
            "email": "other-seller@test.com",
        }
    )
}


def test_thread_offer_flow_with_multiple_requested_items_and_finalize(client: TestClient):
    create_response = client.post(
        "/threads",
        headers=MECHANIC_HEADERS,
        json={
            "vehicle": {
                "plate": "ABC1D23",
                "brand": "FIAT",
                "model": "Palio",
                "year": "2015",
                "engine": "1.0",
                "version": "Fire",
            },
            "requested_items": [
                {"description": "Vela de ignição", "quantity": 4},
                {"description": "Alternador", "quantity": 1},
            ],
            "generate_suggestions": True,
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    thread_id = created["thread"]["id"]
    req_1 = created["requested_items"][0]["id"]
    req_2 = created["requested_items"][1]["id"]
    assert created["request"]["status"] == "ready_for_quote"
    assert created["vehicle"]["brand"] == "FIAT"
    assert len(created["requested_items"]) == 2
    assert {row["requested_item_id"] for row in created["suggestions"]} == {req_1, req_2}

    message_response = client.post(
        f"/threads/{thread_id}/messages",
        headers=MECHANIC_HEADERS,
        json={"type": "text", "body": "Pode mandar NGK ou DENSO"},
    )
    assert message_response.status_code == 200

    offer_response = client.post(f"/threads/{thread_id}/offers", headers=SELLER_HEADERS)
    assert offer_response.status_code == 200
    offer_id = offer_response.json()["id"]

    suggestion_by_item = {row["requested_item_id"]: row for row in created["suggestions"]}
    option_1_response = client.post(
        f"/offers/{offer_id}/items",
        headers=SELLER_HEADERS,
        json={
            "requested_item_id": req_1,
            "source_type": "suggested",
            "suggested_part_id": suggestion_by_item[req_1]["id"],
            "quantity": 4,
            "unit_price": 37.5,
            "notes": "Compatível com Palio 2015",
        },
    )
    assert option_1_response.status_code == 200
    option_1 = option_1_response.json()

    option_2_response = client.post(
        f"/offers/{offer_id}/items",
        headers=SELLER_HEADERS,
        json={
            "requested_item_id": req_1,
            "source_type": "manual",
            "description": "DENSO K20PR-U11",
            "brand": "DENSO",
            "part_number": "K20PR-U11",
            "quantity": 4,
            "unit_price": 39.9,
        },
    )
    assert option_2_response.status_code == 200

    option_3_response = client.post(
        f"/offers/{offer_id}/items",
        headers=SELLER_HEADERS,
        json={
            "requested_item_id": req_2,
            "source_type": "manual",
            "description": "Alternador Bosch X",
            "brand": "Bosch",
            "part_number": "ALT-X",
            "quantity": 1,
            "unit_price": 850.0,
        },
    )
    assert option_3_response.status_code == 200
    option_3 = option_3_response.json()

    submit_response = client.post(f"/offers/{offer_id}/submit", headers=SELLER_HEADERS)
    assert submit_response.status_code == 200
    submitted = submit_response.json()
    assert submitted["status"] == "SUBMITTED_OPTIONS"
    assert submitted["final_total"] is None
    assert submitted["summary_text"] == "Resposta enviada com 2 opções para Vela de ignição e 1 opção para Alternador."
    assert submitted["groups"][0]["requested_item_id"] == req_1
    assert len(submitted["groups"][0]["options"]) == 2
    assert len(submitted["groups"][1]["options"]) == 1

    detail_response = client.get(f"/threads/{thread_id}", headers=MECHANIC_HEADERS)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["offers"][0]["seller_store"]["name"] == "Autopeças Azul"
    assert detail["offers"][0]["seller_user"]["name"] == "Carlos Silva"
    assert detail["messages"][-1]["body"] != "Offer submitted"

    finalize_response = client.post(
        f"/offers/{offer_id}/finalize",
        headers=SELLER_HEADERS,
        json={"selected_option_ids": [option_1["id"], option_3["id"]]},
    )
    assert finalize_response.status_code == 200
    finalized = finalize_response.json()
    assert finalized["status"] == "FINALIZED_QUOTE"
    assert finalized["final_total"] == 1000.0
    assert finalized["groups"][0]["options"][0]["is_final_choice"] is True
    assert finalized["groups"][0]["options"][1]["is_final_choice"] is False

    comparison_response = client.get(f"/threads/{thread_id}/comparison", headers=MECHANIC_HEADERS)
    assert comparison_response.status_code == 200
    comparison = comparison_response.json()
    assert comparison["offers"][0]["final_total"] == 1000.0


def test_legacy_thread_payload_is_normalized_to_requested_items(client: TestClient):
    response = client.post(
        "/threads",
        headers=MECHANIC_HEADERS,
        json={
            "original_description": "Filtro de óleo",
            "part_number": "FO-1",
            "requested_items_count": 2,
            "vehicle_brand": "Honda",
            "vehicle_model": "Civic",
            "vehicle_year": "2018",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["requested_items"][0]["description"] == "Filtro de óleo"
    assert body["requested_items"][0]["quantity"] == 2
    assert body["vehicle"]["brand"] == "Honda"


def test_submitted_offer_can_be_edited_and_resubmitted(client: TestClient):
    create_response = client.post(
        "/threads",
        headers=MECHANIC_HEADERS,
        json={
            "requested_items": [{"description": "Amortecedor traseiro", "quantity": 1}],
        },
    )
    thread_id = create_response.json()["thread"]["id"]
    requested_item_id = create_response.json()["requested_items"][0]["id"]

    offer_id = client.post(f"/threads/{thread_id}/offers", headers=SELLER_HEADERS).json()["id"]
    added_item = client.post(
        f"/offers/{offer_id}/items",
        headers=SELLER_HEADERS,
        json={
            "requested_item_id": requested_item_id,
            "source_type": "manual",
            "description": "Amortecedor Cofap",
            "quantity": 1,
            "unit_price": 300.0,
        },
    ).json()

    first_submit = client.post(f"/offers/{offer_id}/submit", headers=SELLER_HEADERS)
    assert first_submit.status_code == 200
    assert first_submit.json()["status"] == "SUBMITTED_OPTIONS"

    update_response = client.put(
        f"/offers/{offer_id}/items/{added_item['id']}",
        headers=SELLER_HEADERS,
        json={"description": "Amortecedor Monroe", "unit_price": 320.0},
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "Amortecedor Monroe"

    add_alternative_response = client.post(
        f"/offers/{offer_id}/items",
        headers=SELLER_HEADERS,
        json={
            "requested_item_id": requested_item_id,
            "source_type": "manual",
            "description": "Amortecedor Nakata",
            "quantity": 1,
            "unit_price": 310.0,
        },
    )
    assert add_alternative_response.status_code == 200

    resubmit_response = client.post(f"/offers/{offer_id}/submit", headers=SELLER_HEADERS)
    assert resubmit_response.status_code == 200
    resubmitted = resubmit_response.json()
    assert resubmitted["status"] == "SUBMITTED_OPTIONS"
    assert resubmitted["final_total"] is None
    assert len(resubmitted["groups"][0]["options"]) == 2


def test_submit_offer_with_close_quote_creates_service_order_and_closes_thread(client: TestClient):
    create_response = client.post(
        "/threads",
        headers=MECHANIC_HEADERS,
        json={
            "requested_items": [
                {"description": "Pastilha de freio dianteira", "quantity": 1, "notes": "Cliente precisa do carro ainda hoje."},
                {"description": "Alternador", "quantity": 1},
            ],
            "vehicle": {"brand": "VW", "model": "Golf", "year": "2019", "engine": "1.4 TSI"},
        },
    )
    thread_id = create_response.json()["thread"]["id"]
    requested_items = create_response.json()["requested_items"]

    offer_id = client.post(f"/threads/{thread_id}/offers", headers=SELLER_HEADERS).json()["id"]
    client.post(
        f"/offers/{offer_id}/items",
        headers=SELLER_HEADERS,
        json={
            "requested_item_id": requested_items[0]["id"],
            "source_type": "manual",
            "description": "Pastilha premium cerâmica",
            "brand": "Cobreq",
            "part_number": "N-1234",
            "quantity": 1,
            "unit_price": 420.0,
            "notes": "Pronta entrega",
        },
    )
    client.post(
        f"/offers/{offer_id}/items",
        headers=SELLER_HEADERS,
        json={
            "requested_item_id": requested_items[1]["id"],
            "source_type": "manual",
            "description": "Alternador Bosch X",
            "brand": "Bosch",
            "part_number": "ALT-X",
            "quantity": 1,
            "unit_price": 1420.5,
        },
    )

    submit_response = client.post(
        f"/offers/{offer_id}/submit",
        headers=SELLER_HEADERS,
        json={"close_quote": True},
    )
    assert submit_response.status_code == 200
    submitted = submit_response.json()
    assert submitted["offer_id"] == offer_id
    assert submitted["status"] == "proposal_sent"
    assert submitted["thread_status"] == "closed"
    assert submitted["service_order_id"] == f"so_{offer_id}"
    assert submitted["total_amount"] == 1840.5
    assert submitted["final_total"] == 1840.5

    detail_response = client.get(f"/threads/{thread_id}", headers=MECHANIC_HEADERS)
    assert detail_response.status_code == 200
    assert detail_response.json()["thread"]["status"] == "closed"


def test_submit_offer_validation_and_authorization(client: TestClient):
    create_response = client.post(
        "/threads",
        headers=MECHANIC_HEADERS,
        json={"requested_items": [{"description": "Filtro de óleo", "quantity": 1}]},
    )
    thread_id = create_response.json()["thread"]["id"]

    offer_response = client.post(f"/threads/{thread_id}/offers", headers=SELLER_HEADERS)
    offer_id = offer_response.json()["id"]

    empty_submit = client.post(f"/offers/{offer_id}/submit", headers=SELLER_HEADERS)
    assert empty_submit.status_code == 422

    invalid_access = client.get(f"/threads/{thread_id}", headers=OTHER_MECHANIC_HEADERS)
    assert invalid_access.status_code == 401

    other_seller_access = client.post(f"/threads/{thread_id}/offers", headers=OTHER_SELLER_HEADERS)
    assert other_seller_access.status_code == 200
    assert other_seller_access.json()["seller_id"] == 22


def test_mechanic_can_list_and_detail_service_orders(client: TestClient):
    first_thread = client.post(
        "/threads",
        headers=MECHANIC_HEADERS,
        json={"requested_items": [{"description": "Pastilha de freio dianteira", "quantity": 1, "notes": "Cliente precisa do carro ainda hoje."}]},
    ).json()
    first_offer_id = client.post(f"/threads/{first_thread['thread']['id']}/offers", headers=SELLER_HEADERS).json()["id"]
    client.post(
        f"/offers/{first_offer_id}/items",
        headers=SELLER_HEADERS,
        json={
            "requested_item_id": first_thread["requested_items"][0]["id"],
            "source_type": "manual",
            "description": "Pastilha premium cerâmica",
            "brand": "Cobreq",
            "part_number": "N-1234",
            "quantity": 1,
            "unit_price": 420.0,
            "notes": "Pronta entrega",
        },
    )
    client.post(
        f"/offers/{first_offer_id}/submit",
        headers=SELLER_HEADERS,
        json={"close_quote": True},
    )

    second_thread = client.post(
        "/threads",
        headers=MECHANIC_HEADERS,
        json={"requested_items": [{"description": "Alternador", "quantity": 1}], "vehicle": {"brand": "VW", "model": "Golf", "year": "2019", "engine": "1.4 TSI"}},
    ).json()
    second_offer_id = client.post(f"/threads/{second_thread['thread']['id']}/offers", headers=SELLER_HEADERS).json()["id"]
    client.post(
        f"/offers/{second_offer_id}/items",
        headers=SELLER_HEADERS,
        json={
            "requested_item_id": second_thread["requested_items"][0]["id"],
            "source_type": "manual",
            "description": "Alternador Bosch X",
            "brand": "Bosch",
            "part_number": "ALT-X",
            "quantity": 1,
            "unit_price": 1420.5,
        },
    )
    client.post(
        f"/offers/{second_offer_id}/submit",
        headers=SELLER_HEADERS,
        json={"close_quote": True},
    )

    list_response = client.get("/mechanic/service-orders", headers=MECHANIC_HEADERS)
    assert list_response.status_code == 200
    rows = list_response.json()
    assert [row["offer_id"] for row in rows] == [second_offer_id, first_offer_id]
    assert rows[0]["id"] == f"so_{second_offer_id}"
    assert rows[0]["status"] == "proposal_sent"
    assert rows[0]["vehicle_summary"] == "VW Golf 2019 1.4 TSI"

    detail_response = client.get(f"/mechanic/service-orders/so_{first_offer_id}", headers=MECHANIC_HEADERS)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["offer_id"] == first_offer_id
    assert detail["request_notes"] == "Cliente precisa do carro ainda hoje."
    assert detail["auto_parts"]["name"] == "Autopeças Azul"
    assert detail["seller"]["name"] == "Carlos Silva"
    assert detail["items"][0]["line_total"] == 420.0
    assert detail["total_amount"] == 420.0


def test_closed_legacy_submitted_offer_is_exposed_as_service_order(client: TestClient):
    thread = client.post(
        "/threads",
        headers=MECHANIC_HEADERS,
        json={"requested_items": [{"description": "Filtro de óleo", "quantity": 1}]},
    ).json()
    offer_id = client.post(f"/threads/{thread['thread']['id']}/offers", headers=SELLER_HEADERS).json()["id"]
    client.post(
        f"/offers/{offer_id}/items",
        headers=SELLER_HEADERS,
        json={
            "requested_item_id": thread["requested_items"][0]["id"],
            "source_type": "manual",
            "description": "Filtro Tecfil",
            "quantity": 1,
            "unit_price": 89.9,
        },
    )
    client.post(f"/offers/{offer_id}/submit", headers=SELLER_HEADERS)
    client.patch(
        f"/seller/inbox/{thread['thread']['id']}",
        headers=SELLER_HEADERS,
        json={"status": "closed"},
    )

    list_response = client.get("/mechanic/service-orders", headers=MECHANIC_HEADERS)
    assert list_response.status_code == 200
    row = next(item for item in list_response.json() if item["offer_id"] == offer_id)
    assert row["status"] == "proposal_sent"
    assert row["total_amount"] == 89.9

    detail_response = client.get(f"/mechanic/service-orders/so_{offer_id}", headers=MECHANIC_HEADERS)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["status"] == "proposal_sent"
    assert detail["total_amount"] == 89.9


def test_seller_inbox_reads_workshop_and_current_offer_from_browser_threads(client: TestClient):
    create_response = client.post(
        "/threads",
        headers=MECHANIC_HEADERS,
        json={
            "requested_items": [{"description": "Alternador", "quantity": 1}],
            "vehicle": {"brand": "Volkswagen", "model": "Gol", "year": "2019"},
        },
    )
    thread_id = create_response.json()["thread"]["id"]
    requested_item_id = create_response.json()["requested_items"][0]["id"]
    offer_id = client.post(f"/threads/{thread_id}/offers", headers=SELLER_HEADERS).json()["id"]
    client.post(
        f"/offers/{offer_id}/items",
        headers=SELLER_HEADERS,
        json={
            "requested_item_id": requested_item_id,
            "source_type": "manual",
            "description": "Alternador Bosch",
            "quantity": 1,
            "unit_price": 850.0,
        },
    )
    client.post(f"/offers/{offer_id}/submit", headers=SELLER_HEADERS)

    inbox_response = client.get("/seller/inbox", headers=SELLER_HEADERS)
    assert inbox_response.status_code == 200
    assert inbox_response.json()["items"][0]["inbox_item_id"] == str(thread_id)

    detail_response = client.get(f"/seller/inbox/{thread_id}", headers=SELLER_HEADERS)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["workshop"]["name"] == "Oficina Azul"
    assert detail["workshop"]["phone"] == "+5511999999999"
    assert detail["current_offer"]["summary_text"] == "Resposta enviada com 1 opção para Alternador."
