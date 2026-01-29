from __future__ import annotations

from fastapi import FastAPI
from fastapi.requests import Request

from domain.exceptions.base import AppError
from .errors import to_json_response


def register_exception_handlers(app: FastAPI) -> None:
    """Register handlers on a FastAPI app instance for AppError subclasses."""

    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError):
        return to_json_response(exc)
