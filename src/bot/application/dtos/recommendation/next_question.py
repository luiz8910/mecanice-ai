from pydantic import BaseModel
from typing import Optional


class NextQuestion(BaseModel):
    question: Optional[str]
    field: Optional[str]
