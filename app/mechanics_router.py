from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import require_admin
from .mechanics_schemas import MechanicCreate, MechanicRead, MechanicUpdate, MechanicStatus
from .mechanics_repo import (
    create_mechanic,
    get_mechanic,
    list_mechanics,
    update_mechanic,
    set_mechanic_status,
    NotFoundError,
    DuplicatePhoneError,
)

router = APIRouter(prefix="/mechanics", tags=["mechanics"])


@router.post("", response_model=MechanicRead, dependencies=[Depends(require_admin)])
def create(payload: MechanicCreate):
    try:
        return create_mechanic(payload)
    except DuplicatePhoneError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=list[MechanicRead], dependencies=[Depends(require_admin)])
def list_(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: MechanicStatus | None = Query(None),
):
    return list_mechanics(limit=limit, offset=offset, status=status)


@router.get("/{mechanic_id}", response_model=MechanicRead, dependencies=[Depends(require_admin)])
def get_(mechanic_id: int):
    try:
        return get_mechanic(mechanic_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{mechanic_id}", response_model=MechanicRead, dependencies=[Depends(require_admin)])
def patch_(mechanic_id: int, payload: MechanicUpdate):
    try:
        return update_mechanic(mechanic_id, payload)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DuplicatePhoneError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.patch("/{mechanic_id}/status", response_model=MechanicRead, dependencies=[Depends(require_admin)])
def set_status(mechanic_id: int, status: MechanicStatus):
    try:
        return set_mechanic_status(mechanic_id, status)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
