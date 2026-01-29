from __future__ import annotations

from fastapi.responses import JSONResponse

from domain.exceptions.base import AppError


class NotFoundError(AppError):
    status_code = 404

    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(detail)


class DuplicatePhoneError(AppError):
    status_code = 409

    def __init__(self, detail: str = "Phone number already exists") -> None:
        super().__init__(detail)
def to_json_response(exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})
