from __future__ import annotations

from src.bot.application.dtos.messaging import OutgoingMessageDTO
from src.bot.application.dtos.quote_workflow import VendorQuoteOfferDTO
from src.bot.application.ports.driven.messaging import MessagingPort
from src.bot.application.services.idempotency_registry import InMemoryIdempotencyRegistry
from src.bot.infrastructure.logging import get_logger

logger = get_logger(__name__)


class SubmitVendorOfferAndNotifyMechanicUseCase:
    def __init__(
        self,
        messaging: MessagingPort,
        idempotency_registry: InMemoryIdempotencyRegistry,
    ) -> None:
        self._messaging = messaging
        self._idempotency_registry = idempotency_registry

    def execute(self, offer: VendorQuoteOfferDTO) -> bool:
        if offer.idempotency_key and self._idempotency_registry.seen(offer.idempotency_key):
            logger.info(
                "Duplicate vendor offer ignored request_id=%s key=%s",
                offer.request_id,
                offer.idempotency_key,
            )
            return False

        if offer.idempotency_key:
            self._idempotency_registry.mark(offer.idempotency_key)

        store_label = offer.store_name or offer.store_id
        text = (
            f"Orçamento recebido ({offer.request_id})\n"
            f"Loja: {store_label}\n"
            f"Preço: {offer.currency} {offer.price:.2f}\n"
            f"Marca: {offer.brand or 'não informada'}\n"
            f"Disponibilidade: {offer.availability or 'não informada'}\n"
            f"Entrega: {offer.delivery or 'não informada'}"
        )
        if offer.notes:
            text += f"\nObservações: {offer.notes}"

        vehicle_info = offer.vehicle_info or self._build_vehicle_info_text(offer)
        if vehicle_info:
            text += f"\nVeículo: {vehicle_info}"

        self._messaging.send(
            OutgoingMessageDTO(
                recipient=offer.mechanic_phone_e164,
                text=text,
                metadata={
                    "conversation_id": offer.conversation_id,
                    "request_id": offer.request_id,
                    "store_id": offer.store_id,
                    "vendor_id": offer.vendor_id,
                },
            )
        )

        logger.info(
            "Mechanic notified for request_id=%s store_id=%s vendor_id=%s",
            offer.request_id,
            offer.store_id,
            offer.vendor_id,
        )
        return True

    @staticmethod
    def _build_vehicle_info_text(offer: VendorQuoteOfferDTO) -> str | None:
        if offer.vehicle:
            ordered_fields = [
                ("plate", "Placa"),
                ("brand", "Marca"),
                ("model", "Modelo"),
                ("model_year", "Ano"),
                ("color", "Cor"),
                ("city", "Cidade"),
                ("state", "UF"),
            ]
            parts = [
                f"{label}: {offer.vehicle[key]}"
                for key, label in ordered_fields
                if offer.vehicle.get(key)
            ]
            if parts:
                return " | ".join(parts)

        if offer.vehicle_plate:
            return f"Placa: {offer.vehicle_plate}"

        return None
