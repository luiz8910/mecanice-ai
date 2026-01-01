from __future__ import annotations

import json
import re
from typing import Any
import httpx

from .settings import settings
from .models import RecommendationResponse


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class LLMError(RuntimeError):
    pass


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    m = _JSON_RE.search(text)
    if not m:
        raise LLMError("Não foi possível extrair JSON da resposta do modelo.")
    return m.group(0)


async def call_openai_compatible(messages: list[dict[str, str]]) -> str:
    if not settings.LLM_API_KEY:
        raise LLMError("LLM_API_KEY não configurada.")

    url = settings.LLM_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code >= 400:
            raise LLMError(f"Erro do provedor LLM: {r.status_code} - {r.text}")

        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise LLMError(f"Resposta inesperada do provedor LLM: {e}")


async def generate_recommendation(messages: list[dict[str, str]]) -> RecommendationResponse:
    raw = await call_openai_compatible(messages)
    json_str = _extract_json(raw)

    try:
        obj: Any = json.loads(json_str)
    except Exception as e:
        raise LLMError(f"JSON inválido retornado pelo modelo: {e}")

    try:
        return RecommendationResponse.model_validate(obj)
    except Exception as e:
        raise LLMError(f"Resposta não bate no schema: {e}")
