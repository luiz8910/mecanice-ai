"""Seller inbox routes backed by browser-first quotation threads."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.bot.adapters.driver.fastapi.dependencies.auth import (
    BrowserIdentity,
    require_seller,
)
from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_browser_thread_repo,
)
from src.bot.adapters.driver.fastapi.schemas.seller_inbox import (
    InboxItemDetailSchema,
    InboxItemSchema,
    InboxItemUpdateSchema,
    InboxListResponseSchema,
    WorkshopInfoSchema,
)
from src.bot.adapters.driven.db.repositories.browser_thread_repo_sa import (
    BrowserThreadRepoSqlAlchemy,
)

router = APIRouter(prefix="/seller", tags=["seller"])


def _vehicle_summary(row: dict) -> str | None:
    values = [row.get("vehicle_brand"), row.get("vehicle_model"), row.get("vehicle_year")]
    parts = [str(value) for value in values if value]
    return " / ".join(parts) if parts else None


@router.get(
    "/inbox",
    response_model=InboxListResponseSchema,
    summary="Listar threads atribuídas ao vendedor logado",
)
async def list_inbox(
    status: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
    seller: BrowserIdentity = Depends(require_seller),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    rows, total = repo.seller_inbox_list(
        seller_id=seller.vendor_id,
        shop_id=seller.shop_id,
        status=status,
        search=q,
        page=page,
        page_size=page_size,
    )

    items = [
        InboxItemSchema(
            inbox_item_id=str(row["id"]),
            request_id=str(row["request_id"]),
            store_id=str(seller.shop_id),
            vendor_id=str(seller.vendor_id),
            status=row["status"],
            created_at=row["created_at"],
            last_updated_at=row["updated_at"],
            workshop_name=row.get("workshop_name"),
            part_number=row.get("part_number"),
            part_description=row.get("original_description"),
            vehicle_summary=_vehicle_summary(row),
            has_offer=(row.get("submitted_offer_count") or 0) > 0,
        )
        for row in rows
    ]

    return InboxListResponseSchema(items=items, page=page, page_size=page_size, total=total)


@router.get(
    "/inbox/{inbox_item_id}",
    response_model=InboxItemDetailSchema,
    summary="Detalhe completo de uma thread na inbox do vendedor",
)
async def get_inbox_item(
    inbox_item_id: int,
    seller: BrowserIdentity = Depends(require_seller),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    detail = repo.seller_inbox_get(
        thread_id=inbox_item_id,
        seller_id=seller.vendor_id,
        shop_id=seller.shop_id,
    )
    thread = detail["thread"]
    request = detail["request"]
    workshop = detail.get("workshop")
    offers = detail["offers"]
    current_offer = offers[0] if offers else None
    return InboxItemDetailSchema(
        inbox_item_id=str(thread["id"]),
        request_id=str(request["id"]),
        store_id=str(seller.shop_id),
        vendor_id=str(seller.vendor_id),
        status=thread["status"],
        created_at=thread["created_at"],
        last_updated_at=thread["updated_at"],
        workshop=WorkshopInfoSchema(
            workshop_id=workshop["id"],
            name=workshop["name"],
            phone=workshop.get("phone"),
            address=workshop.get("address"),
        )
        if workshop is not None
        else None,
        part_number=request.get("part_number"),
        part_description=request.get("original_description"),
        vehicle_summary=_vehicle_summary(thread),
        original_message=request.get("original_description"),
        notes=current_offer.get("notes") if current_offer else None,
        messages=detail["messages"],
        suggestions=detail["suggestions"],
        current_offer=current_offer,
    )


@router.patch(
    "/inbox/{inbox_item_id}",
    summary="Atualizar status de uma thread na inbox do vendedor",
)
async def update_inbox_item(
    inbox_item_id: int,
    body: InboxItemUpdateSchema,
    seller: BrowserIdentity = Depends(require_seller),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    repo.update_thread_status_for_seller(
        thread_id=inbox_item_id,
        seller_id=seller.vendor_id,
        shop_id=seller.shop_id,
        new_status=body.status,
    )
    return {"success": True}
