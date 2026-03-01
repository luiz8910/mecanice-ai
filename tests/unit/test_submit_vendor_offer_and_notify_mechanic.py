from src.bot.application.dtos.quote_workflow import VendorQuoteOfferDTO
from src.bot.application.services.idempotency_registry import InMemoryIdempotencyRegistry
from src.bot.application.useCases.submit_vendor_offer_and_notify_mechanic import (
    SubmitVendorOfferAndNotifyMechanicUseCase,
)


class FakeMessaging:
    def __init__(self) -> None:
        self.sent_messages = []

    def send(self, message):
        self.sent_messages.append(message)


def test_submit_offer_includes_vehicle_info_for_mechanic_confirmation():
    messaging = FakeMessaging()
    use_case = SubmitVendorOfferAndNotifyMechanicUseCase(
        messaging=messaging,
        idempotency_registry=InMemoryIdempotencyRegistry(),
    )

    delivered = use_case.execute(
        VendorQuoteOfferDTO(
            conversation_id="conv-1",
            request_id="req-1",
            mechanic_phone_e164="+5511999990000",
            store_id="1",
            vendor_id="2",
            store_name="Loja Centro",
            price=199.9,
            currency="BRL",
            vehicle={
                "plate": "BRA2E19",
                "brand": "FIAT",
                "model": "ARGO",
                "model_year": "2021",
            },
        )
    )

    assert delivered is True
    assert len(messaging.sent_messages) == 1
    text = messaging.sent_messages[0].text
    assert "Veículo:" in text
    assert "Placa: BRA2E19" in text
    assert "Marca: FIAT" in text
