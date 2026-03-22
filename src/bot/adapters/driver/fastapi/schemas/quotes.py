"""Request / response schemas for the quotes endpoint.

These are the wire-format models exposed by the REST API.  They map
to / from the application-layer DTOs inside the router.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PartRequestSchema(BaseModel):
    item_id: Optional[str] = None
    part_number: Optional[str] = None
    description: Optional[str] = None
    quantity: int = 1
    notes: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class QuoteRequestSchema(BaseModel):
    """Body accepted by ``POST /quotes/recommendation``."""

    requester_id: Optional[str] = Field(
        None, description="ID do mecânico ou solicitante"
    )
    vehicle: Optional[Dict[str, str]] = Field(
        None,
        description="Informações do veículo (make, model, year, engine …)",
        examples=[{"make": "Chevrolet", "model": "Vectra", "year": "2000"}],
    )
    parts: Optional[List[PartRequestSchema]] = Field(
        None, description="Lista de peças solicitadas"
    )
    context: Optional[Dict[str, Any]] = Field(
        None, description="Contexto adicional livre"
    )


class CandidateSchema(BaseModel):
    id: Optional[str] = None
    part_number: Optional[str] = None
    brand: Optional[str] = None
    average_price_brl: Optional[float] = None
    score: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    compatibility_status: Optional[str] = None
    reason: Optional[str] = None


class RecommendationItemResultSchema(BaseModel):
    item_id: Optional[str] = None
    description: Optional[str] = None
    requested_item_type: Optional[str] = None
    vehicle: dict[str, Any] = Field(default_factory=dict)
    needs_more_info: bool = False
    required_missing_fields: list[str] = Field(default_factory=list)
    accepted_candidates: list[CandidateSchema] = Field(default_factory=list)
    rejected_candidates: list[CandidateSchema] = Field(default_factory=list)
    query: dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None


class EvidenceSchema(BaseModel):
    id: Optional[str] = None
    score: Optional[float] = None
    text: Optional[str] = None


class QuoteResponseSchema(BaseModel):
    """Body returned by ``POST /quotes/recommendation``."""

    id: Optional[str] = None
    requested_item_type: Optional[str] = None
    needs_more_info: bool = False
    required_missing_fields: list[str] = Field(default_factory=list)
    candidates: list[CandidateSchema] = Field(default_factory=list)
    accepted_candidates: list[CandidateSchema] = Field(default_factory=list)
    rejected_candidates: list[CandidateSchema] = Field(default_factory=list)
    items: list[RecommendationItemResultSchema] = Field(default_factory=list)
    evidences: Optional[List[EvidenceSchema]] = None
    raw: dict[str, Any] = Field(default_factory=dict)
