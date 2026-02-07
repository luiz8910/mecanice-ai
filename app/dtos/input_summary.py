from __future__ import annotations

from typing import Literal
from pydantic import BaseModel


class InputSummary(BaseModel):
    raw_text: str
    has_images: bool
    detected_intent: Literal["identify_part"]
