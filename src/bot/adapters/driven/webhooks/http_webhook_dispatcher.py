from __future__ import annotations

from typing import Any

import httpx

from src.bot.application.ports.driven.webhook_dispatcher import WebhookDispatcherPort
from src.bot.infrastructure.logging import get_logger

logger = get_logger(__name__)


class HttpWebhookDispatcher(WebhookDispatcherPort):
    def __init__(self, webhook_url: str, timeout_seconds: int = 8) -> None:
        self._webhook_url = webhook_url
        self._timeout_seconds = timeout_seconds

    async def dispatch(
        self,
        event_type: str,
        event_id: str,
        payload: dict[str, Any],
    ) -> None:
        if not self._webhook_url:
            logger.warning(
                "SELLER_PORTAL_WEBHOOK_URL missing; skipping dispatch event_id=%s",
                event_id,
            )
            return

        body = {
            "event_type": event_type,
            "event_id": event_id,
            **payload,
        }

        headers = {
            "Content-Type": "application/json",
            "X-Event-Id": event_id,
        }

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(self._webhook_url, json=body, headers=headers)
            response.raise_for_status()

        logger.info("Webhook dispatched event_type=%s event_id=%s", event_type, event_id)
