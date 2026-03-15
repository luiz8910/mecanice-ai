from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from src.bot.adapters.driver.fastapi.dependencies.auth import (
    BrowserIdentity,
    require_authenticated,
    require_seller,
)
from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_browser_thread_repo,
)
from src.bot.adapters.driver.fastapi.schemas.threads import (
    OfferFinalizeSchema,
    OfferItemCreateSchema,
    OfferItemResponseSchema,
    OfferSubmitResponseSchema,
    OfferSubmitSchema,
    OfferItemUpdateSchema,
    OfferResponseSchema,
)
from src.bot.adapters.driven.db.repositories.browser_thread_repo_sa import (
    BrowserThreadRepoSqlAlchemy,
)

router = APIRouter(prefix="/offers", tags=["offers"])


@router.get("/{offer_id}", response_model=OfferResponseSchema, summary="Detalhar oferta")
async def get_offer(
    offer_id: int,
    actor: BrowserIdentity = Depends(require_authenticated),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    return repo.get_offer(offer_id=offer_id, actor=actor)


@router.post(
    "/{offer_id}/items",
    response_model=OfferItemResponseSchema,
    summary="Adicionar item à oferta",
)
async def add_offer_item(
    offer_id: int,
    body: OfferItemCreateSchema,
    seller: BrowserIdentity = Depends(require_seller),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    return repo.add_offer_item(
        offer_id=offer_id,
        seller_id=seller.vendor_id,
        payload=body.model_dump(),
    )


@router.put(
    "/{offer_id}/items/{item_id}",
    response_model=OfferItemResponseSchema,
    summary="Atualizar item da oferta",
)
async def update_offer_item(
    offer_id: int,
    item_id: int,
    body: OfferItemUpdateSchema,
    seller: BrowserIdentity = Depends(require_seller),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    return repo.update_offer_item(
        offer_id=offer_id,
        item_id=item_id,
        seller_id=seller.vendor_id,
        payload=body.model_dump(exclude_unset=True),
    )


@router.delete(
    "/{offer_id}/items/{item_id}",
    status_code=204,
    summary="Remover item da oferta",
)
async def delete_offer_item(
    offer_id: int,
    item_id: int,
    seller: BrowserIdentity = Depends(require_seller),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
) -> Response:
    repo.delete_offer_item(
        offer_id=offer_id,
        item_id=item_id,
        seller_id=seller.vendor_id,
    )
    return Response(status_code=204)


@router.post(
    "/{offer_id}/submit",
    response_model=OfferSubmitResponseSchema,
    summary="Submeter oferta do vendedor",
)
async def submit_offer(
    offer_id: int,
    body: OfferSubmitSchema = OfferSubmitSchema(),
    seller: BrowserIdentity = Depends(require_seller),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    return repo.submit_offer(
        offer_id=offer_id,
        seller_id=seller.vendor_id,
        payload=body.model_dump(exclude_unset=True),
    )


@router.post(
    "/{offer_id}/finalize",
    response_model=OfferResponseSchema,
    summary="Consolidar orçamento final da oferta",
)
async def finalize_offer(
    offer_id: int,
    body: OfferFinalizeSchema = OfferFinalizeSchema(),
    seller: BrowserIdentity = Depends(require_seller),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    return repo.finalize_offer(
        offer_id=offer_id,
        seller_id=seller.vendor_id,
        payload=body.model_dump(exclude_unset=True),
    )
