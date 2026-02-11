from __future__ import annotations

from typing import Protocol


class GeoDistancePort(Protocol):
    def distance_meters(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Return approximate distance in meters between two lat/lon points."""
        ...
