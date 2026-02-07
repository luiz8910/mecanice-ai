from __future__ import annotations

from pydantic import BaseModel

from .types import SourceType


class ContextSource(BaseModel):
    source_id: str
    source_type: SourceType = "catalog"
    text: str
