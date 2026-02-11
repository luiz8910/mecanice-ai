from __future__ import annotations

from typing import Protocol, List, Optional
from ...domain.model.supplier import Supplier


class SupplierRepoPort(Protocol):
    def add(self, supplier: Supplier) -> None:
        ...

    def get(self, id: str) -> Optional[Supplier]:
        ...

    def list(self) -> List[Supplier]:
        ...

    def remove(self, id: str) -> None:
        ...
