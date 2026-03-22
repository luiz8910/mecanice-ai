from typing import List, Optional

from pydantic import BaseModel, Field

from .candidate import Candidate
from .evidence import Evidence
from .recommendation_item_result import RecommendationItemResult


class RecommendationResponse(BaseModel):
    id: Optional[str]
    requested_item_type: Optional[str] = None
    needs_more_info: bool = False
    required_missing_fields: list[str] = Field(default_factory=list)
    candidates: List[Candidate] = Field(default_factory=list)
    accepted_candidates: List[Candidate] = Field(default_factory=list)
    rejected_candidates: List[Candidate] = Field(default_factory=list)
    items: List[RecommendationItemResult] = Field(default_factory=list)
    evidences: Optional[List[Evidence]] = None
    raw: dict = Field(default_factory=dict)
