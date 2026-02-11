from __future__ import annotations

from typing import Protocol

from ...dtos.messaging import IncomingMessageDTO, OutgoingMessageDTO


class MessagingPort(Protocol):
    def send(self, message: OutgoingMessageDTO) -> None:
        ...

    def receive(self) -> IncomingMessageDTO:
        ...
