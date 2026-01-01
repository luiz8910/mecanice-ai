from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


SourceType = Literal["catalog", "manual", "user_image", "unknown"]
ConfirmType = Literal["question", "photo", "measurement"]
AxleType = Literal["front", "rear", "unknown"]


class Evidence(BaseModel):
    source_type: SourceType
    source_id: Optional[str] = None
    snippet: str


class Confirmation(BaseModel):
    type: ConfirmType
    prompt: str


class Candidate(BaseModel):
    label: str
    name: str
    part_numbers: List[str] = Field(default_factory=list)
    brand: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: List[Evidence] = Field(default_factory=list)
    what_to_confirm: List[Confirmation] = Field(default_factory=list)
    risk_notes: Optional[str] = None


class InputSummary(BaseModel):
    raw_text: str
    has_images: bool
    detected_intent: Literal["identify_part"]


class VehicleGuess(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    variant_notes: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    missing_fields: List[str] = Field(default_factory=list)


class PartRequest(BaseModel):
    part_type: str
    axle: AxleType
    symptoms_or_context: Optional[str] = None


class NextQuestion(BaseModel):
    ask: bool
    type: ConfirmType
    prompt: str
    reason: str


class Safety(BaseModel):
    no_owner_data: bool = True
    no_guessing_part_numbers: bool = True
    disclaimer_short: str


class RecommendationResponse(BaseModel):
    request_id: str
    language: Literal["pt-BR"]
    input_summary: InputSummary
    vehicle_guess: VehicleGuess
    part_request: PartRequest
    candidates: List[Candidate] = Field(default_factory=list)
    next_question: NextQuestion
    safety: Safety


# ---- Request DTOs ----

class KnownFields(BaseModel):
    axle: AxleType = "unknown"
    rear_brake_type: Literal["disc", "drum", "unknown"] = "unknown"
    engine: str = "unknown"
    abs: Literal["yes", "no", "unknown"] = "unknown"


class ContextSource(BaseModel):
    source_id: str
    source_type: SourceType = "catalog"
    text: str


class RecommendationRequest(BaseModel):
    request_id: str
    user_text: str
    images_base64: List[str] = Field(default_factory=list)
    known_fields: KnownFields = Field(default_factory=KnownFields)
    context_sources: List[ContextSource] = Field(default_factory=list)
