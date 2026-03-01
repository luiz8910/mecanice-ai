from __future__ import annotations

from src.bot.application.dtos.quote_workflow import MechanicQuoteRequestDTO
from src.bot.application.ports.driven.webhook_dispatcher import WebhookDispatcherPort
from src.bot.infrastructure.logging import get_logger

logger = get_logger(__name__)


class DispatchQuoteRequestWebhookUseCase:
    def __init__(self, dispatcher: WebhookDispatcherPort) -> None:
        self._dispatcher = dispatcher

    async def execute(self, request: MechanicQuoteRequestDTO) -> None:
        payload = {
            "request_id": request.request_id,
            "conversation_id": request.conversation_id,
            "mechanic_phone_e164": request.mechanic_phone_e164,
            "workshop_id": request.workshop_id,
            "store_id": request.store_id,
            "store_name": request.store_name,
            "vendor_id": request.vendor_id,
            "vendor_name": request.vendor_name,
            "part_number": request.part_number,
            "vehicle_plate": request.vehicle_plate,
            "vehicle": request.vehicle,
            "vehicle_info": request.vehicle_info,
            "notes": request.notes,
            "created_at": request.raw_payload.get("timestamp"),
            "raw_payload": request.raw_payload,
        }

        await self._dispatcher.dispatch(
            event_type="QUOTE_REQUEST_ASSIGNED",
            event_id=request.event_id,
            payload=payload,
        )

        logger.info(
            "Quote request dispatched request_id=%s event_id=%s",
            request.request_id,
            request.event_id,
        )
