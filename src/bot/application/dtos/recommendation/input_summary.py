from pydantic import BaseModel
from typing import Optional, Dict


class InputSummary(BaseModel):
    text: Optional[str]
    fields: Optional[Dict[str, str]] = None
