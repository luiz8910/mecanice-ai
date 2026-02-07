from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import require_admin
from .autoparts_schemas import (
    AutoPartCreate,
    AutoPartRead,
    AutoPartUpdate,
    AutoPartStatus,
)
from .autoparts_repo import (
    create_autopart,
    get_autopart,
    list_autoparts,
    update_autopart,
    set_autopart_status,
)
from .exceptions import NotFoundError, DuplicatePhoneError


router = APIRouter(tags=["autoparts"])


@router.post("", response_model=AutoPartRead, dependencies=[Depends(require_admin)])
def create(payload: AutoPartCreate):
    try:
        return create_autopart(payload)
    except DuplicatePhoneError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=list[AutoPartRead], dependencies=[Depends(require_admin)])
def list_(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: AutoPartStatus | None = Query(None),
):
    return list_autoparts(limit=limit, offset=offset, status=status)


@router.get("/{autopart_id}", response_model=AutoPartRead, dependencies=[Depends(require_admin)])
def get_(autopart_id: int):
    try:
        return get_autopart(autopart_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{autopart_id}", response_model=AutoPartRead, dependencies=[Depends(require_admin)])
def patch_(autopart_id: int, payload: AutoPartUpdate):
    try:
        return update_autopart(autopart_id, payload)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DuplicatePhoneError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.patch("/{autopart_id}/status", response_model=AutoPartRead, dependencies=[Depends(require_admin)])
def set_status(autopart_id: int, status: AutoPartStatus):
    try:
        return set_autopart_status(autopart_id, status)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
