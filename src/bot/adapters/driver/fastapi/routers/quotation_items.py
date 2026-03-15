"""Routes for quotation items (peças) and offer submission."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from src.bot.adapters.driver.fastapi.dependencies.auth import (
    SellerIdentity,
    require_seller,
)
from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_quotation_item_repo,
)
from src.bot.adapters.driver.fastapi.schemas.quotation_items import (
    QuotationEventSchema,
    QuotationItemCreateSchema,
    QuotationItemResponseSchema,
    QuotationItemUpdateSchema,
    SubmitOfferResponseSchema,
)
from src.bot.adapters.driven.db.repositories.quotation_item_repo_sa import (
    QuotationItemRepoSqlAlchemy,
)
from src.bot.adapters.driven.whatsapp.test_message_sink import record_outbound_message
from src.bot.application.dtos.messaging import OutgoingMessageDTO
from src.bot.infrastructure.logging import get_logger
from src.bot.tasks.whatsapp import send_quote_whatsapp

router = APIRouter(prefix="/seller/inbox", tags=["seller-items"])
logger = get_logger(__name__)


# ── Items CRUD ───────────────────────────────────────────────────

@router.get(
    "/{quotation_id}/items",
    response_model=list[QuotationItemResponseSchema],
    summary="Listar peças de uma cotação",
)
async def list_items(
    quotation_id: int,
    seller: SellerIdentity = Depends(require_seller),
    repo: QuotationItemRepoSqlAlchemy = Depends(get_quotation_item_repo),
):
    return repo.list_items(quotation_id=quotation_id, seller_id=seller.vendor_id)


@router.post(
    "/{quotation_id}/items",
    response_model=QuotationItemResponseSchema,
    summary="Adicionar peça manual a uma cotação",
)
async def add_item(
    quotation_id: int,
    body: QuotationItemCreateSchema,
    seller: SellerIdentity = Depends(require_seller),
    repo: QuotationItemRepoSqlAlchemy = Depends(get_quotation_item_repo),
):
    return repo.add_item(
        quotation_id=quotation_id,
        seller_id=seller.vendor_id,
        payload=body.model_dump(),
    )


@router.patch(
    "/{quotation_id}/items/{item_id}",
    response_model=QuotationItemResponseSchema,
    summary="Atualizar peça (definir preço, selecionar, etc.)",
)
async def update_item(
    quotation_id: int,
    item_id: int,
    body: QuotationItemUpdateSchema,
    seller: SellerIdentity = Depends(require_seller),
    repo: QuotationItemRepoSqlAlchemy = Depends(get_quotation_item_repo),
):
    return repo.update_item(
        item_id=item_id,
        quotation_id=quotation_id,
        seller_id=seller.vendor_id,
        payload=body.model_dump(exclude_unset=True),
    )


@router.delete(
    "/{quotation_id}/items/{item_id}",
    status_code=204,
    summary="Remover peça de uma cotação",
)
async def delete_item(
    quotation_id: int,
    item_id: int,
    seller: SellerIdentity = Depends(require_seller),
    repo: QuotationItemRepoSqlAlchemy = Depends(get_quotation_item_repo),
) -> Response:
    repo.delete_item(
        item_id=item_id,
        quotation_id=quotation_id,
        seller_id=seller.vendor_id,
    )
    return Response(status_code=204)


# ── Events / History ─────────────────────────────────────────────

@router.get(
    "/{quotation_id}/events",
    response_model=list[QuotationEventSchema],
    summary="Histórico de eventos da cotação",
)
async def list_events(
    quotation_id: int,
    seller: SellerIdentity = Depends(require_seller),
    repo: QuotationItemRepoSqlAlchemy = Depends(get_quotation_item_repo),
):
    return repo.list_events(quotation_id=quotation_id, seller_id=seller.vendor_id)


# ── Submit Offer ─────────────────────────────────────────────────

@router.post(
    "/{quotation_id}/offer",
    response_model=SubmitOfferResponseSchema,
    summary="Confirmar e enviar orçamento (peças selecionadas)",
)
async def submit_offer(
    quotation_id: int,
    seller: SellerIdentity = Depends(require_seller),
    repo: QuotationItemRepoSqlAlchemy = Depends(get_quotation_item_repo),
):
    result = repo.submit_offer(
        quotation_id=quotation_id,
        seller_id=seller.vendor_id,
    )

    # Mirror a WhatsApp-like return to the test chat to validate end-to-end flow.
    record_outbound_message(
        OutgoingMessageDTO(
            recipient=f"seller:{seller.vendor_id}",
            text=(
                f"Cotacao {quotation_id} enviada. "
                f"Itens: {result['items_count']} | Total: R$ {result['total']:.2f}"
            ),
            metadata={
                "quotation_id": str(quotation_id),
                "seller_id": str(seller.vendor_id),
                "source": "seller_inbox_offer",
            },
        )
    )

    try:
        send_quote_whatsapp.delay(str(quotation_id))
    except Exception as exc:
        # Do not break seller flow in local/dev if broker is unavailable.
        logger.warning("Failed to enqueue WhatsApp send for quotation_id=%s: %s", quotation_id, exc)

    return result
