from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .models import RecommendationRequest, RecommendationResponse
from .prompt import build_messages
from .llm_client import generate_recommendation, LLMError
from .cache import TTLCache, build_cache_key
from .settings import settings
from .rag import retrieve_context


app = FastAPI(title="Mecanice MVP (IA-first + RAG)", version="0.2.0")
cache = TTLCache(ttl_seconds=settings.CACHE_TTL_SECONDS)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/parts/recommendations", response_model=RecommendationResponse)
async def parts_recommendations(req: RecommendationRequest):
    # 1) RAG: se não vier contexto, busca no banco
    if not req.context_sources:
        req.context_sources = await retrieve_context(req.user_text)

    # 2) Cache: evita gastar tokens em perguntas repetidas
    cache_key = build_cache_key(req.user_text, req.known_fields.model_dump())
    cached = cache.get(cache_key)
    if cached:
        return cached

    # 3) LLM: sempre retorna JSON válido e validado no schema
    messages = build_messages(req)
    try:
        result = await generate_recommendation(messages)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))

    cache.set(cache_key, result)
    return result
