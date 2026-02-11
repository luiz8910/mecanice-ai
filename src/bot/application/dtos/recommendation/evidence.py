from pydantic import BaseModel
from typing import Optional


class Evidence(BaseModel):
    id: Optional[str]
    score: Optional[float]
    text: Optional[str]
