"""Backward-compatible shim: re-export structured exception API.

This module preserves the original import path ``app.exceptions`` so
existing imports keep working while the real implementations live in
top-level ``domain.exceptions`` and ``infrastructure.exceptions``.
"""

from domain.exceptions.base import AppError
from infrastructure.exceptions import (
    NotFoundError,
    DuplicatePhoneError,
    register_exception_handlers,
)

__all__ = ["AppError", "NotFoundError", "DuplicatePhoneError", "register_exception_handlers"]
