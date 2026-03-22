from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .candidate import Candidate


class RecommendationItemResult(BaseModel):
    item_id: Optional[str] = None
    description: Optional[str] = None
    requested_item_type: Optional[str] = None
    vehicle: dict = Field(default_factory=dict)
    needs_more_info: bool = False
    required_missing_fields: list[str] = Field(default_factory=list)
    accepted_candidates: list[Candidate] = Field(default_factory=list)
    rejected_candidates: list[Candidate] = Field(default_factory=list)
    query: dict = Field(default_factory=dict)
    summary: Optional[str] = None
