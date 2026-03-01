from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MechanicQuoteRequestDTO(BaseModel):
    request_id: str
    conversation_id: str | None = None
    mechanic_phone_e164: str
    workshop_id: int | None = None
    store_id: str | None = None
    store_name: str | None = None
    vendor_id: str | None = None
    vendor_name: str | None = None
    part_number: str | None = None
    vehicle_plate: str | None = None
    vehicle: dict[str, str] | None = None
    vehicle_info: str | None = None
    notes: str | None = None
    event_id: str
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class VendorQuoteOfferDTO(BaseModel):
    conversation_id: str
    request_id: str
    mechanic_phone_e164: str | None = None
    store_id: str
    vendor_id: str
    store_name: str | None = None
    price: float
    currency: str = "BRL"
    brand: str | None = None
    availability: str | None = None
    delivery: str | None = None
    vehicle_plate: str | None = None
    vehicle: dict[str, str] | None = None
    vehicle_info: str | None = None
    notes: str | None = None
    idempotency_key: str | None = None
