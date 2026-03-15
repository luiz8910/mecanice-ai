"""Test-only WhatsApp-like chat page and API endpoints.

This router intentionally keeps an in-memory message store and must not be used
in production workflows.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from random import choice
from threading import Lock
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.bot.adapters.driven.llm.llm_recommendation_adapter import LlmError
from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_quotation_item_repo,
    get_quotation_repo,
    get_vendor_repo,
    get_workshop_repo,
)
from src.bot.adapters.driver.fastapi.dependencies.use_cases import (
    get_fanout_use_case,
)
from src.bot.adapters.driven.db.repositories.quotation_item_repo_sa import (
    QuotationItemRepoSqlAlchemy,
)
from src.bot.adapters.driven.db.repositories.quotation_repo_sa import (
    QuotationRepoSqlAlchemy,
)
from src.bot.adapters.driven.db.repositories.vendor_repo_sa import VendorRepoSqlAlchemy
from src.bot.adapters.driven.db.repositories.workshop_repo_sa import (
    WorkshopRepoSqlAlchemy,
)
from src.bot.application.dtos.recommendation.part_request import PartRequest
from src.bot.application.dtos.recommendation.recommendation_request import (
    RecommendationRequest,
)
from src.bot.application.useCases.fanout_quote_requests import (
    FanoutQuoteRequestsUseCase,
)
from src.bot.adapters.driven.whatsapp.test_message_sink import (
    clear_outbound_messages,
    list_outbound_messages,
)

router = APIRouter(prefix="/test/whatsapp", tags=["test-whatsapp-chat"])

_STATIC_PAGE = Path(__file__).resolve().parent.parent / "static" / "whatsapp_chat_teste.html"

_lock = Lock()
_seen_outbound_ids: set[str] = set()
_messages: list[dict] = [
    {
        "id": str(uuid4()),
        "direction": "incoming",
        "text": "Ambiente de teste iniciado. Pode enviar mensagens.",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
]


class ChatMessageCreate(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    direction: Literal["incoming", "outgoing"] = "outgoing"
    persist_quotation: bool = True
    seller_id: int | None = Field(default=None, gt=0)
    workshop_id: int | None = Field(default=None, gt=0)
    part_number: str | None = Field(default=None, max_length=255)
    create_item: bool = True
    item_price: float | None = Field(default=None, ge=0)
    use_llm: bool = True


class SimulateReplyRequest(BaseModel):
    text: str | None = Field(default=None, max_length=4000)


def _append_message(text: str, direction: Literal["incoming", "outgoing"]) -> dict:
    message = {
        "id": str(uuid4()),
        "direction": direction,
        "text": text,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        _messages.append(message)
    return message


def _build_code() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = uuid4().hex[:6].upper()
    return f"CHAT-{stamp}-{suffix}"


def _resolve_defaults(
    payload: ChatMessageCreate,
    vendor_repo: VendorRepoSqlAlchemy,
    workshop_repo: WorkshopRepoSqlAlchemy,
) -> tuple[int | None, int | None]:
    seller_id = payload.seller_id
    workshop_id = payload.workshop_id

    if seller_id is None:
        vendors = vendor_repo.list_vendors(limit=1, offset=0, active=True)
        if vendors:
            seller_id = int(vendors[0]["id"])

    if workshop_id is None:
        workshops = workshop_repo.list_rows(limit=1, offset=0)
        if workshops:
            workshop_id = int(workshops[0]["id"])

    return seller_id, workshop_id


async def _persist_as_quotation(
    *,
    payload: ChatMessageCreate,
    quotation_repo: QuotationRepoSqlAlchemy,
    quotation_item_repo: QuotationItemRepoSqlAlchemy,
    vendor_repo: VendorRepoSqlAlchemy,
    workshop_repo: WorkshopRepoSqlAlchemy,
    fanout_use_case: FanoutQuoteRequestsUseCase,
) -> dict:
    seller_id, workshop_id = _resolve_defaults(payload, vendor_repo, workshop_repo)
    if seller_id is None or workshop_id is None:
        raise ValueError(
            "Nao foi possivel resolver seller_id/workshop_id. Selecione manualmente no painel."
        )

    original_text = payload.text.strip()
    base_part_number = (payload.part_number or "").strip() or original_text[:120]
    recommendation = None

    if payload.create_item and payload.use_llm:
        recommendation_request = RecommendationRequest(
            requester_id=f"test-whatsapp-workshop-{workshop_id}",
            vehicle=None,
            parts=[
                PartRequest(
                    part_number=(payload.part_number or None),
                    description=original_text,
                    quantity=1,
                )
            ],
            context={
                "channel": "test_whatsapp",
                "seller_id": str(seller_id),
                "workshop_id": str(workshop_id),
            },
        )
        try:
            recommendation = await fanout_use_case.execute(recommendation_request)
        except LlmError as exc:
            raise ValueError(f"Falha na cotacao via IA: {exc}") from exc

        if not recommendation or not recommendation.candidates:
            raise ValueError(
                "Falha na cotacao via IA: nenhum candidato de peca foi retornado."
            )

    top_candidate = (recommendation.candidates or [None])[0] if recommendation else None
    part_number = (top_candidate.part_number if top_candidate else None) or base_part_number
    first_description = (
        (top_candidate.metadata or {}).get("description") if top_candidate else None
    )

    quotation = quotation_repo.create_quotation(
        {
            "code": _build_code(),
            "seller_id": seller_id,
            "workshop_id": workshop_id,
            "part_number": part_number,
            "part_description": first_description or original_text,
            "vehicle_info": "Teste via chat local",
            "status": "NEW",
            "is_urgent": False,
            "offer_submitted": False,
            "original_message": original_text,
            "notes": "Criado automaticamente pelo /test/whatsapp",
        }
    )

    items: list[dict] = []
    if payload.create_item:
        if recommendation and recommendation.candidates:
            for idx, candidate in enumerate(recommendation.candidates):
                metadata = candidate.metadata or {}
                confidence = candidate.score
                confidence_pct = None
                if confidence is not None:
                    confidence_pct = max(0.0, min(100.0, float(confidence) * 100.0))

                item_payload = {
                    "part_number": candidate.part_number or base_part_number,
                    "description": metadata.get("description") or original_text,
                    "brand": candidate.brand,
                    "compatibility": metadata.get("compatibility_notes"),
                    "price": candidate.average_price_brl,
                    "availability": "Em estoque",
                    "confidence_score": confidence_pct,
                    "notes": metadata.get("origin"),
                    "selected": False,
                }

                if payload.item_price is not None and payload.item_price > 0 and idx == 0:
                    item_payload["price"] = payload.item_price
                    item_payload["selected"] = True

                item = quotation_item_repo.add_item(
                    quotation_id=int(quotation["id"]),
                    seller_id=int(quotation["seller_id"]),
                    payload=item_payload,
                )
                items.append(item)
        else:
            item_payload = {
                "part_number": part_number,
                "description": original_text,
                "selected": payload.item_price is not None and payload.item_price > 0,
                "availability": "Em estoque",
            }
            if payload.item_price is not None and payload.item_price > 0:
                item_payload["price"] = payload.item_price

            item = quotation_item_repo.add_item(
                quotation_id=int(quotation["id"]),
                seller_id=int(quotation["seller_id"]),
                payload=item_payload,
            )
            items.append(item)

    return {
        "quotation": quotation,
        "items": items,
        "llm_candidates_count": len(recommendation.candidates or []) if recommendation else 0,
    }


@router.get("", response_class=FileResponse)
def test_chat_page() -> FileResponse:
    """Serves a single-page WhatsApp-like UI for local tests."""
    return FileResponse(_STATIC_PAGE)


@router.get("/api/messages")
def list_messages() -> dict:
    outbound = list_outbound_messages(limit=250)
    with _lock:
        for item in outbound:
            item_id = str(item.get("id") or "")
            if not item_id or item_id in _seen_outbound_ids:
                continue
            _seen_outbound_ids.add(item_id)
            _messages.append(
                {
                    "id": item_id,
                    "direction": "incoming",
                    "text": f"Oferta enviada ao WhatsApp: {item.get('text', '')}",
                    "created_at": item.get("created_at") or datetime.now(timezone.utc).isoformat(),
                }
            )
        # Keeps payload bounded for polling clients.
        items = list(_messages[-250:])
    return {"messages": items}


@router.get("/api/context")
def get_context(
    vendor_repo: VendorRepoSqlAlchemy = Depends(get_vendor_repo),
    workshop_repo: WorkshopRepoSqlAlchemy = Depends(get_workshop_repo),
) -> dict:
    vendors = vendor_repo.list_vendors(limit=100, offset=0, active=True)
    workshops = workshop_repo.list_rows(limit=100, offset=0)
    return {
        "vendors": [
            {
                "id": int(v["id"]),
                "name": v["name"],
                "autopart_id": int(v["autopart_id"]),
            }
            for v in vendors
        ],
        "workshops": [
            {
                "id": int(w["id"]),
                "name": w["name"],
                "status": w.get("status"),
            }
            for w in workshops
        ],
        "defaults": {
            "seller_id": int(vendors[0]["id"]) if vendors else None,
            "workshop_id": int(workshops[0]["id"]) if workshops else None,
        },
    }


@router.post("/api/messages")
async def send_message(
    payload: ChatMessageCreate,
    quotation_repo: QuotationRepoSqlAlchemy = Depends(get_quotation_repo),
    quotation_item_repo: QuotationItemRepoSqlAlchemy = Depends(get_quotation_item_repo),
    vendor_repo: VendorRepoSqlAlchemy = Depends(get_vendor_repo),
    workshop_repo: WorkshopRepoSqlAlchemy = Depends(get_workshop_repo),
    fanout_use_case: FanoutQuoteRequestsUseCase = Depends(get_fanout_use_case),
) -> dict:
    message = _append_message(payload.text.strip(), payload.direction)
    persisted: dict | None = None
    persist_error: str | None = None

    if payload.direction == "outgoing" and payload.persist_quotation:
        try:
            persisted = await _persist_as_quotation(
                payload=payload,
                quotation_repo=quotation_repo,
                quotation_item_repo=quotation_item_repo,
                vendor_repo=vendor_repo,
                workshop_repo=workshop_repo,
                fanout_use_case=fanout_use_case,
            )
            quotation = persisted["quotation"]
            items_count = len(persisted.get("items") or [])
            llm_candidates_count = int(persisted.get("llm_candidates_count") or 0)
            llm_note = (
                f" | candidatos_ia={llm_candidates_count}" if llm_candidates_count > 0 else ""
            )
            _append_message(
                (
                    "Cotacao criada no banco: "
                    f"ID={quotation['id']} | CODE={quotation['code']} | "
                    f"seller_id={quotation['seller_id']} | workshop_id={quotation['workshop_id']} | "
                    f"itens={items_count}{llm_note}"
                ),
                "incoming",
            )
        except Exception as exc:  # test-only endpoint
            persist_error = str(exc)
            _append_message(f"Falha ao persistir cotacao: {persist_error}", "incoming")

    return {"message": message, "persisted": persisted, "error": persist_error}


@router.post("/api/simulate-reply")
def simulate_reply(payload: SimulateReplyRequest) -> dict:
    canned_replies = [
        "Recebido. Estou validando aqui.",
        "Mensagem recebida com sucesso no ambiente local.",
        "Fluxo OK. Pode seguir com o proximo teste.",
        "Resposta simulada via endpoint de teste.",
    ]
    text = (payload.text or "").strip() or choice(canned_replies)
    message = _append_message(text, "incoming")
    return {"message": message}


@router.delete("/api/messages")
def clear_messages() -> dict:
    clear_outbound_messages()
    with _lock:
        _seen_outbound_ids.clear()
        _messages.clear()
        _messages.append(
            {
                "id": str(uuid4()),
                "direction": "incoming",
                "text": "Chat limpo. Pronto para novo teste.",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        items = list(_messages)
    return {"messages": items}
