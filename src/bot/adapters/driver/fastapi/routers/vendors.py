from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from src.bot.adapters.driver.fastapi.dependencies.auth import require_admin
from src.bot.adapters.driver.fastapi.dependencies.repositories import get_vendor_repo
from src.bot.adapters.driver.fastapi.schemas.vendors import (
    VendorAssignmentCreateSchema,
    VendorAssignmentResponseSchema,
    VendorCreateSchema,
    VendorMetricEventResponseSchema,
    VendorResponseSchema,
    VendorUpdateSchema,
)
from src.bot.adapters.driven.db.repositories.vendor_repo_sa import VendorRepoSqlAlchemy

router = APIRouter(
    prefix="/vendors",
    tags=["vendors"],
    dependencies=[Depends(require_admin)],
)


@router.post("", response_model=VendorResponseSchema, summary="Criar vendedor")
async def create_vendor(
    body: VendorCreateSchema,
    repo: VendorRepoSqlAlchemy = Depends(get_vendor_repo),
):
    return repo.create_vendor(body.model_dump())


@router.get("/{vendor_id}", response_model=VendorResponseSchema, summary="Buscar vendedor")
async def get_vendor(
    vendor_id: int,
    repo: VendorRepoSqlAlchemy = Depends(get_vendor_repo),
):
    return repo.get_vendor(vendor_id)


@router.get("", response_model=list[VendorResponseSchema], summary="Listar vendedores")
async def list_vendors(
    limit: int = 50,
    offset: int = 0,
    autopart_id: int | None = None,
    active: bool | None = None,
    repo: VendorRepoSqlAlchemy = Depends(get_vendor_repo),
):
    return repo.list_vendors(
        limit=limit,
        offset=offset,
        autopart_id=autopart_id,
        active=active,
    )


@router.patch("/{vendor_id}", response_model=VendorResponseSchema, summary="Atualizar vendedor")
async def update_vendor(
    vendor_id: int,
    body: VendorUpdateSchema,
    repo: VendorRepoSqlAlchemy = Depends(get_vendor_repo),
):
    payload = body.model_dump(exclude_unset=True)
    return repo.update_vendor(vendor_id, payload)


@router.delete("/{vendor_id}", status_code=204, summary="Remover vendedor (exclusão lógica)")
async def delete_vendor(
    vendor_id: int,
    repo: VendorRepoSqlAlchemy = Depends(get_vendor_repo),
) -> Response:
    repo.delete_vendor(vendor_id)
    return Response(status_code=204)


@router.post(
    "/assignments",
    response_model=VendorAssignmentResponseSchema,
    summary="Vincular oficina x autopeça a vendedor",
)
async def create_assignment(
    body: VendorAssignmentCreateSchema,
    repo: VendorRepoSqlAlchemy = Depends(get_vendor_repo),
):
    return repo.assign_vendor_to_workshop(
        workshop_id=body.workshop_id,
        autopart_id=body.autopart_id,
        vendor_id=body.vendor_id,
    )


@router.get(
    "/assignments",
    response_model=list[VendorAssignmentResponseSchema],
    summary="Listar vínculos oficina-autopeça-vendedor",
)
async def list_assignments(
    workshop_id: int | None = None,
    autopart_id: int | None = None,
    vendor_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    repo: VendorRepoSqlAlchemy = Depends(get_vendor_repo),
):
    return repo.list_assignments(
        workshop_id=workshop_id,
        autopart_id=autopart_id,
        vendor_id=vendor_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/metrics/events",
    response_model=list[VendorMetricEventResponseSchema],
    summary="Listar eventos de métricas de vendedores",
)
async def list_metric_events(
    vendor_id: int | None = None,
    event_type: str | None = None,
    start_ts: str | None = None,
    end_ts: str | None = None,
    limit: int = 200,
    offset: int = 0,
    repo: VendorRepoSqlAlchemy = Depends(get_vendor_repo),
):
    return repo.get_metric_events(
        vendor_id=vendor_id,
        event_type=event_type,
        start_ts=start_ts,
        end_ts=end_ts,
        limit=limit,
        offset=offset,
    )
