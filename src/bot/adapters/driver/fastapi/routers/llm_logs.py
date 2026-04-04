from __future__ import annotations

from fastapi import APIRouter, Depends

from src.bot.adapters.driver.fastapi.dependencies.auth import require_admin
from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_llm_call_log_repo,
)
from src.bot.adapters.driver.fastapi.schemas.llm_logs import (
    LlmLogDetailSchema,
    LlmLogSummarySchema,
)
from src.bot.adapters.driven.db.repositories.llm_call_log_repo_sa import (
    LlmCallLogRepoSqlAlchemy,
)

router = APIRouter(
    prefix="/admin/llm-logs",
    tags=["llm-logs"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[LlmLogSummarySchema], summary="Listar logs de chamadas LLM")
async def list_llm_logs(
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    model: str | None = None,
    requester_id: str | None = None,
    thread_id: str | None = None,
    repo: LlmCallLogRepoSqlAlchemy = Depends(get_llm_call_log_repo),
):
    return repo.list_logs(
        limit=limit,
        offset=offset,
        status=status,
        model=model,
        requester_id=requester_id,
        thread_id=thread_id,
    )


@router.get(
    "/{log_id}",
    response_model=LlmLogDetailSchema,
    summary="Detalhar uma chamada LLM específica",
)
async def get_llm_log(
    log_id: str,
    repo: LlmCallLogRepoSqlAlchemy = Depends(get_llm_call_log_repo),
):
    return repo.get_log(log_id)
