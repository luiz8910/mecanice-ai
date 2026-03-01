from __future__ import annotations

from src.bot.application.dtos.quote_workflow import MechanicQuoteRequestDTO
from src.bot.application.services.idempotency_registry import InMemoryIdempotencyRegistry
from src.bot.application.useCases.dispatch_quote_request_webhook import (
    DispatchQuoteRequestWebhookUseCase,
)
from src.bot.infrastructure.logging import get_logger

logger = get_logger(__name__)


class ProcessMechanicWhatsAppMessageUseCase:
    def __init__(
        self,
        dispatch_use_case: DispatchQuoteRequestWebhookUseCase,
        idempotency_registry: InMemoryIdempotencyRegistry,
    ) -> None:
        self._dispatch_use_case = dispatch_use_case
        self._idempotency_registry = idempotency_registry

    async def execute(self, request: MechanicQuoteRequestDTO) -> bool:
        if self._idempotency_registry.seen(request.event_id):
            logger.info("Duplicate WhatsApp event ignored event_id=%s", request.event_id)
            return False

        self._idempotency_registry.mark(request.event_id)
        await self._dispatch_use_case.execute(request)
        return True
