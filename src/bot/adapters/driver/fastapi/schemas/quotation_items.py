"""Schemas for quotation items (peças) and events (histórico)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Quotation Items ──────────────────────────────────────────────

class QuotationItemCreateSchema(BaseModel):
    """Used when adding a manual part or an identified part."""

    part_number: str = Field(..., min_length=1, description="Código da peça")
    description: str = Field("", description="Descrição da peça")
    brand: str | None = Field(None, description="Marca (ex: Fras-le)")
    compatibility: str | None = Field(None, description="Compatibilidade (ex: Gol G5/G6)")
    price: float | None = Field(None, ge=0, description="Preço em R$")
    availability: str | None = Field("Em estoque", description="Disponibilidade")
    delivery_time: str | None = Field(None, description="Prazo de entrega (ex: 1 dia)")
    confidence_score: float | None = Field(None, ge=0, le=100, description="Score de confiança (%)")
    notes: str | None = None
    selected: bool = False


class QuotationItemUpdateSchema(BaseModel):
    """Used when setting price / availability / selecting an item."""

    description: str | None = None
    brand: str | None = None
    compatibility: str | None = None
    price: float | None = Field(None, ge=0)
    availability: str | None = None
    delivery_time: str | None = None
    confidence_score: float | None = Field(None, ge=0, le=100)
    notes: str | None = None
    selected: bool | None = None


class QuotationItemResponseSchema(BaseModel):
    id: int
    quotation_id: int
    part_number: str
    description: str
    brand: str | None = None
    compatibility: str | None = None
    price: float | None = None
    availability: str | None = None
    delivery_time: str | None = None
    confidence_score: float | None = None
    notes: str | None = None
    selected: bool
    created_at: datetime
    updated_at: datetime


# ── Quotation Events ─────────────────────────────────────────────

class QuotationEventSchema(BaseModel):
    id: int
    quotation_id: int
    event_type: str
    description: str
    created_at: datetime


# ── Submit Offer ─────────────────────────────────────────────────

class SubmitOfferResponseSchema(BaseModel):
    success: bool = True
    quotation_id: int
    status: str
    items_count: int
    total: float
