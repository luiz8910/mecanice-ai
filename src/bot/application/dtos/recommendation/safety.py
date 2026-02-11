from pydantic import BaseModel
from typing import Optional


class Safety(BaseModel):
    safe: bool = True
    reason: Optional[str] = None
