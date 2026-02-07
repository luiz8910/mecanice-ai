from __future__ import annotations

from pydantic import BaseModel

from .types import ConfirmType


class Confirmation(BaseModel):
    type: ConfirmType
    prompt: str
