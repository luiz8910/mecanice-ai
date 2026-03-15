from __future__ import annotations

from fastapi import APIRouter, Depends

from src.bot.adapters.driver.fastapi.dependencies.auth import (
    BrowserIdentity,
    require_mechanic,
)
from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_browser_thread_repo,
)
from src.bot.adapters.driver.fastapi.schemas.service_orders import (
    ServiceOrderDetailSchema,
    ServiceOrderListItemSchema,
)
from src.bot.adapters.driven.db.repositories.browser_thread_repo_sa import (
    BrowserThreadRepoSqlAlchemy,
)

router = APIRouter(prefix="/mechanic/service-orders", tags=["mechanic-service-orders"])


@router.get(
    "",
    response_model=list[ServiceOrderListItemSchema],
    summary="Listar ordens de serviço do mecânico logado",
)
async def list_service_orders(
    mechanic: BrowserIdentity = Depends(require_mechanic),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    return repo.list_service_orders(mechanic_id=mechanic.mechanic_id)


@router.get(
    "/{service_order_id}",
    response_model=ServiceOrderDetailSchema,
    summary="Detalhar ordem de serviço do mecânico logado",
)
async def get_service_order(
    service_order_id: str,
    mechanic: BrowserIdentity = Depends(require_mechanic),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    return repo.get_service_order(
        service_order_id=service_order_id,
        mechanic_id=mechanic.mechanic_id,
    )
