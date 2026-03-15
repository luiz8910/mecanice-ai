from __future__ import annotations

from fastapi import APIRouter, Depends

from src.bot.adapters.driver.fastapi.dependencies.auth import (
    BrowserIdentity,
    require_authenticated,
    require_mechanic,
    require_seller,
)
from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_browser_thread_repo,
)
from src.bot.adapters.driver.fastapi.dependencies.use_cases import (
    get_parts_suggestion_provider,
)
from src.bot.adapters.driver.fastapi.schemas.threads import (
    OfferResponseSchema,
    PartRequestResponseSchema,
    SuggestedPartResponseSchema,
    ThreadComparisonResponseSchema,
    ThreadCreateSchema,
    ThreadDetailResponseSchema,
    ThreadMessageCreateSchema,
    ThreadMessageResponseSchema,
    ThreadSummarySchema,
)
from src.bot.adapters.driven.db.repositories.browser_thread_repo_sa import (
    BrowserThreadRepoSqlAlchemy,
)
from src.bot.application.services.parts_suggestion_provider import PartsSuggestionProvider

router = APIRouter(prefix="/threads", tags=["threads"])


def _thread_vehicle_payload(body: ThreadCreateSchema) -> dict[str, str]:
    if body.vehicle is None:
        return {}
    return {
        key: value
        for key, value in body.vehicle.model_dump().items()
        if value is not None
    }


@router.post("", response_model=ThreadDetailResponseSchema, summary="Criar thread de cotação")
async def create_thread(
    body: ThreadCreateSchema,
    mechanic: BrowserIdentity = Depends(require_mechanic),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
    suggestion_provider: PartsSuggestionProvider = Depends(get_parts_suggestion_provider),
):
    request_status = "processing" if body.generate_suggestions else "ready_for_quote"
    result = repo.create_thread(
        mechanic_id=mechanic.mechanic_id,
        workshop_id=mechanic.shop_id,
        payload=body.model_dump(),
        request_status=request_status,
    )

    if body.generate_suggestions:
        try:
            all_suggestions: list[dict] = []
            vehicle_payload = _thread_vehicle_payload(body)
            for requested_item in result["requested_items"]:
                suggestions = await suggestion_provider.suggest(
                    {
                        "thread_id": result["thread"]["id"],
                        "request_id": result["request"]["id"],
                        "requested_item_id": requested_item["id"],
                        "original_description": requested_item["description"],
                        "part_number": requested_item.get("part_number"),
                        "requested_items_count": requested_item["quantity"],
                        "vehicle": vehicle_payload,
                    }
                )
                for suggestion in suggestions:
                    all_suggestions.append(
                        {
                            **suggestion,
                            "requested_item_id": requested_item["id"],
                        }
                    )
            if all_suggestions:
                result["suggestions"] = repo.save_suggestions(
                    thread_id=result["thread"]["id"],
                    request_id=result["request"]["id"],
                    suggestions=all_suggestions,
                )
        except Exception:
            result["suggestions"] = []
        finally:
            repo.update_request_status(result["request"]["id"], "ready_for_quote")
            result["request"]["status"] = "ready_for_quote"

    return result


@router.get("", response_model=list[ThreadSummarySchema], summary="Listar threads visíveis ao usuário")
async def list_threads(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    actor: BrowserIdentity = Depends(require_authenticated),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    return repo.list_threads(actor=actor, status=status, limit=limit, offset=offset)


@router.get("/{thread_id}", response_model=ThreadDetailResponseSchema, summary="Detalhar thread")
async def get_thread(
    thread_id: int,
    actor: BrowserIdentity = Depends(require_authenticated),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    return repo.get_thread_detail(thread_id=thread_id, actor=actor)


@router.get(
    "/{thread_id}/messages",
    response_model=list[ThreadMessageResponseSchema],
    summary="Listar mensagens da thread",
)
async def list_messages(
    thread_id: int,
    actor: BrowserIdentity = Depends(require_authenticated),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    return repo.list_messages(thread_id=thread_id, actor=actor)


@router.post(
    "/{thread_id}/messages",
    response_model=ThreadMessageResponseSchema,
    summary="Enviar mensagem na thread",
)
async def create_message(
    thread_id: int,
    body: ThreadMessageCreateSchema,
    actor: BrowserIdentity = Depends(require_authenticated),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    return repo.add_message(
        thread_id=thread_id,
        actor=actor,
        sender_role="system" if actor.role == "admin" else actor.role,
        sender_user_ref=f"{actor.role}:{actor.user_id}",
        type_=body.type,
        body=body.body,
    )


@router.get(
    "/{thread_id}/request",
    response_model=PartRequestResponseSchema,
    summary="Buscar request estruturado da thread",
)
async def get_request(
    thread_id: int,
    actor: BrowserIdentity = Depends(require_authenticated),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    return repo.get_request(thread_id=thread_id, actor=actor)


@router.get(
    "/{thread_id}/suggestions",
    response_model=list[SuggestedPartResponseSchema],
    summary="Listar sugestões persistidas da thread",
)
async def list_suggestions(
    thread_id: int,
    actor: BrowserIdentity = Depends(require_authenticated),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    return repo.list_suggestions(thread_id=thread_id, actor=actor)


@router.post(
    "/{thread_id}/offers",
    response_model=OfferResponseSchema,
    summary="Criar ou obter draft de oferta do vendedor",
)
async def create_offer(
    thread_id: int,
    seller: BrowserIdentity = Depends(require_seller),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    return repo.get_or_create_offer(
        thread_id=thread_id,
        seller_id=seller.vendor_id,
        seller_shop_id=seller.shop_id,
    )


@router.get(
    "/{thread_id}/offers",
    response_model=list[OfferResponseSchema],
    summary="Listar ofertas da thread",
)
async def list_offers(
    thread_id: int,
    actor: BrowserIdentity = Depends(require_authenticated),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    return repo.list_offers(thread_id=thread_id, actor=actor)


@router.get(
    "/{thread_id}/comparison",
    response_model=ThreadComparisonResponseSchema,
    summary="Comparação normalizada das ofertas da thread",
)
async def get_comparison(
    thread_id: int,
    mechanic: BrowserIdentity = Depends(require_mechanic),
    repo: BrowserThreadRepoSqlAlchemy = Depends(get_browser_thread_repo),
):
    return repo.get_comparison(thread_id=thread_id, mechanic_id=mechanic.mechanic_id)
