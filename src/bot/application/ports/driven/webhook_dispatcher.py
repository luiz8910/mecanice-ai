from __future__ import annotations

from typing import Any, Protocol


class WebhookDispatcherPort(Protocol):
    async def dispatch(
        self,
        event_type: str,
        event_id: str,
        payload: dict[str, Any],
    ) -> None:
        ...
