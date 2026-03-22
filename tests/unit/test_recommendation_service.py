from __future__ import annotations

import asyncio

from src.bot.application.dtos.recommendation.candidate import Candidate
from src.bot.application.dtos.recommendation.part_request import PartRequest
from src.bot.application.dtos.recommendation.recommendation_request import (
    RecommendationRequest,
)
from src.bot.application.dtos.recommendation.recommendation_response import (
    RecommendationResponse,
)
from src.bot.application.services.recommendation_service import (
    FilteredRecommendationService,
    expand_requested_items,
)


class FakeLlm:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, request: RecommendationRequest) -> RecommendationResponse:
        self.calls += 1
        prefiltered_candidates = (request.context or {}).get("prefiltered_candidates") or []
        candidates = [Candidate.model_validate(candidate) for candidate in prefiltered_candidates]
        return RecommendationResponse(
            id=request.requester_id,
            requested_item_type=(request.context or {}).get("requested_item_type"),
            candidates=candidates,
            accepted_candidates=candidates,
            rejected_candidates=[],
            needs_more_info=False,
            required_missing_fields=[],
            items=[],
            evidences=[],
            raw={"source": "fake-llm"},
        )


def _run(coro):
    return asyncio.run(coro)


def test_recommendation_service_filters_wrong_category_and_incompatible_vehicle():
    llm = FakeLlm()
    service = FilteredRecommendationService(llm=llm)
    request = RecommendationRequest(
        requester_id="req-1",
        vehicle={"brand": "Fiat", "model": "Palio", "year": "2015", "engine": "1.0"},
        parts=[
            PartRequest(
                item_id="item-1",
                description="vela para palio 2015",
                quantity=4,
            )
        ],
        context={
            "original_description": "vela para palio 2015",
            "raw_candidates": [
                {
                    "id": "cand-ok",
                    "part_number": "BKR6E-11",
                    "brand": "NGK",
                    "score": 0.91,
                    "metadata": {
                        "description": "Vela de ignição NGK",
                        "compatibility_notes": "Fiat Palio 1.0 2012-2016",
                    },
                },
                {
                    "id": "cand-subaru",
                    "part_number": "SUB-999",
                    "brand": "NGK",
                    "score": 0.87,
                    "metadata": {
                        "description": "Vela de ignição",
                        "compatibility_notes": "Subaru Impreza 2025",
                    },
                },
                {
                    "id": "cand-oil",
                    "part_number": "OIL-5W30",
                    "brand": "Mobil",
                    "score": 0.95,
                    "metadata": {
                        "description": "Óleo lubrificante 5W30",
                        "compatibility_notes": "Uso geral",
                    },
                },
            ],
        },
    )

    response = _run(service.generate(request))

    assert llm.calls == 1
    assert len(response.items) == 1
    item = response.items[0]
    assert item.requested_item_type == "spark_plug"
    assert [candidate.part_number for candidate in item.accepted_candidates] == ["BKR6E-11"]
    rejection_map = {candidate.part_number: candidate.reason for candidate in item.rejected_candidates}
    assert rejection_map["SUB-999"] == "incompatible_vehicle"
    assert rejection_map["OIL-5W30"] == "wrong_category"


def test_recommendation_service_marks_alternator_as_needing_more_info():
    llm = FakeLlm()
    service = FilteredRecommendationService(llm=llm)
    request = RecommendationRequest(
        requester_id="req-2",
        vehicle={"brand": "Fiat", "model": "Palio", "year": "2015"},
        parts=[
            PartRequest(
                item_id="item-1",
                description="alternador para palio 2015",
                quantity=1,
            )
        ],
        context={
            "original_description": "alternador para palio 2015",
            "raw_candidates": [
                {
                    "id": "cand-alt",
                    "part_number": "ALT-123",
                    "brand": "Bosch",
                    "score": 0.82,
                    "metadata": {
                        "description": "Alternador Bosch",
                        "compatibility_notes": "Fiat Palio 2015",
                    },
                }
            ],
        },
    )

    response = _run(service.generate(request))

    assert llm.calls == 0
    assert response.needs_more_info is True
    assert len(response.items) == 1
    item = response.items[0]
    assert item.requested_item_type == "alternator"
    assert item.needs_more_info is True
    assert item.accepted_candidates == []
    assert "engine" in item.required_missing_fields
    assert "version" in item.required_missing_fields
    assert item.rejected_candidates[0].reason == "insufficient_vehicle_data"


def test_expand_requested_items_splits_multi_item_description():
    expanded = expand_requested_items(
        [
            {
                "description": "alternador e vela para palio 2015",
                "quantity": 1,
                "notes": None,
            }
        ],
        {"brand": "Fiat", "model": "Palio", "year": "2015"},
    )

    assert [item["description"] for item in expanded] == ["alternador", "vela de ignicao"]


def test_recommendation_service_rejects_wrong_category_before_llm():
    llm = FakeLlm()
    service = FilteredRecommendationService(llm=llm)
    request = RecommendationRequest(
        requester_id="req-3",
        vehicle={"brand": "Fiat", "model": "Palio", "year": "2015", "engine": "1.0"},
        parts=[PartRequest(item_id="item-1", description="vela", quantity=4)],
        context={
            "raw_candidates": [
                {
                    "id": "cand-filter",
                    "part_number": "AF-123",
                    "brand": "Tecfil",
                    "score": 0.7,
                    "metadata": {
                        "description": "Filtro de ar",
                        "compatibility_notes": "Fiat Palio 2015",
                    },
                }
            ]
        },
    )

    response = _run(service.generate(request))

    assert llm.calls == 0
    item = response.items[0]
    assert item.accepted_candidates == []
    assert item.rejected_candidates[0].reason == "wrong_category"


def test_recommendation_service_rejects_year_model_incompatibility():
    llm = FakeLlm()
    service = FilteredRecommendationService(llm=llm)
    request = RecommendationRequest(
        requester_id="req-4",
        vehicle={"brand": "Fiat", "model": "Palio", "year": "2015", "engine": "1.0"},
        parts=[PartRequest(item_id="item-1", description="vela de ignição", quantity=4)],
        context={
            "raw_candidates": [
                {
                    "id": "cand-year-mismatch",
                    "part_number": "SP-404",
                    "brand": "Denso",
                    "score": 0.75,
                    "metadata": {
                        "description": "Vela de ignição",
                        "compatibility_notes": "Fiat Uno 2025",
                    },
                }
            ]
        },
    )

    response = _run(service.generate(request))

    assert llm.calls == 0
    item = response.items[0]
    assert item.accepted_candidates == []
    assert item.rejected_candidates[0].reason == "incompatible_vehicle"
