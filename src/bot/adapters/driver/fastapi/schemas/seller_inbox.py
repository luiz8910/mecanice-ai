"""Schemas for the seller inbox read model backed by browser-first threads."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.bot.adapters.driver.fastapi.schemas.threads import (
    OfferResponseSchema,
    SuggestedPartResponseSchema,
    ThreadMessageResponseSchema,
)


InboxStatus = str


class InboxItemSchema(BaseModel):
    inbox_item_id: str
    request_id: str
    store_id: str
    vendor_id: str
    status: InboxStatus
    created_at: datetime
    last_updated_at: datetime
    workshop_name: str | None = None
    part_number: str | None = None
    part_description: str | None = None
    vehicle_summary: str | None = None
    has_offer: bool | None = None


class InboxListResponseSchema(BaseModel):
    items: list[InboxItemSchema]
    page: int
    page_size: int
    total: int


class WorkshopInfoSchema(BaseModel):
    workshop_id: int
    name: str
    phone: str | None = None
    address: str | None = None


class InboxItemDetailSchema(BaseModel):
    inbox_item_id: str
    request_id: str
    store_id: str
    vendor_id: str
    status: InboxStatus
    created_at: datetime
    last_updated_at: datetime
    workshop: WorkshopInfoSchema | None = None
    part_number: str | None = None
    part_description: str | None = None
    vehicle_summary: str | None = None
    original_message: str | None = None
    notes: str | None = None
    messages: list[ThreadMessageResponseSchema] = Field(default_factory=list)
    suggestions: list[SuggestedPartResponseSchema] = Field(default_factory=list)
    current_offer: OfferResponseSchema | None = None


class InboxItemUpdateSchema(BaseModel):
    status: str
