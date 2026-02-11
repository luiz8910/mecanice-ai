"""WhatsApp webhook router (not yet wired in `app_factory`).

Keeping this module non-empty avoids confusing 0-byte placeholders.
The handler is intentionally minimal and can be expanded later.
"""

from __future__ import annotations

from fastapi import APIRouter, Response

from src.bot.adapters.driver.fastapi.schemas.whatsapp_cloud_api import (
	WhatsAppWebhookPayload,
)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.post("/webhook", status_code=204)
async def ingest_webhook(_: WhatsAppWebhookPayload) -> Response:
	"""Acknowledge webhook delivery.

	TODO: validate signature, deduplicate events, and route messages to
	the application layer.
	"""

	return Response(status_code=204)

