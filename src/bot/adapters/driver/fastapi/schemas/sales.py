from __future__ import annotations

from pydantic import BaseModel, Field


class ConversationSaleCreateSchema(BaseModel):
    vendor_id: int = Field(..., gt=0)
    store_id: str = Field(..., min_length=1)
    request_id: str = Field(..., min_length=1)
    sale_value: float | None = Field(default=None, ge=0)
    notes: str | None = None
