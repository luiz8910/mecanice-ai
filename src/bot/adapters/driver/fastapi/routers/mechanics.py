"""Mechanics CRUD router (admin-only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from src.bot.adapters.driver.fastapi.dependencies.auth import require_admin
from src.bot.adapters.driver.fastapi.dependencies.repositories import (
	get_mechanic_repo,
)
from src.bot.adapters.driver.fastapi.schemas.mechanics import (
	MechanicCreateSchema,
	MechanicResponseSchema,
	MechanicUpdateSchema,
)
from src.bot.adapters.driven.db.repositories.mechanic_repo_sa import (
	MechanicRepoSqlAlchemy,
)
from src.bot.domain.errors import MechanicNotFound


router = APIRouter(
	prefix="/mechanics",
	tags=["mechanics"],
	dependencies=[Depends(require_admin)],
)


@router.post("", response_model=MechanicResponseSchema, summary="Criar mecânico")
async def create_mechanic(
	body: MechanicCreateSchema,
	repo: MechanicRepoSqlAlchemy = Depends(get_mechanic_repo),
):
	return repo.create(body.model_dump())


@router.get("/{mechanic_id}", response_model=MechanicResponseSchema, summary="Buscar mecânico")
async def get_mechanic(
	mechanic_id: int,
	repo: MechanicRepoSqlAlchemy = Depends(get_mechanic_repo),
):
	row = repo.get_row(mechanic_id)
	if row is None:
		raise MechanicNotFound("mechanic not found")
	return row


@router.get("", response_model=list[MechanicResponseSchema], summary="Listar mecânicos")
async def list_mechanics(
	limit: int = 50,
	offset: int = 0,
	status: str | None = None,
	workshop_id: int | None = None,
	repo: MechanicRepoSqlAlchemy = Depends(get_mechanic_repo),
):
	return repo.list(
		limit=limit,
		offset=offset,
		status=status,
		workshop_id=workshop_id,
	)


@router.patch(
	"/{mechanic_id}",
	response_model=MechanicResponseSchema,
	summary="Atualizar mecânico (parcial)",
)
async def patch_mechanic(
	mechanic_id: int,
	body: MechanicUpdateSchema,
	repo: MechanicRepoSqlAlchemy = Depends(get_mechanic_repo),
):
	payload = body.model_dump(exclude_unset=True)
	return repo.update(mechanic_id, payload)


@router.delete(
	"/{mechanic_id}",
	status_code=204,
	summary="Remover mecânico",
)
async def delete_mechanic(
	mechanic_id: int,
	repo: MechanicRepoSqlAlchemy = Depends(get_mechanic_repo),
) -> Response:
	repo.delete(mechanic_id)
	return Response(status_code=204)
