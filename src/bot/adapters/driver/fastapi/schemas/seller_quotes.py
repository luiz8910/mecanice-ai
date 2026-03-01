from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class VendorOfferSubmissionSchema(BaseModel):
    conversation_id: str = Field(..., description="Conversation ID sent in quote assignment webhook")
    request_id: str = Field(..., description="QuoteRequest ID")
    mechanic_phone_e164: Optional[str] = Field(default=None, description="Mechanic WhatsApp phone")
    store_id: str
    vendor_id: str
    store_name: Optional[str] = None
    price: float = Field(..., ge=0)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    brand: Optional[str] = None
    availability: Optional[str] = None
    delivery: Optional[str] = None
    vehicle_plate: Optional[str] = None
    vehicle: Optional[dict[str, str]] = None
    vehicle_info: Optional[str] = None
    notes: Optional[str] = None
