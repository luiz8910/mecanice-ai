from pydantic import BaseModel
from typing import Optional


class PartRequest(BaseModel):
    part_number: Optional[str]
    description: Optional[str]
    quantity: Optional[int] = 1
