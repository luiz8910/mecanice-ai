from __future__ import annotations

from typing import Protocol


class VehiclePlateLookupPort(Protocol):
    async def lookup(self, plate: str) -> dict[str, str] | None:
        """Return minimal vehicle details for a normalized plate (ABC1234)."""
        ...
