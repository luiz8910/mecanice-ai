from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from src.bot.adapters.driver.fastapi.dependencies.auth import require_admin
from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_quotation_repo,
)
from src.bot.adapters.driver.fastapi.schemas.quotations import (
    QuotationCreateSchema,
    QuotationResponseSchema,
    QuotationUpdateSchema,
)
from src.bot.adapters.driven.db.repositories.quotation_repo_sa import (
    QuotationRepoSqlAlchemy,
)

router = APIRouter(
    prefix="/quotations",
    tags=["quotations"],
    dependencies=[Depends(require_admin)],
)


@router.post("", response_model=QuotationResponseSchema, summary="Criar cotação")
async def create_quotation(
    body: QuotationCreateSchema,
    repo: QuotationRepoSqlAlchemy = Depends(get_quotation_repo),
):
    return repo.create_quotation(body.model_dump())


@router.get(
    "/{quotation_id}",
    response_model=QuotationResponseSchema,
    summary="Buscar cotação por ID",
)
async def get_quotation(
    quotation_id: int,
    repo: QuotationRepoSqlAlchemy = Depends(get_quotation_repo),
):
    return repo.get_quotation(quotation_id)


@router.get(
    "",
    response_model=list[QuotationResponseSchema],
    summary="Listar cotações",
)
async def list_quotations(
    limit: int = 50,
    offset: int = 0,
    seller_id: int | None = None,
    workshop_id: int | None = None,
    status: str | None = None,
    is_urgent: bool | None = None,
    search: str | None = None,
    repo: QuotationRepoSqlAlchemy = Depends(get_quotation_repo),
):
    return repo.list_quotations(
        limit=limit,
        offset=offset,
        seller_id=seller_id,
        workshop_id=workshop_id,
        status=status,
        is_urgent=is_urgent,
        search=search,
    )


@router.patch(
    "/{quotation_id}",
    response_model=QuotationResponseSchema,
    summary="Atualizar cotação",
)
async def update_quotation(
    quotation_id: int,
    body: QuotationUpdateSchema,
    repo: QuotationRepoSqlAlchemy = Depends(get_quotation_repo),
):
    payload = body.model_dump(exclude_unset=True)
    return repo.update_quotation(quotation_id, payload)


@router.delete(
    "/{quotation_id}",
    status_code=204,
    summary="Remover cotação (exclusão lógica)",
)
async def delete_quotation(
    quotation_id: int,
    repo: QuotationRepoSqlAlchemy = Depends(get_quotation_repo),
) -> Response:
    repo.delete_quotation(quotation_id)
    return Response(status_code=204)
