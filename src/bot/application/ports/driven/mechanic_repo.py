from __future__ import annotations

from typing import Protocol, List, Optional
from ...domain.model.mechanic import Mechanic


class MechanicRepoPort(Protocol):
    def add(self, mechanic: Mechanic) -> None:
        ...

    def get(self, id: str) -> Optional[Mechanic]:
        ...

    def list_by_workshop(self, workshop_id: str) -> List[Mechanic]:
        ...

    def remove(self, id: str) -> None:
        ...
