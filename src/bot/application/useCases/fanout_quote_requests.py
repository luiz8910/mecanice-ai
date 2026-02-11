"""Use case: Fan-out a quote request to the LLM and return a recommendation.

Application layer — orchestrates the port call without knowing HTTP,
OpenAI, or any infrastructure detail.
"""

from __future__ import annotations

from src.bot.application.dtos.recommendation.recommendation_request import (
    RecommendationRequest,
)
from src.bot.application.dtos.recommendation.recommendation_response import (
    RecommendationResponse,
)
from src.bot.application.ports.driven.llm_recommendation_port import (
    LlmRecommendationPort,
)
from src.bot.infrastructure.logging import get_logger

logger = get_logger(__name__)


class FanoutQuoteRequestsUseCase:
    """Sends a part/quote request to the LLM and returns the structured result.

    In future iterations this use case will also broadcast the request
    to multiple supplier stores; for now it focuses on the LLM analysis step.
    """

    def __init__(self, llm: LlmRecommendationPort) -> None:
        self._llm = llm

    async def execute(
        self, request: RecommendationRequest
    ) -> RecommendationResponse:
        logger.info(
            "FanoutQuoteRequests  requester=%s  parts=%s",
            request.requester_id,
            [p.part_number for p in (request.parts or [])],
        )

        response = await self._llm.generate(request)

        logger.info(
            "LLM returned %d candidate(s)",
            len(response.candidates) if response.candidates else 0,
        )
        return response
