from __future__ import annotations

from threading import Lock


class InMemoryIdempotencyRegistry:
    def __init__(self) -> None:
        self._keys: set[str] = set()
        self._lock = Lock()

    def seen(self, key: str) -> bool:
        with self._lock:
            return key in self._keys

    def mark(self, key: str) -> None:
        with self._lock:
            self._keys.add(key)
