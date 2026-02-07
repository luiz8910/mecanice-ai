from __future__ import annotations

from typing import Literal
from pydantic import BaseModel

from .types import AxleType


class KnownFields(BaseModel):
    axle: AxleType = "unknown"
    rear_brake_type: Literal["disc", "drum", "unknown"] = "unknown"
    engine: str = "unknown"
    abs: Literal["yes", "no", "unknown"] = "unknown"
