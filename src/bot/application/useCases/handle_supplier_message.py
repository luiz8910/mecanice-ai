"""Use case stub: handle an inbound supplier/auto-parts store message."""

from __future__ import annotations

from src.bot.application.dtos.messaging import IncomingMessageDTO


class HandleSupplierMessageUseCase:
	async def execute(self, message: IncomingMessageDTO) -> None:
		raise NotImplementedError("TODO: implement supplier message handling")

