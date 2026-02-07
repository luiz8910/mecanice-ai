from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class VehicleGuess(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    variant_notes: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    missing_fields: List[str] = Field(default_factory=list)
