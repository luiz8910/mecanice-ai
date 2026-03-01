"""Schemas for the Seller Inbox API (consumed by Seller Portal front-end)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


InboxStatus = Literal["NEW", "IN_PROGRESS", "OFFERED", "CONFIRMED", "CLOSED"]


class InboxItemSchema(BaseModel):
    inbox_item_id: str = Field(..., description="ID único do item na inbox do vendedor.")
    request_id: str = Field(..., description="ID da solicitação de cotação.")
    store_id: str = Field(..., description="ID da loja à qual o vendedor pertence.")
    vendor_id: str = Field(..., description="ID do vendedor atribuído.")
    status: InboxStatus
    created_at: datetime
    last_updated_at: datetime
    workshop_name: str | None = None
    part_number: str | None = None
    part_description: str | None = None
    vehicle_summary: str | None = None
    is_urgent: bool | None = None
    has_offer: bool | None = None


class InboxListResponseSchema(BaseModel):
    items: list[InboxItemSchema]
    page: int
    page_size: int
    total: int


class WorkshopInfoSchema(BaseModel):
    """Workshop info shown in the quotation detail."""
    workshop_id: int
    name: str
    phone: str | None = None
    address: str | None = None


class QuotationItemInlineSchema(BaseModel):
    """Item (part) shown inline in the detail."""
    id: int
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


class QuotationEventInlineSchema(BaseModel):
    """History event shown inline in the detail."""
    id: int
    event_type: str
    description: str
    created_at: datetime


class InboxItemDetailSchema(BaseModel):
    """Full detail of a single inbox quotation."""

    inbox_item_id: str = Field(..., description="ID da cotação.")
    request_id: str = Field(..., description="Código da solicitação (ex: REQ-2024-006).")
    store_id: str
    vendor_id: str
    seller_name: str | None = None
    status: InboxStatus
    created_at: datetime
    last_updated_at: datetime
    workshop: WorkshopInfoSchema | None = None
    part_number: str | None = None
    part_description: str | None = None
    vehicle_summary: str | None = None
    original_message: str | None = None
    is_urgent: bool | None = None
    has_offer: bool | None = None
    notes: str | None = None
    items: list[QuotationItemInlineSchema] = []
    events: list[QuotationEventInlineSchema] = []


class InboxItemUpdateSchema(BaseModel):
    status: InboxStatus = Field(..., description="Novo status do item.")
