"""CRUD endpoints for manufacturers (montadoras)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from src.bot.adapters.driver.fastapi.dependencies.auth import require_admin
from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_manufacturer_repo,
)
from src.bot.adapters.driver.fastapi.schemas.vehicles import (
    ManufacturerCreateSchema,
    ManufacturerResponseSchema,
    ManufacturerUpdateSchema,
)
from src.bot.adapters.driven.db.repositories.manufacturer_repo_sa import (
    ManufacturerRepoSqlAlchemy,
)

router = APIRouter(
    prefix="/manufacturers",
    tags=["manufacturers"],
)


@router.get(
    "",
    response_model=list[ManufacturerResponseSchema],
    summary="List manufacturers",
)
async def list_manufacturers(
    country_of_origin: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
    repo: ManufacturerRepoSqlAlchemy = Depends(get_manufacturer_repo),
):
    return repo.list_manufacturers(
        country_of_origin=country_of_origin,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{manufacturer_id}",
    response_model=ManufacturerResponseSchema,
    summary="Get a manufacturer",
)
async def get_manufacturer(
    manufacturer_id: int,
    repo: ManufacturerRepoSqlAlchemy = Depends(get_manufacturer_repo),
):
    return repo.get_by_id(manufacturer_id)


@router.post(
    "",
    response_model=ManufacturerResponseSchema,
    status_code=201,
    summary="Create a manufacturer",
    dependencies=[Depends(require_admin)],
)
async def create_manufacturer(
    body: ManufacturerCreateSchema,
    repo: ManufacturerRepoSqlAlchemy = Depends(get_manufacturer_repo),
):
    return repo.create(body.model_dump())


@router.patch(
    "/{manufacturer_id}",
    response_model=ManufacturerResponseSchema,
    summary="Update a manufacturer",
    dependencies=[Depends(require_admin)],
)
async def update_manufacturer(
    manufacturer_id: int,
    body: ManufacturerUpdateSchema,
    repo: ManufacturerRepoSqlAlchemy = Depends(get_manufacturer_repo),
):
    return repo.update(manufacturer_id, body.model_dump(exclude_unset=True))


@router.delete(
    "/{manufacturer_id}",
    status_code=204,
    summary="Delete a manufacturer (soft)",
    dependencies=[Depends(require_admin)],
)
async def delete_manufacturer(
    manufacturer_id: int,
    repo: ManufacturerRepoSqlAlchemy = Depends(get_manufacturer_repo),
) -> Response:
    repo.delete(manufacturer_id)
    return Response(status_code=204)
