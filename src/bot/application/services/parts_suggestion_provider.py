"""Suggestion provider boundary for browser-first quotation threads."""

from __future__ import annotations

from typing import Any

from src.bot.adapters.driven.llm.llm_recommendation_adapter import (
    LlmError,
)
from src.bot.application.dtos.recommendation.part_request import PartRequest
from src.bot.application.dtos.recommendation.recommendation_request import (
    RecommendationRequest,
)
from src.bot.application.ports.driven.llm_recommendation_port import (
    LlmRecommendationPort,
)


class PartsSuggestionProvider:
    async def suggest(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError


class LlmPartsSuggestionProvider(PartsSuggestionProvider):
    def __init__(self, recommender: LlmRecommendationPort) -> None:
        self._recommender = recommender

    async def suggest(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        request = RecommendationRequest(
            requester_id=str(payload["request_id"]),
            vehicle=payload.get("vehicle") or None,
            parts=[
                PartRequest(
                    item_id=str(payload.get("requested_item_id") or ""),
                    part_number=payload.get("part_number"),
                    description=payload.get("original_description"),
                    quantity=payload.get("requested_items_count") or 1,
                    notes=payload.get("notes"),
                )
            ],
            context={
                "thread_id": str(payload["thread_id"]),
                "original_description": payload.get("original_description") or "",
                "raw_candidates": payload.get("raw_candidates") or [],
                "raw_candidates_by_item": payload.get("raw_candidates_by_item") or {},
                "requested_item_id": payload.get("requested_item_id"),
                "amperage": payload.get("amperage"),
                "connector": payload.get("connector"),
                "pulley": payload.get("pulley"),
                "photo": payload.get("photo"),
            },
        )

        response = await self._recommender.generate(request)

        suggestions: list[dict[str, Any]] = []
        for item_result in response.items:
            for candidate in item_result.accepted_candidates:
                metadata = candidate.metadata or {}
                suggestions.append(
                    {
                        "title": metadata.get("title")
                        or metadata.get("description")
                        or candidate.part_number
                        or payload.get("part_number")
                        or "Suggested part",
                        "brand": candidate.brand,
                        "part_number": candidate.part_number,
                        "confidence": candidate.score,
                        "note": item_result.summary,
                        "metadata_json": {
                            "average_price_brl": candidate.average_price_brl,
                            "candidate_id": candidate.id,
                            "requested_item_type": item_result.requested_item_type,
                            "needs_more_info": item_result.needs_more_info,
                            "required_missing_fields": item_result.required_missing_fields,
                            "rejected_candidates": [
                                rejected.model_dump() for rejected in item_result.rejected_candidates
                            ],
                            **metadata,
                        },
                    }
                )
        return suggestions


__all__ = ["LlmError", "PartsSuggestionProvider", "LlmPartsSuggestionProvider"]
