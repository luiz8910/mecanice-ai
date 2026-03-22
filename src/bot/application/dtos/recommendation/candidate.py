from typing import Optional

from pydantic import BaseModel, Field


class Candidate(BaseModel):
    id: Optional[str] = None
    part_number: Optional[str] = None
    brand: Optional[str] = None
    average_price_brl: Optional[float] = None
    score: Optional[float] = None
    metadata: dict = Field(default_factory=dict)
    compatibility_status: Optional[str] = None
    reason: Optional[str] = None
