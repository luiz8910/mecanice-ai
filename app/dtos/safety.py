from __future__ import annotations

from pydantic import BaseModel


class Safety(BaseModel):
    no_owner_data: bool = True
    no_guessing_part_numbers: bool = True
    disclaimer_short: str
