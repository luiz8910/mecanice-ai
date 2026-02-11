from __future__ import annotations

from typing import Protocol

from src.bot.application.dtos.recommendation.recommendation_request import (
    RecommendationRequest,
)
from src.bot.application.dtos.recommendation.recommendation_response import (
    RecommendationResponse,
)


class LlmRecommendationPort(Protocol):
    async def generate(
        self, request: RecommendationRequest
    ) -> RecommendationResponse:
        """Generate a recommendation response from an LLM or model service."""
        ...
