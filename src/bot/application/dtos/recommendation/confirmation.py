from pydantic import BaseModel
from typing import Optional


class Confirmation(BaseModel):
    confirmed: bool
    reason: Optional[str] = None
