from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class VendorCreateSchema(BaseModel):
    autopart_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1)
    email: str | None = None
    active: bool = True


class VendorUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    email: str | None = None
    active: bool | None = None


class VendorResponseSchema(BaseModel):
    id: int
    autopart_id: int
    name: str
    email: str | None = None
    active: bool
    served_workshops_count: int
    quotes_received_count: int
    sales_converted_count: int
    metrics_updated_at: datetime
    created_at: datetime
    updated_at: datetime


class VendorAssignmentCreateSchema(BaseModel):
    workshop_id: int = Field(..., gt=0)
    autopart_id: int = Field(..., gt=0)
    vendor_id: int = Field(..., gt=0)


class VendorAssignmentResponseSchema(BaseModel):
    id: int
    workshop_id: int
    workshop_name: str
    autopart_id: int
    autopart_name: str
    vendor_id: int
    vendor_name: str
    created_at: datetime
    updated_at: datetime


class VendorMetricEventResponseSchema(BaseModel):
    id: int
    vendor_id: int
    autopart_id: int
    workshop_id: int | None = None
    conversation_id: str | None = None
    request_id: str | None = None
    event_type: str
    event_ts: datetime
    metadata: dict[str, Any]
