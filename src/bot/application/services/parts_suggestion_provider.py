"""Suggestion provider boundary for browser-first quotation threads."""

from __future__ import annotations

from typing import Any

from src.bot.adapters.driven.llm.llm_recommendation_adapter import (
    LlmError,
    OpenAiRecommendationAdapter,
)
from src.bot.application.dtos.recommendation.part_request import PartRequest
from src.bot.application.dtos.recommendation.recommendation_request import (
    RecommendationRequest,
)


class PartsSuggestionProvider:
    async def suggest(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError


class LlmPartsSuggestionProvider(PartsSuggestionProvider):
    def __init__(self, adapter: OpenAiRecommendationAdapter) -> None:
        self._adapter = adapter

    async def suggest(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        request = RecommendationRequest(
            requester_id=str(payload["request_id"]),
            vehicle=payload.get("vehicle") or None,
            parts=[
                PartRequest(
                    part_number=payload.get("part_number"),
                    description=payload.get("original_description"),
                    quantity=payload.get("requested_items_count") or 1,
                )
            ],
            context={
                "thread_id": str(payload["thread_id"]),
                "original_description": payload.get("original_description") or "",
            },
        )

        response = await self._adapter.generate(request)

        suggestions: list[dict[str, Any]] = []
        for candidate in response.candidates or []:
            metadata = candidate.metadata or {}
            suggestions.append(
                {
                    "title": metadata.get("title")
                    or candidate.part_number
                    or payload.get("part_number")
                    or "Suggested part",
                    "brand": candidate.brand,
                    "part_number": candidate.part_number,
                    "confidence": candidate.score,
                    "note": metadata.get("note"),
                    "metadata_json": {
                        "average_price_brl": candidate.average_price_brl,
                        "candidate_id": candidate.id,
                        **metadata,
                    },
                }
            )
        return suggestions


__all__ = ["LlmError", "PartsSuggestionProvider", "LlmPartsSuggestionProvider"]
