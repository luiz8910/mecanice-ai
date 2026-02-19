"""Workshops CRUD router (admin-only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from src.bot.adapters.driver.fastapi.dependencies.auth import require_admin
from src.bot.adapters.driver.fastapi.dependencies.repositories import get_workshop_repo
from src.bot.adapters.driver.fastapi.schemas.workshops import (
	WorkshopCreateSchema,
	WorkshopResponseSchema,
	WorkshopUpdateSchema,
)
from src.bot.adapters.driven.db.repositories.workshop_repo_sa import WorkshopRepoSqlAlchemy
from src.bot.domain.errors import WorkshopNotFound


router = APIRouter(
	prefix="/workshops",
	tags=["workshops"],
	dependencies=[Depends(require_admin)],
)


@router.post("", response_model=WorkshopResponseSchema, summary="Criar oficina")
async def create_workshop(
	body: WorkshopCreateSchema,
	repo: WorkshopRepoSqlAlchemy = Depends(get_workshop_repo),
):
	return repo.create(body.model_dump())


@router.get("/{workshop_id}", response_model=WorkshopResponseSchema, summary="Buscar oficina")
async def get_workshop(
	workshop_id: int,
	repo: WorkshopRepoSqlAlchemy = Depends(get_workshop_repo),
):
	row = repo.get_row(workshop_id)
	if row is None:
		raise WorkshopNotFound("workshop not found")
	return row


@router.get("", response_model=list[WorkshopResponseSchema], summary="Listar oficinas")
async def list_workshops(
	limit: int = 50,
	offset: int = 0,
	status: str | None = None,
	repo: WorkshopRepoSqlAlchemy = Depends(get_workshop_repo),
):
	return repo.list_rows(limit=limit, offset=offset, status=status)


@router.patch(
	"/{workshop_id}",
	response_model=WorkshopResponseSchema,
	summary="Atualizar oficina (parcial)",
)
async def patch_workshop(
	workshop_id: int,
	body: WorkshopUpdateSchema,
	repo: WorkshopRepoSqlAlchemy = Depends(get_workshop_repo),
):
	payload = body.model_dump(exclude_unset=True)
	return repo.update(workshop_id, payload)


@router.delete(
	"/{workshop_id}",
	status_code=204,
	summary="Remover oficina",
)
async def delete_workshop(
	workshop_id: int,
	repo: WorkshopRepoSqlAlchemy = Depends(get_workshop_repo),
) -> Response:
	repo.delete(workshop_id)
	return Response(status_code=204)
