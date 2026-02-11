from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Supplier:
    id: str
    name: str
    contact: Optional[str] = None
    address: Optional[str] = None

    def display_name(self) -> str:
        return f"{self.name} ({self.id})"
