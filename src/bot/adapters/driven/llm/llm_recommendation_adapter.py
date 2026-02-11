"""Concrete adapter that calls an OpenAI-compatible Chat Completions API.

Implements :class:`LlmRecommendationPort` — the only piece of the
application that actually knows about HTTP, httpx and provider specifics.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

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

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ── public interface (matches LlmRecommendationPort) ─────────────

    async def generate(
        self, request: RecommendationRequest
    ) -> RecommendationResponse:
        messages = build_messages(request)
        raw_text = await self._call_chat_completions(messages)
        return self._parse_response(raw_text, request)

    # ── private helpers ──────────────────────────────────────────────

    async def _call_chat_completions(
        self,
        messages: list[dict[str, str]],
    ) -> str:
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
            "Calling LLM  model=%s  url=%s", s.LLM_MODEL, url,
        )

        async with httpx.AsyncClient(timeout=s.LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, headers=headers, json=payload)

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

        logger.debug("LLM raw content: %s", content[:300])
        return content

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
