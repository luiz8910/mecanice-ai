from pydantic import BaseModel
from typing import Optional, List
from .candidate import Candidate
from .evidence import Evidence


class RecommendationResponse(BaseModel):
    id: Optional[str]
    candidates: Optional[List[Candidate]] = None
    evidences: Optional[List[Evidence]] = None
    raw: Optional[dict] = None
