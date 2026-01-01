import time
from typing import Any, Optional


class TTLCache:
    def __init__(self, ttl_seconds: int):
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        item = self._store.get(key)
        if not item:
            return None
        expires_at, value = item
        if time.time() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        expires_at = time.time() + self.ttl
        self._store[key] = (expires_at, value)


def build_cache_key(user_text: str, known_fields: dict) -> str:
    parts = [
        user_text.strip().lower(),
        known_fields.get("axle", "unknown"),
        known_fields.get("rear_brake_type", "unknown"),
        known_fields.get("engine", "unknown"),
        known_fields.get("abs", "unknown"),
    ]
    return "rec:" + ":".join(str(p).lower() for p in parts)
