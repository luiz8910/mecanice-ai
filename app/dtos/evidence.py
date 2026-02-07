from __future__ import annotations

from typing import Optional
from pydantic import BaseModel

from .types import SourceType


class Evidence(BaseModel):
    source_type: SourceType
    source_id: Optional[str] = None
    snippet: str
