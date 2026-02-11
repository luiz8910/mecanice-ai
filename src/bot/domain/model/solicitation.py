from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional


@dataclass
class Solicitation:
    id: str
    requester: str
    vehicle_info: Dict[str, str]
    parts: List[Dict[str, object]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    notes: Optional[str] = None

    def add_part(self, part: Dict[str, object]) -> None:
        self.parts.append(part)
