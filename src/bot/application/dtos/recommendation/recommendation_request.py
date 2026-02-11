from pydantic import BaseModel
from typing import Optional, List
from .part_request import PartRequest


class RecommendationRequest(BaseModel):
    requester_id: Optional[str]
    vehicle: Optional[dict]
    parts: Optional[List[PartRequest]] = None
    context: Optional[dict] = None
