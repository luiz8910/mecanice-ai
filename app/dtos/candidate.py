from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

from .evidence import Evidence
from .confirmation import Confirmation


class Candidate(BaseModel):
    label: str
    name: str
    part_numbers: List[str] = Field(default_factory=list)
    brand: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: List[Evidence] = Field(default_factory=list)
    what_to_confirm: List[Confirmation] = Field(default_factory=list)
    risk_notes: Optional[str] = None
