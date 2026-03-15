from __future__ import annotations

import httpx

from src.bot.adapters.driven.whatsapp.test_message_sink import record_outbound_message
from src.bot.application.dtos.messaging import OutgoingMessageDTO
from src.bot.infrastructure.config.settings import Settings, settings
from src.bot.infrastructure.logging import get_logger

logger = get_logger(__name__)


class WhatsAppService:
    def __init__(self, app_settings: Settings = settings) -> None:
        self._settings = app_settings

    def send_text(self, to: str, text: str) -> None:
        if not to or not text:
            raise ValueError("to and text are required")

        # Test mirror: keep local visibility of outbound messages regardless of
        # external provider availability.
        record_outbound_message(
            OutgoingMessageDTO(recipient=to, text=text, metadata={"channel": "whatsapp_service"})
        )

        access_token = self._settings.WHATSAPP_ACCESS_TOKEN or self._settings.META_WHATSAPP_TOKEN
        phone_number_id = self._settings.WHATSAPP_PHONE_NUMBER_ID or self._settings.META_WHATSAPP_PHONE_NUMBER_ID

        if not access_token or not phone_number_id:
            logger.warning(
                "WhatsApp credentials missing; skipping send to=%s",
                to,
            )
            return

        base_url = (
            self._settings.WHATSAPP_API_BASE_URL
            or self._settings.META_WHATSAPP_API_BASE_URL
        ).rstrip("/")
        url = f"{base_url}/{phone_number_id}/messages"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }

        with httpx.Client(timeout=self._settings.META_WHATSAPP_TIMEOUT_SECONDS) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        logger.info("WhatsApp message sent to=%s", to)
