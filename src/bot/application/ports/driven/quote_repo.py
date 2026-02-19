from __future__ import annotations

from typing import Protocol, List, Optional
from ....domain.model.quote import Quote


class QuoteRepoPort(Protocol):
    def add(self, quote: Quote) -> None:
        ...

    def get(self, id: str) -> Optional[Quote]:
        ...

    def list(self) -> List[Quote]:
        ...

    def remove(self, id: str) -> None:
        ...
