from typing import Any, Optional

from pydantic import BaseModel, Field


class PartRequest(BaseModel):
    item_id: Optional[str] = None
    part_number: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[int] = 1
    notes: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
