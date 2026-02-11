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
from src.bot.application.useCases.fanout_quote_requests import (
    FanoutQuoteRequestsUseCase,
)
from src.bot.infrastructure.config.settings import settings


@lru_cache(maxsize=1)
def _llm_adapter() -> OpenAiRecommendationAdapter:
    return OpenAiRecommendationAdapter(settings)


def get_fanout_use_case() -> FanoutQuoteRequestsUseCase:
    return FanoutQuoteRequestsUseCase(llm=_llm_adapter())
