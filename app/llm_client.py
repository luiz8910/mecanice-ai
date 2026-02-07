# app/llm_client.py
from __future__ import annotations

import base64
import json
import re
from typing import Any, Iterable, Optional

import httpx

from .settings import settings
from .dtos import RecommendationResponse


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class LLMError(RuntimeError):
    pass



def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        # remove ```json or ``` + leading/trailing fences
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json(text: str) -> str:
    """
    Fallback caso o provedor/modelo não respeite response_format=json_object.
    Tenta extrair o primeiro JSON {...} do texto.
    """
    text = _strip_code_fences(text)
    m = _JSON_RE.search(text)
    if not m:
        raise LLMError("Não foi possível extrair JSON da resposta do modelo.")
    return m.group(0)


def build_user_message(
    user_text: str,
    *,
    image_url: str | None = None,
    image_b64: str | None = None,
    image_bytes: bytes | None = None,
    mime_type: str = "image/jpeg",
    detail: str = "auto",
) -> dict[str, Any]:
    """
    Cria um message para Chat Completions que suporta texto + imagem.

    Use UM dos:
      - image_url (URL pública)
      - image_b64 (apenas o base64, sem prefixo)
      - image_bytes (bytes da imagem)

    Retorna:
      {"role":"user","content":[{"type":"text","text":...},{"type":"image_url","image_url":{"url":...}}]}
    """
    if not user_text:
        user_text = ""

    content: list[dict[str, Any]] = [{"type": "text", "text": user_text}]

    img_url_final: str | None = None
    if image_url:
        img_url_final = image_url
    elif image_b64:
        img_url_final = f"data:{mime_type};base64,{image_b64}"
    elif image_bytes:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        img_url_final = f"data:{mime_type};base64,{b64}"

    if img_url_final:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": img_url_final,
                    "detail": detail,
                },
            }
        )

    return {"role": "user", "content": content}


def build_messages(
    *,
    system_prompt: str | None = None,
    user_text: str,
    image_url: str | None = None,
    image_b64: str | None = None,
    image_bytes: bytes | None = None,
    mime_type: str = "image/jpeg",
) -> list[dict[str, Any]]:
    """
    Helper opcional: monta messages com system + user(texto+imagem).
    """
    msgs: list[dict[str, Any]] = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    msgs.append(
        build_user_message(
            user_text,
            image_url=image_url,
            image_b64=image_b64,
            image_bytes=image_bytes,
            mime_type=mime_type,
        )
    )
    return msgs


async def _post_json(
    *,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code >= 400:
            raise LLMError(f"Erro do provedor LLM: {r.status_code} - {r.text}")
        try:
            return r.json()
        except Exception as e:
            raise LLMError(f"Resposta não é JSON válido: {e} - body={r.text}")


def _get_first_choice_content(data: dict[str, Any]) -> str:
    """
    Compatível com Chat Completions:
      data["choices"][0]["message"]["content"]
    """
    try:
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        raise LLMError(f"Resposta inesperada do provedor LLM: {e}")


async def call_openai_compatible(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    force_json: bool = True,
) -> str:
    """
    Chama um provedor compatível com OpenAI (inclui a própria OpenAI) via /chat/completions.
    Usa settings.LLM_*.
    """
    if not settings.LLM_API_KEY:
        raise LLMError("LLM_API_KEY não configurada (ou OPENAI_API_KEY ausente).")

    base = settings.LLM_BASE_URL.rstrip("/")
    url = f"{base}/chat/completions"

    payload: dict[str, Any] = {
        "model": model or settings.LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
    }

    # Ajuda MUITO a garantir JSON estável (se o modelo suportar).
    if force_json:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    data = await _post_json(
        url=url,
        headers=headers,
        payload=payload,
        timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
    )
    return _get_first_choice_content(data)


# -----------------------------
# Embeddings (similaridade)
# -----------------------------

async def embed_text(text: str) -> list[float]:
    """
    Retorna o vetor de embedding para o texto.
    Provider suportado:
      - openai_compatible (default)
      - dummy (retorna [])
    """
    provider = (settings.EMBEDDINGS_PROVIDER or "openai_compatible").strip()

    if provider == "dummy":
        return []

    if provider != "openai_compatible":
        raise LLMError(f"Provider de embeddings não suportado: {provider}")

    if not settings.EMBEDDINGS_API_KEY:
        raise LLMError("EMBEDDINGS_API_KEY não configurada (ou OPENAI_API_KEY ausente).")

    base = settings.EMBEDDINGS_BASE_URL.rstrip("/")
    url = f"{base}/embeddings"

    payload: dict[str, Any] = {
        "model": settings.EMBEDDINGS_MODEL,
        "input": text,
    }

    headers = {
        "Authorization": f"Bearer {settings.EMBEDDINGS_API_KEY}",
        "Content-Type": "application/json",
    }

    data = await _post_json(
        url=url,
        headers=headers,
        payload=payload,
        timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
    )

    try:
        return data["data"][0]["embedding"]
    except Exception as e:
        raise LLMError(f"Resposta inesperada do embeddings: {e}")
