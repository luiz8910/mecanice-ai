"""FastAPI router for AutoParts admin operations (compat).

Only the API surface used by unit tests is implemented.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .auth import require_admin
from .autoparts_repo import (
    create_autopart,
    get_autopart,
    list_autoparts,
    set_autopart_status,
    update_autopart,
)
from .autoparts_schemas import AutoPartCreate, AutoPartUpdate
from .exceptions import NotFoundError

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("")
def create(body: AutoPartCreate):
    return create_autopart(body)


@router.get("/{autopart_id}")
def get(autopart_id: int):
    try:
        return get_autopart(autopart_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("")
def list(limit: int = 50, offset: int = 0, status: str | None = None):
    return list_autoparts(limit=limit, offset=offset, status=status)


@router.patch("/{autopart_id}")
def patch(autopart_id: int, body: AutoPartUpdate):
    try:
        return update_autopart(autopart_id, body)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/{autopart_id}/status")
def patch_status(autopart_id: int, status: str):
    try:
        return set_autopart_status(autopart_id, status)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
