from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ServiceOrderListItemSchema(BaseModel):
    id: str
    thread_id: int
    offer_id: int
    status: str
    title: str
    workshop_name: str | None = None
    vehicle_summary: str | None = None
    total_amount: float
    item_count: int
    created_at: datetime
    submitted_at: datetime
    auto_parts_name: str | None = None
    seller_name: str | None = None


class ServiceOrderAutoPartsSchema(BaseModel):
    name: str | None = None
    phone: str | None = None
    address: str | None = None


class ServiceOrderSellerSchema(BaseModel):
    name: str | None = None
    phone: str | None = None


class ServiceOrderItemSchema(BaseModel):
    id: str
    requested_item_id: int | None = None
    requested_item_label: str | None = None
    description: str
    brand: str | None = None
    part_number: str | None = None
    quantity: int
    unit_price: float | None = None
    line_total: float
    notes: str | None = None


class ServiceOrderDetailSchema(BaseModel):
    id: str
    thread_id: int
    offer_id: int
    status: str
    title: str
    created_at: datetime
    submitted_at: datetime
    workshop_name: str | None = None
    vehicle_summary: str | None = None
    request_notes: str | None = None
    auto_parts: ServiceOrderAutoPartsSchema
    seller: ServiceOrderSellerSchema
    items: list[ServiceOrderItemSchema] = Field(default_factory=list)
    total_amount: float
