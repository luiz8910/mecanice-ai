from pydantic import BaseModel
from typing import Optional


class Candidate(BaseModel):
    id: Optional[str] = None
    part_number: Optional[str] = None
    brand: Optional[str] = None
    average_price_brl: Optional[float] = None
    score: Optional[float] = None
    metadata: Optional[dict] = None
