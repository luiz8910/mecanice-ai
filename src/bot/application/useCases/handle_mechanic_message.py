"""Use case stub: handle an inbound mechanic message."""

from __future__ import annotations

from src.bot.application.dtos.messaging import IncomingMessageDTO


class HandleMechanicMessageUseCase:
	async def execute(self, message: IncomingMessageDTO) -> None:
		raise NotImplementedError("TODO: implement mechanic message handling")

