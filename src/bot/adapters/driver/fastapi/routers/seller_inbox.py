"""Seller inbox routes consumed by the Seller Portal front-end."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.bot.adapters.driver.fastapi.dependencies.auth import (
    SellerIdentity,
    require_seller,
)
from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_quotation_repo,
    get_quotation_item_repo,
)
from src.bot.adapters.driver.fastapi.schemas.seller_inbox import (
    InboxItemDetailSchema,
    InboxItemSchema,
    InboxItemUpdateSchema,
    InboxListResponseSchema,
    QuotationEventInlineSchema,
    QuotationItemInlineSchema,
    WorkshopInfoSchema,
)
from src.bot.adapters.driven.db.repositories.quotation_repo_sa import (
    QuotationRepoSqlAlchemy,
)
from src.bot.adapters.driven.db.repositories.quotation_item_repo_sa import (
    QuotationItemRepoSqlAlchemy,
)

router = APIRouter(prefix="/seller", tags=["seller"])


@router.get(
    "/inbox",
    response_model=InboxListResponseSchema,
    summary="Listar cotações atribuídas ao vendedor logado",
)
async def list_inbox(
    status: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
    seller: SellerIdentity = Depends(require_seller),
    repo: QuotationRepoSqlAlchemy = Depends(get_quotation_repo),
):
    rows, total = repo.inbox_list(
        seller_id=seller.vendor_id,
        status=status,
        search=q,
        page=page,
        page_size=page_size,
    )

    items = [
        InboxItemSchema(
            inbox_item_id=str(r["id"]),
            request_id=r["code"],
            store_id=str(r["store_id"]),
            vendor_id=str(r["seller_id"]),
            status=r["status"],
            created_at=r["created_at"],
            last_updated_at=r["updated_at"],
            workshop_name=r.get("workshop_name"),
            part_number=r.get("part_number"),
            part_description=r.get("part_description"),
            vehicle_summary=r.get("vehicle_info"),
            is_urgent=r.get("is_urgent"),
            has_offer=r.get("offer_submitted"),
        )
        for r in rows
    ]

    return InboxListResponseSchema(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/inbox/{inbox_item_id}",
    response_model=InboxItemDetailSchema,
    summary="Detalhe completo de uma cotação na inbox do vendedor",
)
async def get_inbox_item(
    inbox_item_id: int,
    seller: SellerIdentity = Depends(require_seller),
    repo: QuotationRepoSqlAlchemy = Depends(get_quotation_repo),
    item_repo: QuotationItemRepoSqlAlchemy = Depends(get_quotation_item_repo),
):
    r = repo.inbox_get(
        quotation_id=inbox_item_id,
        seller_id=seller.vendor_id,
    )
    items_raw = item_repo.list_items(
        quotation_id=inbox_item_id,
        seller_id=seller.vendor_id,
    )
    events_raw = item_repo.list_events(
        quotation_id=inbox_item_id,
        seller_id=seller.vendor_id,
    )
    return InboxItemDetailSchema(
        inbox_item_id=str(r["id"]),
        request_id=r["code"],
        store_id=str(r["store_id"]),
        vendor_id=str(r["seller_id"]),
        seller_name=r.get("seller_name"),
        status=r["status"],
        created_at=r["created_at"],
        last_updated_at=r["updated_at"],
        workshop=WorkshopInfoSchema(
            workshop_id=r["workshop_id"],
            name=r.get("workshop_name", ""),
            phone=r.get("workshop_phone"),
            address=r.get("workshop_address"),
        ),
        part_number=r.get("part_number"),
        part_description=r.get("part_description"),
        vehicle_summary=r.get("vehicle_info"),
        original_message=r.get("original_message"),
        is_urgent=r.get("is_urgent"),
        has_offer=r.get("offer_submitted"),
        notes=r.get("notes"),
        items=[
            QuotationItemInlineSchema(
                id=i["id"],
                part_number=i["part_number"],
                description=i.get("description", ""),
                brand=i.get("brand"),
                compatibility=i.get("compatibility"),
                price=float(i["price"]) if i.get("price") is not None else None,
                availability=i.get("availability"),
                delivery_time=i.get("delivery_time"),
                confidence_score=float(i["confidence_score"]) if i.get("confidence_score") is not None else None,
                notes=i.get("notes"),
                selected=i.get("selected", False),
            )
            for i in items_raw
        ],
        events=[
            QuotationEventInlineSchema(
                id=e["id"],
                event_type=e["event_type"],
                description=e["description"],
                created_at=e["created_at"],
            )
            for e in events_raw
        ],
    )


@router.patch(
    "/inbox/{inbox_item_id}",
    summary="Atualizar status de um item na inbox do vendedor",
)
async def update_inbox_item(
    inbox_item_id: int,
    body: InboxItemUpdateSchema,
    seller: SellerIdentity = Depends(require_seller),
    repo: QuotationRepoSqlAlchemy = Depends(get_quotation_repo),
):
    repo.inbox_update_status(
        quotation_id=inbox_item_id,
        seller_id=seller.vendor_id,
        new_status=body.status,
    )
    return {"success": True}
