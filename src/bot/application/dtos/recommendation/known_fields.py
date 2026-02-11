from pydantic import BaseModel
from typing import Optional, Dict


class KnownFields(BaseModel):
    fields: Optional[Dict[str, str]] = None
