from __future__ import annotations

import asyncio
from types import SimpleNamespace

from src.bot.adapters.driven.llm.llm_recommendation_adapter import (
    OpenAiRecommendationAdapter,
)
from src.bot.application.dtos.recommendation.part_request import PartRequest
from src.bot.application.dtos.recommendation.recommendation_request import (
    RecommendationRequest,
)


class FakeLogStore:
    def __init__(self) -> None:
        self.created_payload: dict | None = None
        self.success_payload: dict | None = None
        self.failure_payload: dict | None = None

    def create_log(self, payload: dict) -> str:
        self.created_payload = payload
        return "log-123"

    def mark_success(self, log_id: str, payload: dict) -> None:
        self.success_payload = {"log_id": log_id, **payload}

    def mark_failure(self, log_id: str, payload: dict) -> None:
        self.failure_payload = {"log_id": log_id, **payload}


class FakeResponse:
    def __init__(self) -> None:
        self.status_code = 200
        self.text = (
            '{"choices":[{"message":{"content":"{\\"id\\":\\"req-1\\",'
            '\\"candidates\\":[{\\"id\\":\\"1\\",\\"part_number\\":\\"BKR6E-11\\",'
            '\\"brand\\":\\"NGK\\",\\"score\\":0.9,\\"metadata\\":{}}],\\"raw\\":{}}"}}]}'
        )

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"id":"req-1","candidates":[{"id":"1","part_number":"BKR6E-11",'
                            '"brand":"NGK","score":0.9,"metadata":{}}],"raw":{}}'
                        )
                    }
                }
            ]
        }


class FakeAsyncClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers=None, json=None):
        return FakeResponse()


def test_openai_adapter_persists_llm_log(monkeypatch):
    monkeypatch.setattr(
        "src.bot.adapters.driven.llm.llm_recommendation_adapter.httpx.AsyncClient",
        FakeAsyncClient,
    )
    settings = SimpleNamespace(
        LLM_API_KEY="test-key",
        LLM_BASE_URL="https://api.openai.com/v1",
        LLM_MODEL="gpt-4o-mini",
        LLM_TEMPERATURE=0.2,
        LLM_TIMEOUT_SECONDS=30,
        LLM_PROVIDER="openai",
    )
    log_store = FakeLogStore()
    adapter = OpenAiRecommendationAdapter(settings, log_store=log_store)
    request = RecommendationRequest(
        requester_id="req-1",
        vehicle={"brand": "Fiat", "model": "Palio", "year": "2015"},
        parts=[PartRequest(description="vela para palio 2015", quantity=4)],
        context={"thread_id": "10", "original_description": "vela para palio 2015"},
    )

    response = asyncio.run(adapter.generate(request))

    assert response.candidates[0].part_number == "BKR6E-11"
    assert log_store.created_payload is not None
    assert log_store.created_payload["thread_id"] == "10"
    assert log_store.created_payload["model"] == "gpt-4o-mini"
    assert log_store.success_payload is not None
    assert log_store.success_payload["log_id"] == "log-123"
    assert log_store.success_payload["http_status"] == 200
    assert log_store.success_payload["response_candidate_count"] == 1
    assert log_store.failure_payload is None
