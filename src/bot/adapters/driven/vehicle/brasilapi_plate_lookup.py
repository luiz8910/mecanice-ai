from __future__ import annotations

import httpx

from src.bot.application.ports.driven.vehicle_plate_lookup import VehiclePlateLookupPort
from src.bot.infrastructure.config.settings import Settings
from src.bot.infrastructure.logging import get_logger

logger = get_logger(__name__)


class BrasilApiVehiclePlateLookup(VehiclePlateLookupPort):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def lookup(self, plate: str) -> dict[str, str] | None:
        base_url = self._settings.PLATE_LOOKUP_BASE_URL.strip().rstrip("/")
        if not base_url:
            return None

        headers: dict[str, str] = {"Accept": "application/json"}
        api_key = self._settings.PLATE_LOOKUP_API_KEY.strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        url = f"{base_url}/{plate}"

        try:
            async with httpx.AsyncClient(
                timeout=self._settings.PLATE_LOOKUP_TIMEOUT_SECONDS
            ) as client:
                response = await client.get(url, headers=headers)
        except httpx.HTTPError:
            logger.exception("Plate lookup request failed plate=%s", plate)
            return None

        if response.status_code == 404:
            return None

        try:
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            logger.exception("Plate lookup parse failed plate=%s", plate)
            return None

        details: dict[str, str] = {
            "plate": plate,
            "brand": str(payload.get("marca") or "").strip(),
            "model": str(payload.get("modelo") or "").strip(),
            "model_year": str(payload.get("ano") or "").strip(),
            "color": str(payload.get("cor") or "").strip(),
            "city": str(payload.get("municipio") or payload.get("cidade") or "").strip(),
            "state": str(payload.get("uf") or "").strip(),
        }

        return {key: value for key, value in details.items() if value}
