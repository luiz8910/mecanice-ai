from pydantic import BaseModel
from typing import Optional


class ContextSource(BaseModel):
    source_id: Optional[str]
    source_type: Optional[str]
    excerpt: Optional[str]
