"""WhatsApp Cloud API client (driven adapter).

This is currently a stub to make the integration point explicit.
When implemented, it should translate `OutgoingMessageDTO` into Meta's
HTTP API calls and translate inbound webhooks into `IncomingMessageDTO`.
"""

from __future__ import annotations

from src.bot.application.dtos.messaging import IncomingMessageDTO, OutgoingMessageDTO
from src.bot.application.ports.driven.messaging import MessagingPort


class MetaCloudApiClient(MessagingPort):
	def send(self, message: OutgoingMessageDTO) -> None:
		raise NotImplementedError(
			"Meta Cloud API send() not implemented yet (stub adapter)"
		)

	def receive(self) -> IncomingMessageDTO:
		raise NotImplementedError(
			"Meta Cloud API receive() not implemented; use webhook router"
		)

