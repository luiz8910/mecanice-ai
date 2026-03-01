from __future__ import annotations

import re

from src.bot.application.ports.driven.vehicle_plate_lookup import VehiclePlateLookupPort

_PLATE_PATTERN = re.compile(r"\b([A-Za-z]{3}[-\s]?(?:\d{4}|\d[A-Za-z]\d{2}))\b")


def _normalize_plate(raw_plate: str) -> str | None:
    normalized = "".join(char for char in raw_plate.upper() if char.isalnum())
    if len(normalized) != 7:
        return None
    if not normalized[:3].isalpha():
        return None

    tail = normalized[3:]
    if re.fullmatch(r"\d{4}", tail):
        return normalized
    if re.fullmatch(r"\d[A-Z]\d{2}", tail):
        return normalized
    return None


class VehiclePlateResolver:
    def __init__(self, lookup: VehiclePlateLookupPort) -> None:
        self._lookup = lookup

    @staticmethod
    def extract_plate(text: str) -> str | None:
        for match in _PLATE_PATTERN.finditer(text or ""):
            normalized = _normalize_plate(match.group(1))
            if normalized:
                return normalized
        return None

    @staticmethod
    def to_vehicle_info(vehicle: dict[str, str] | None) -> str | None:
        if not vehicle:
            return None

        ordered_fields = [
            ("plate", "Placa"),
            ("brand", "Marca"),
            ("model", "Modelo"),
            ("model_year", "Ano"),
            ("color", "Cor"),
            ("city", "Cidade"),
            ("state", "UF"),
        ]
        parts = [
            f"{label}: {vehicle[key]}"
            for key, label in ordered_fields
            if vehicle.get(key)
        ]
        return " | ".join(parts) if parts else None

    async def resolve_from_text(self, text: str) -> dict[str, str] | None:
        plate = self.extract_plate(text)
        if not plate:
            return None

        details = await self._lookup.lookup(plate)
        if not details:
            return {"plate": plate}

        merged = {"plate": plate, **details}
        return {key: value for key, value in merged.items() if value}
