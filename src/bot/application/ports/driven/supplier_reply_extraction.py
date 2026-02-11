from __future__ import annotations

from typing import Protocol


class SupplierReplyExtractionPort(Protocol):
    def extract_text(self, raw: str) -> str:
        """Extract meaningful payload from a supplier reply (eg. parse prices)."""
        ...
