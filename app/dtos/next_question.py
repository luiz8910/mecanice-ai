from __future__ import annotations

from pydantic import BaseModel

from .types import ConfirmType


class NextQuestion(BaseModel):
    ask: bool
    type: ConfirmType
    prompt: str
    reason: str
