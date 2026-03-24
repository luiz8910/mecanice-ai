"""Concrete adapter that calls an OpenAI-compatible Chat Completions API.

Implements :class:`LlmRecommendationPort` — the only piece of the
application that actually knows about HTTP, httpx and provider specifics.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx

from src.bot.adapters.driven.db.repositories.llm_call_log_repo_sa import (
    LlmCallLogStore,
)
from src.bot.application.dtos.recommendation.recommendation_request import (
    RecommendationRequest,
)
from src.bot.application.dtos.recommendation.recommendation_response import (
    RecommendationResponse,
)
from src.bot.infrastructure.config.settings import Settings
from src.bot.infrastructure.logging import get_logger
from .prompt_templates import build_messages

logger = get_logger(__name__)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class LlmError(RuntimeError):
    """Raised when the LLM call fails or returns unparseable output."""


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json(text: str) -> str:
    text = _strip_code_fences(text)
    m = _JSON_RE.search(text)
    if not m:
        raise LlmError("Não foi possível extrair JSON da resposta do modelo.")
    return m.group(0)


class OpenAiRecommendationAdapter:
    """Driven adapter — OpenAI-compatible LLM provider."""

    def __init__(self, settings: Settings, log_store: Any | None = None) -> None:
        self._settings = settings
        self._log_store = log_store or LlmCallLogStore()

    # ── public interface (matches LlmRecommendationPort) ─────────────

    async def generate(
        self, request: RecommendationRequest
    ) -> RecommendationResponse:
        messages = build_messages(request)
        start = time.perf_counter()
        log_id = self._create_log(request, messages)
        http_status: int | None = None
        raw_text: str | None = None
        response = None
        try:
            response = await self._call_chat_completions(messages)
            http_status = response.status_code
            raw_text = self._extract_content(response)
            parsed = self._parse_response(raw_text, request)
            self._mark_log_success(
                log_id,
                http_status=http_status,
                duration_ms=int((time.perf_counter() - start) * 1000),
                raw_text=raw_text,
                parsed_response=parsed.model_dump(),
            )
            return parsed
        except Exception as exc:
            response_text = None
            if response is not None:
                http_status = response.status_code
                response_text = response.text
            elif raw_text is not None:
                response_text = raw_text
            self._mark_log_failure(
                log_id,
                http_status=http_status,
                duration_ms=int((time.perf_counter() - start) * 1000),
                raw_text=response_text,
                error_message=str(exc),
            )
            raise

    # ── private helpers ──────────────────────────────────────────────

    async def _call_chat_completions(
        self,
        messages: list[dict[str, str]],
    ) -> httpx.Response:
        s = self._settings
        if not s.LLM_API_KEY:
            raise LlmError("LLM_API_KEY não configurada.")

        url = f"{s.LLM_BASE_URL.rstrip('/')}/chat/completions"

        payload: dict[str, Any] = {
            "model": s.LLM_MODEL,
            "messages": messages,
            "temperature": s.LLM_TEMPERATURE,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {s.LLM_API_KEY}",
            "Content-Type": "application/json",
        }

        logger.info(
            "[RECOMMENDER_DEBUG] Calling LLM model=%s url=%s", s.LLM_MODEL, url,
        )

        async with httpx.AsyncClient(timeout=s.LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, headers=headers, json=payload)

        return resp

    def _extract_content(self, resp: httpx.Response) -> str:
        if resp.status_code >= 400:
            raise LlmError(
                f"Erro do provedor LLM: {resp.status_code} — {resp.text[:500]}"
            )

        try:
            data = resp.json()
        except Exception as exc:
            raise LlmError(f"Resposta não é JSON válido: {exc}") from exc

        try:
            content: str = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LlmError(f"Resposta inesperada do provedor: {exc}") from exc

        logger.debug("[RECOMMENDER_DEBUG] LLM raw content: %s", content[:300])
        return content

    def _build_payload_preview(
        self,
        *,
        request: RecommendationRequest,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        context = dict(request.context or {})
        return {
            "requester_id": request.requester_id,
            "thread_id": context.get("thread_id"),
            "request_id": context.get("request_id") or context.get("requested_item_id"),
            "provider": self._settings.LLM_PROVIDER,
            "endpoint": f"{self._settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
            "model": self._settings.LLM_MODEL,
            "vehicle_json": request.vehicle or {},
            "context_json": context,
            "request_payload_json": {
                "model": self._settings.LLM_MODEL,
                "temperature": self._settings.LLM_TEMPERATURE,
                "response_format": {"type": "json_object"},
            },
            "metadata_json": {
                "parts_count": len(request.parts or []),
            },
            "messages": messages,
        }

    def _create_log(
        self,
        request: RecommendationRequest,
        messages: list[dict[str, str]],
    ) -> str | None:
        try:
            return self._log_store.create_log(
                self._build_payload_preview(request=request, messages=messages)
            )
        except Exception as exc:
            logger.warning("[RECOMMENDER_DEBUG] failed to create llm log: %s", exc)
            return None

    def _mark_log_success(
        self,
        log_id: str | None,
        *,
        http_status: int | None,
        duration_ms: int,
        raw_text: str | None,
        parsed_response: dict[str, Any],
    ) -> None:
        if log_id is None:
            return
        try:
            self._log_store.mark_success(
                log_id,
                {
                    "http_status": http_status,
                    "duration_ms": duration_ms,
                    "response_candidate_count": len(parsed_response.get("candidates") or []),
                    "parsed_response_json": parsed_response,
                    "raw_response_text": raw_text,
                },
            )
        except Exception as exc:
            logger.warning("[RECOMMENDER_DEBUG] failed to mark llm log success: %s", exc)

    def _mark_log_failure(
        self,
        log_id: str | None,
        *,
        http_status: int | None,
        duration_ms: int,
        raw_text: str | None,
        error_message: str,
    ) -> None:
        if log_id is None:
            return
        try:
            self._log_store.mark_failure(
                log_id,
                {
                    "http_status": http_status,
                    "duration_ms": duration_ms,
                    "raw_response_text": raw_text,
                    "error_message": error_message,
                },
            )
        except Exception as exc:
            logger.warning("[RECOMMENDER_DEBUG] failed to mark llm log failure: %s", exc)

    def _parse_response(
        self,
        raw: str,
        request: RecommendationRequest,
    ) -> RecommendationResponse:
        raw = raw.strip()
        json_text = raw if raw.startswith("{") else _extract_json(raw)

        try:
            obj: Any = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise LlmError(
                f"JSON inválido retornado pelo modelo: {exc}"
            ) from exc

        # Ensure the response carries an id (echo requester_id if missing)
        if "id" not in obj or not obj["id"]:
            obj["id"] = request.requester_id or "unknown"

        try:
            return RecommendationResponse.model_validate(obj)
        except Exception as exc:
            raise LlmError(f"Resposta não bate no schema: {exc}") from exc
