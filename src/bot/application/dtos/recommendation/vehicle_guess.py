from pydantic import BaseModel
from typing import Optional


class VehicleGuess(BaseModel):
    make: Optional[str]
    model: Optional[str]
    year: Optional[int]
    confidence: Optional[float]
