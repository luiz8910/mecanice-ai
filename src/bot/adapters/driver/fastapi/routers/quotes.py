"""Quotes router — driver adapter that exposes recommendation via HTTP."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.bot.adapters.driven.llm.llm_recommendation_adapter import LlmError
from src.bot.adapters.driver.fastapi.dependencies.use_cases import (
    get_fanout_use_case,
)
from src.bot.adapters.driver.fastapi.schemas.quotes import (
    QuoteRequestSchema,
    QuoteResponseSchema,
)
from src.bot.application.dtos.recommendation.part_request import PartRequest
from src.bot.application.dtos.recommendation.recommendation_request import (
    RecommendationRequest,
)
from src.bot.application.useCases.fanout_quote_requests import (
    FanoutQuoteRequestsUseCase,
)

router = APIRouter(prefix="/quotes", tags=["quotes"])


def _to_application_dto(schema: QuoteRequestSchema) -> RecommendationRequest:
    """Map the wire schema to the application-layer DTO."""
    parts = None
    if schema.parts:
        parts = [
            PartRequest(
                part_number=p.part_number,
                description=p.description,
                quantity=p.quantity,
            )
            for p in schema.parts
        ]
    return RecommendationRequest(
        requester_id=schema.requester_id,
        vehicle=schema.vehicle,
        parts=parts,
        context=schema.context,
    )


@router.post(
    "/recommendation",
    response_model=QuoteResponseSchema,
    summary="Solicitar recomendação de peça via IA",
)
async def recommendation(
    body: QuoteRequestSchema,
    use_case: FanoutQuoteRequestsUseCase = Depends(get_fanout_use_case),
):
    """Recebe um pedido de cotação e retorna a recomendação estruturada da OpenAI."""
    request_dto = _to_application_dto(body)
    try:
        result = await use_case.execute(request_dto)
    except LlmError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return result
