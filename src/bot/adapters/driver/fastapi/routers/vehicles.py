"""CRUD endpoints for vehicles."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from src.bot.adapters.driver.fastapi.dependencies.auth import require_admin
from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_vehicle_repo,
)
from src.bot.adapters.driver.fastapi.schemas.vehicles import (
    VehicleCreateSchema,
    VehicleResponseSchema,
    VehicleUpdateSchema,
)
from src.bot.adapters.driven.db.repositories.vehicle_repo_sa import (
    VehicleRepoSqlAlchemy,
)

router = APIRouter(
    prefix="/vehicles",
    tags=["vehicles"],
)


@router.get(
    "",
    response_model=list[VehicleResponseSchema],
    summary="List vehicles",
)
async def list_vehicles(
    manufacturer_id: int | None = None,
    body_type: str | None = None,
    fuel_type: str | None = None,
    country_of_origin: str | None = None,
    year: int | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    is_current: bool | None = None,
    engine: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
    repo: VehicleRepoSqlAlchemy = Depends(get_vehicle_repo),
):
    return repo.list_vehicles(
        manufacturer_id=manufacturer_id,
        body_type=body_type,
        fuel_type=fuel_type,
        country_of_origin=country_of_origin,
        year=year,
        year_from=year_from,
        year_to=year_to,
        is_current=is_current,
        engine=engine,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{vehicle_id}",
    response_model=VehicleResponseSchema,
    summary="Get a vehicle",
)
async def get_vehicle(
    vehicle_id: int,
    repo: VehicleRepoSqlAlchemy = Depends(get_vehicle_repo),
):
    return repo.get_by_id(vehicle_id)


@router.post(
    "",
    response_model=VehicleResponseSchema,
    status_code=201,
    summary="Create a vehicle",
    dependencies=[Depends(require_admin)],
)
async def create_vehicle(
    body: VehicleCreateSchema,
    repo: VehicleRepoSqlAlchemy = Depends(get_vehicle_repo),
):
    return repo.create(body.model_dump())


@router.patch(
    "/{vehicle_id}",
    response_model=VehicleResponseSchema,
    summary="Update a vehicle",
    dependencies=[Depends(require_admin)],
)
async def update_vehicle(
    vehicle_id: int,
    body: VehicleUpdateSchema,
    repo: VehicleRepoSqlAlchemy = Depends(get_vehicle_repo),
):
    return repo.update(vehicle_id, body.model_dump(exclude_unset=True))


@router.delete(
    "/{vehicle_id}",
    status_code=204,
    summary="Delete a vehicle (soft)",
    dependencies=[Depends(require_admin)],
)
async def delete_vehicle(
    vehicle_id: int,
    repo: VehicleRepoSqlAlchemy = Depends(get_vehicle_repo),
) -> Response:
    repo.delete(vehicle_id)
    return Response(status_code=204)
