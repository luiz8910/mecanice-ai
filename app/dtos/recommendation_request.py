from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field

from .known_fields import KnownFields
from .context_source import ContextSource


class RecommendationRequest(BaseModel):
    request_id: str
    user_text: str
    images_base64: List[str] = Field(default_factory=list)
    known_fields: KnownFields = Field(default_factory=KnownFields)
    context_sources: List[ContextSource] = Field(default_factory=list)
