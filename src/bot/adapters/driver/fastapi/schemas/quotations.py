from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


QuotationStatus = Literal["NEW", "IN_PROGRESS", "OFFERED", "CONFIRMED", "CLOSED"]


class QuotationCreateSchema(BaseModel):
    code: str = Field(..., min_length=1, description="Human-readable code, e.g. REQ-2024-001")
    seller_id: int = Field(..., gt=0, description="Vendor (seller) ID")
    workshop_id: int = Field(..., gt=0, description="Workshop ID")
    part_number: str = Field(..., min_length=1)
    part_description: str = Field(..., min_length=1)
    vehicle_info: str | None = None
    status: QuotationStatus = "NEW"
    is_urgent: bool = False
    offer_submitted: bool = False
    original_message: str | None = None
    notes: str | None = None


class QuotationUpdateSchema(BaseModel):
    part_number: str | None = Field(default=None, min_length=1)
    part_description: str | None = Field(default=None, min_length=1)
    vehicle_info: str | None = None
    status: QuotationStatus | None = None
    is_urgent: bool | None = None
    offer_submitted: bool | None = None
    notes: str | None = None


class QuotationResponseSchema(BaseModel):
    id: int
    code: str
    seller_id: int
    seller_name: str
    workshop_id: int
    workshop_name: str
    part_number: str
    part_description: str
    vehicle_info: str | None = None
    status: str
    is_urgent: bool
    offer_submitted: bool
    original_message: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
