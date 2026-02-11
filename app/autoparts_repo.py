"""Repository functions for AutoParts (compat).

In production these should talk to the database.
Unit tests monkeypatch these functions.
"""

from __future__ import annotations

from typing import Any, Optional

from .autoparts_schemas import AutoPartCreate, AutoPartUpdate


def create_autopart(payload: AutoPartCreate) -> dict[str, Any]:
    raise NotImplementedError


def get_autopart(autopart_id: int) -> dict[str, Any]:
    raise NotImplementedError


def list_autoparts(limit: int = 50, offset: int = 0, status: Optional[str] = None):
    raise NotImplementedError


def update_autopart(autopart_id: int, payload: AutoPartUpdate) -> dict[str, Any]:
    raise NotImplementedError


def set_autopart_status(autopart_id: int, status: str) -> dict[str, Any]:
    raise NotImplementedError
