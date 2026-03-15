"""WhatsApp adapter that sends via Meta API and mirrors outbound messages to test sink."""

from __future__ import annotations

from src.bot.adapters.driven.whatsapp.meta_cloud_api_client import MetaCloudApiClient
from src.bot.adapters.driven.whatsapp.test_message_sink import record_outbound_message
from src.bot.application.dtos.messaging import IncomingMessageDTO, OutgoingMessageDTO
from src.bot.application.ports.driven.messaging import MessagingPort
from src.bot.infrastructure.config.settings import Settings


class ObservableWhatsAppClient(MessagingPort):
    def __init__(self, settings: Settings) -> None:
        self._delegate = MetaCloudApiClient(settings)

    def send(self, message: OutgoingMessageDTO) -> None:
        # Mirror first so local test UIs can observe outbound traffic even if
        # provider credentials are missing in dev.
        record_outbound_message(message)
        self._delegate.send(message)

    def receive(self) -> IncomingMessageDTO:
        return self._delegate.receive()
