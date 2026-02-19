from __future__ import annotations

from typing import Protocol, List, Optional
from ....domain.model.workshop import Workshop


class WorkshopRepoPort(Protocol):
    def add(self, workshop: Workshop) -> None:
        ...

    def get(self, id: str) -> Optional[Workshop]:
        ...

    def list(self) -> List[Workshop]:
        ...

    def remove(self, id: str) -> None:
        ...
