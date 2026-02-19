from __future__ import annotations

from typing import Protocol, List, Optional
from ....domain.model.solicitation import Solicitation


class SolicitationRepoPort(Protocol):
    def add(self, solicitation: Solicitation) -> None:
        ...

    def get(self, id: str) -> Optional[Solicitation]:
        ...

    def list(self) -> List[Solicitation]:
        ...

    def remove(self, id: str) -> None:
        ...
