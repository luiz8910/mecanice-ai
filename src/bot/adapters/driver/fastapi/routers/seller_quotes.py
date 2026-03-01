from __future__ import annotations

from fastapi import APIRouter, Depends, Header

from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_quote_workflow_repo,
    get_vendor_repo,
)
from src.bot.adapters.driver.fastapi.dependencies.use_cases import (
    get_vehicle_plate_resolver,
    get_submit_vendor_offer_use_case,
)
from src.bot.adapters.driver.fastapi.schemas.seller_quotes import (
    VendorOfferSubmissionSchema,
)
from src.bot.adapters.driver.fastapi.schemas.sales import ConversationSaleCreateSchema
from src.bot.adapters.driven.db.repositories.quote_workflow_repo_sa import (
    QuoteWorkflowRepoSqlAlchemy,
)
from src.bot.adapters.driven.db.repositories.vendor_repo_sa import VendorRepoSqlAlchemy
from src.bot.application.dtos.quote_workflow import VendorQuoteOfferDTO
from src.bot.application.useCases.submit_vendor_offer_and_notify_mechanic import (
    SubmitVendorOfferAndNotifyMechanicUseCase,
)
from src.bot.application.services.vehicle_plate_resolver import VehiclePlateResolver
from src.bot.domain.errors import ValidationError

router = APIRouter(prefix="/seller", tags=["seller"])


@router.post("/quotes/offers")
async def submit_offer(
    body: VendorOfferSubmissionSchema,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    use_case: SubmitVendorOfferAndNotifyMechanicUseCase = Depends(
        get_submit_vendor_offer_use_case
    ),
    vehicle_plate_resolver: VehiclePlateResolver = Depends(get_vehicle_plate_resolver),
    workflow_repo: QuoteWorkflowRepoSqlAlchemy = Depends(get_quote_workflow_repo),
    vendor_repo: VendorRepoSqlAlchemy = Depends(get_vendor_repo),
):
    conversation = workflow_repo.get_conversation_context(body.conversation_id)
    if conversation is None:
        raise ValidationError("conversation_id not found")

    if str(conversation.vendor_id) != str(body.vendor_id):
        raise ValidationError("vendor_id does not match assigned vendor for conversation")
    if str(conversation.autopart_id) != str(body.store_id):
        raise ValidationError("store_id does not match conversation")
    if body.request_id != conversation.request_id:
        raise ValidationError("request_id does not match conversation")

    mechanic_phone = body.mechanic_phone_e164 or conversation.mechanic_phone_e164
    resolved_vehicle = body.vehicle
    if resolved_vehicle is None:
        resolved_vehicle = await vehicle_plate_resolver.resolve_from_text(
            conversation.last_mechanic_message
        )

    vehicle_info = body.vehicle_info or vehicle_plate_resolver.to_vehicle_info(resolved_vehicle)
    vehicle_plate = body.vehicle_plate or (resolved_vehicle or {}).get("plate")

    delivered = use_case.execute(
        VendorQuoteOfferDTO(
            conversation_id=body.conversation_id,
            request_id=body.request_id,
            mechanic_phone_e164=mechanic_phone,
            store_id=body.store_id,
            vendor_id=body.vendor_id,
            store_name=body.store_name,
            price=body.price,
            currency=body.currency,
            brand=body.brand,
            availability=body.availability,
            delivery=body.delivery,
            vehicle_plate=vehicle_plate,
            vehicle=resolved_vehicle,
            vehicle_info=vehicle_info,
            notes=body.notes,
            idempotency_key=x_idempotency_key,
        )
    )
    vendor_repo.record_quote_received(
        vendor_id=conversation.vendor_id,
        autopart_id=conversation.autopart_id,
        workshop_id=conversation.workshop_id,
        conversation_id=conversation.conversation_id,
        request_id=conversation.request_id,
    )
    workflow_repo.touch_conversation(body.conversation_id)
    return {"ok": True, "delivered_to_mechanic": delivered}


@router.post("/conversations/{conversation_id}/sales")
def register_sale(
    conversation_id: str,
    body: ConversationSaleCreateSchema,
    workflow_repo: QuoteWorkflowRepoSqlAlchemy = Depends(get_quote_workflow_repo),
    vendor_repo: VendorRepoSqlAlchemy = Depends(get_vendor_repo),
):
    conversation = workflow_repo.get_conversation_context(conversation_id)
    if conversation is None:
        raise ValidationError("conversation_id not found")

    if str(conversation.vendor_id) != str(body.vendor_id):
        raise ValidationError("vendor_id does not match assigned vendor for conversation")
    if str(conversation.autopart_id) != str(body.store_id):
        raise ValidationError("store_id does not match conversation")
    if body.request_id != conversation.request_id:
        raise ValidationError("request_id does not match conversation")

    vendor_repo.record_sale_converted(
        vendor_id=conversation.vendor_id,
        autopart_id=conversation.autopart_id,
        workshop_id=conversation.workshop_id,
        conversation_id=conversation.conversation_id,
        request_id=conversation.request_id,
        metadata={
            "sale_value": body.sale_value,
            "notes": body.notes,
        },
    )
    workflow_repo.touch_conversation(conversation_id)
    return {"ok": True, "sale_recorded": True}
