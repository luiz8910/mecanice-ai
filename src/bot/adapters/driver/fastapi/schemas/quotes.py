"""Request / response schemas for the quotes endpoint.

These are the wire-format models exposed by the REST API.  They map
to / from the application-layer DTOs inside the router.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PartRequestSchema(BaseModel):
    part_number: Optional[str] = None
    description: Optional[str] = None
    quantity: int = 1


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
    context: Optional[Dict[str, str]] = Field(
        None, description="Contexto adicional livre"
    )


class CandidateSchema(BaseModel):
    id: Optional[str] = None
    part_number: Optional[str] = None
    brand: Optional[str] = None
    average_price_brl: Optional[float] = None
    score: Optional[float] = None
    metadata: Optional[dict] = None


class EvidenceSchema(BaseModel):
    id: Optional[str] = None
    score: Optional[float] = None
    text: Optional[str] = None


class QuoteResponseSchema(BaseModel):
    """Body returned by ``POST /quotes/recommendation``."""

    id: Optional[str] = None
    candidates: Optional[List[CandidateSchema]] = None
    evidences: Optional[List[EvidenceSchema]] = None
    raw: Optional[dict] = None
