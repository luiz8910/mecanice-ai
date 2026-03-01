"""WhatsApp webhook router.

Receives mechanic-only WhatsApp messages and dispatches a webhook event so the
Seller Portal front-end can fetch/process the quote request.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends

from src.bot.adapters.driver.fastapi.dependencies.repositories import (
	get_quote_workflow_repo,
)
from src.bot.adapters.driver.fastapi.dependencies.use_cases import (
	get_vehicle_plate_resolver,
    get_webhook_dispatcher,
)
from src.bot.adapters.driver.fastapi.schemas.whatsapp_cloud_api import (
	WhatsAppWebhookPayload,
)
from src.bot.adapters.driven.db.repositories.quote_workflow_repo_sa import (
	QuoteWorkflowRepoSqlAlchemy,
)
from src.bot.application.dtos.quote_workflow import MechanicQuoteRequestDTO
from src.bot.application.useCases.dispatch_quote_request_webhook import (
    DispatchQuoteRequestWebhookUseCase,
)
from src.bot.application.useCases.route_mechanic_message_to_conversations import (
	RouteMechanicMessageToConversationsUseCase,
)
from src.bot.application.services.vehicle_plate_resolver import VehiclePlateResolver

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _extract_messages(payload: WhatsAppWebhookPayload) -> list[dict]:
	messages: list[dict] = []
	for entry in payload.entry or []:
		for change in entry.get("changes", []):
			value = change.get("value", {})
			messages.extend(value.get("messages", []) or [])
	return messages


@router.post("/webhook")
async def ingest_webhook(
	payload: WhatsAppWebhookPayload,
	dispatcher=Depends(get_webhook_dispatcher),
	vehicle_plate_resolver: VehiclePlateResolver = Depends(get_vehicle_plate_resolver),
	workflow_repo: QuoteWorkflowRepoSqlAlchemy = Depends(get_quote_workflow_repo),
):
	"""Converts inbound mechanic messages into portal webhook events."""
	dispatch_use_case = DispatchQuoteRequestWebhookUseCase(dispatcher=dispatcher)
	route_use_case = RouteMechanicMessageToConversationsUseCase(workflow_repo)

	accepted = 0
	duplicates = 0

	for message in _extract_messages(payload):
		text_body = ((message.get("text") or {}).get("body") or "").strip()
		mechanic_phone = (message.get("from") or "").strip()
		if not text_body or not mechanic_phone:
			continue

		vehicle = await vehicle_plate_resolver.resolve_from_text(text_body)
		vehicle_info = vehicle_plate_resolver.to_vehicle_info(vehicle)

		source_event_id = message.get("id") or str(uuid4())
		conversations = route_use_case.execute(
			source_event_id=source_event_id,
			mechanic_phone_e164=mechanic_phone,
			message_text=text_body,
		)

		for conversation in conversations:
			if not conversation.created:
				duplicates += 1
				continue

			request = MechanicQuoteRequestDTO(
				request_id=conversation.request_id,
				conversation_id=conversation.conversation_id,
				event_id=conversation.conversation_id,
				mechanic_phone_e164=conversation.mechanic_phone_e164,
				workshop_id=conversation.workshop_id,
				store_id=str(conversation.autopart_id),
				store_name=conversation.autopart_name,
				vendor_id=str(conversation.vendor_id),
				vendor_name=conversation.vendor_name,
				part_number=text_body,
				vehicle_plate=(vehicle or {}).get("plate"),
				vehicle=vehicle,
				vehicle_info=vehicle_info,
				raw_payload=message,
			)
			await dispatch_use_case.execute(request)
			accepted += 1

	return {
		"ok": True,
		"accepted": accepted,
		"duplicates": duplicates,
	}

