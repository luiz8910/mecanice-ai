from __future__ import annotations

from typing import Optional
from pydantic import BaseModel

from .types import AxleType


class PartRequest(BaseModel):
    part_type: str
    axle: AxleType
    symptoms_or_context: Optional[str] = None
