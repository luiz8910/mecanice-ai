from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field

from .input_summary import InputSummary
from .vehicle_guess import VehicleGuess
from .part_request import PartRequest
from .candidate import Candidate
from .next_question import NextQuestion
from .safety import Safety
from .types import LanguageType


class RecommendationResponse(BaseModel):
    request_id: str
    language: LanguageType
    input_summary: InputSummary
    vehicle_guess: VehicleGuess
    part_request: PartRequest
    candidates: List[Candidate] = Field(default_factory=list)
    next_question: NextQuestion
    safety: Safety
