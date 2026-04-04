"""Dependency-injection wiring for FastAPI use-case dependencies.

This module creates the concrete adapters and injects them into
application-layer use cases, keeping the router free of infrastructure
concerns.
"""

from __future__ import annotations

from functools import lru_cache

from src.bot.adapters.driven.llm.llm_recommendation_adapter import (
    OpenAiRecommendationAdapter,
)
from src.bot.adapters.driven.webhooks.http_webhook_dispatcher import (
    HttpWebhookDispatcher,
)
from src.bot.adapters.driven.whatsapp.observable_whatsapp_client import (
    ObservableWhatsAppClient,
)
from src.bot.adapters.driven.vehicle.brasilapi_plate_lookup import (
    BrasilApiVehiclePlateLookup,
)
from src.bot.application.useCases.fanout_quote_requests import (
    FanoutQuoteRequestsUseCase,
)
from src.bot.application.useCases.submit_vendor_offer_and_notify_mechanic import (
    SubmitVendorOfferAndNotifyMechanicUseCase,
)
from src.bot.application.services.idempotency_registry import (
    InMemoryIdempotencyRegistry,
)
from src.bot.application.services.parts_suggestion_provider import (
    LlmPartsSuggestionProvider,
    PartsSuggestionProvider,
)
from src.bot.application.services.vehicle_plate_resolver import VehiclePlateResolver
from src.bot.infrastructure.config.settings import settings


@lru_cache(maxsize=1)
def _llm_adapter() -> OpenAiRecommendationAdapter:
    return OpenAiRecommendationAdapter(settings)


@lru_cache(maxsize=1)
def _webhook_dispatcher() -> HttpWebhookDispatcher:
    return HttpWebhookDispatcher(
        webhook_url=settings.SELLER_PORTAL_WEBHOOK_URL,
        timeout_seconds=settings.SELLER_PORTAL_WEBHOOK_TIMEOUT_SECONDS,
    )


@lru_cache(maxsize=1)
def _whatsapp_client() -> ObservableWhatsAppClient:
    return ObservableWhatsAppClient(settings)


@lru_cache(maxsize=1)
def _vehicle_plate_lookup() -> BrasilApiVehiclePlateLookup:
    return BrasilApiVehiclePlateLookup(settings)


@lru_cache(maxsize=1)
def _vehicle_plate_resolver() -> VehiclePlateResolver:
    return VehiclePlateResolver(_vehicle_plate_lookup())


@lru_cache(maxsize=1)
def _vendor_offer_idempotency_registry() -> InMemoryIdempotencyRegistry:
    return InMemoryIdempotencyRegistry()


def get_fanout_use_case() -> FanoutQuoteRequestsUseCase:
    return FanoutQuoteRequestsUseCase(llm=_llm_adapter())


def get_submit_vendor_offer_use_case() -> SubmitVendorOfferAndNotifyMechanicUseCase:
    return SubmitVendorOfferAndNotifyMechanicUseCase(
        messaging=_whatsapp_client(),
        idempotency_registry=_vendor_offer_idempotency_registry(),
    )


def get_parts_suggestion_provider() -> PartsSuggestionProvider:
    return LlmPartsSuggestionProvider(adapter=_llm_adapter())


def get_webhook_dispatcher() -> HttpWebhookDispatcher:
    return _webhook_dispatcher()


def get_vehicle_plate_resolver() -> VehiclePlateResolver:
    return _vehicle_plate_resolver()
