from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.bot.adapters.driver.fastapi.dependencies.auth import (
    SellerIdentity,
    require_seller,
)
from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_quotation_item_repo,
)
from src.bot.adapters.driver.fastapi.schemas.quote_confirmation import (
    ConfirmAndSendQuoteRequestSchema,
    ConfirmAndSendQuoteResponseSchema,
)
from src.bot.adapters.driven.db.repositories.quotation_item_repo_sa import (
    QuotationItemRepoSqlAlchemy,
)
from src.bot.domain.errors import ValidationError
from src.bot.tasks.whatsapp import send_quote_whatsapp

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.post(
    "/{quote_id}/confirm-and-send",
    response_model=ConfirmAndSendQuoteResponseSchema,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Confirmar cotação e enviar WhatsApp de forma assíncrona",
)
async def confirm_and_send_quote(
    quote_id: int,
    body: ConfirmAndSendQuoteRequestSchema,
    seller: SellerIdentity = Depends(require_seller),
    repo: QuotationItemRepoSqlAlchemy = Depends(get_quotation_item_repo),
):
    try:
        selected_ids = [int(item_id) for item_id in body.selected_item_ids]
    except (TypeError, ValueError) as exc:
        raise ValidationError("selected_item_ids deve conter apenas IDs numéricos") from exc

    repo.confirm_and_send_offer(
        quotation_id=quote_id,
        seller_id=seller.vendor_id,
        selected_item_ids=selected_ids,
        note=body.note,
    )

    send_quote_whatsapp.delay(str(quote_id))

    return ConfirmAndSendQuoteResponseSchema(ok=True, queued=True)
