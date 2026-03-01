"""WhatsApp Cloud API client (driven adapter).

Translates `OutgoingMessageDTO` into Meta HTTP API calls.
"""

from __future__ import annotations

import httpx

from src.bot.application.dtos.messaging import IncomingMessageDTO, OutgoingMessageDTO
from src.bot.application.ports.driven.messaging import MessagingPort
from src.bot.infrastructure.config.settings import Settings
from src.bot.infrastructure.logging import get_logger

logger = get_logger(__name__)


class MetaCloudApiClient(MessagingPort):
	def __init__(self, settings: Settings) -> None:
		self._settings = settings

	def send(self, message: OutgoingMessageDTO) -> None:
		if not message.recipient or not message.text:
			raise ValueError("recipient and text are required to send WhatsApp")

		if (
			not self._settings.META_WHATSAPP_TOKEN
			or not self._settings.META_WHATSAPP_PHONE_NUMBER_ID
		):
			logger.warning(
				"WhatsApp credentials missing; skipping send recipient=%s",
				message.recipient,
			)
			return

		base_url = self._settings.META_WHATSAPP_API_BASE_URL.rstrip("/")
		url = f"{base_url}/{self._settings.META_WHATSAPP_PHONE_NUMBER_ID}/messages"
		headers = {
			"Authorization": f"Bearer {self._settings.META_WHATSAPP_TOKEN}",
			"Content-Type": "application/json",
		}
		payload = {
			"messaging_product": "whatsapp",
			"to": message.recipient,
			"type": "text",
			"text": {"body": message.text},
		}

		with httpx.Client(timeout=self._settings.META_WHATSAPP_TIMEOUT_SECONDS) as client:
			response = client.post(url, json=payload, headers=headers)
			response.raise_for_status()

		logger.info("WhatsApp message sent recipient=%s", message.recipient)

	def receive(self) -> IncomingMessageDTO:
		raise NotImplementedError(
			"Meta Cloud API receive() not implemented; use webhook router"
		)

