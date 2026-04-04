from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_llm_call_log_repo,
)
from src.bot.adapters.driver.fastapi.routers.llm_logs import router as llm_logs_router
from src.bot.infrastructure.config.settings import settings
from src.bot.infrastructure.errors.http_exceptions import register_exception_handlers


class FakeLlmCallLogRepo:
    def __init__(self) -> None:
        self.last_filters: dict | None = None
        self.log_id = str(uuid4())

    def list_logs(self, **filters):
        self.last_filters = filters
        return [
            {
                "id": self.log_id,
                "requester_id": "123",
                "thread_id": "10",
                "request_id": "20",
                "provider": "openai",
                "endpoint": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-4o-mini",
                "status": "succeeded",
                "http_status": 200,
                "duration_ms": 812,
                "response_candidate_count": 3,
                "error_message": None,
                "created_at": datetime(2026, 3, 23, tzinfo=timezone.utc),
                "updated_at": datetime(2026, 3, 23, tzinfo=timezone.utc),
            }
        ]

    def get_log(self, log_id: str):
        return {
            "id": log_id,
            "requester_id": "123",
            "thread_id": "10",
            "request_id": "20",
            "provider": "openai",
            "endpoint": "https://api.openai.com/v1/chat/completions",
            "model": "gpt-4o-mini",
            "status": "failed",
            "http_status": 502,
            "duration_ms": 912,
            "response_candidate_count": None,
            "error_message": "Erro do provedor LLM",
            "vehicle_json": {"brand": "Fiat", "model": "Palio", "year": "2015"},
            "context_json": {"thread_id": "10", "original_description": "vela palio 2015"},
            "request_payload_json": {"model": "gpt-4o-mini", "temperature": 0.2},
            "parsed_response_json": None,
            "raw_response_text": "{\"error\": \"boom\"}",
            "metadata_json": {"parts_count": 1},
            "messages": [
                {
                    "id": str(uuid4()),
                    "log_id": log_id,
                    "position": 0,
                    "role": "system",
                    "content": "system prompt",
                    "created_at": datetime(2026, 3, 23, tzinfo=timezone.utc),
                },
                {
                    "id": str(uuid4()),
                    "log_id": log_id,
                    "position": 1,
                    "role": "user",
                    "content": "vela palio 2015",
                    "created_at": datetime(2026, 3, 23, tzinfo=timezone.utc),
                },
            ],
            "created_at": datetime(2026, 3, 23, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 3, 23, tzinfo=timezone.utc),
        }


@pytest.fixture
def client():
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(llm_logs_router)
    repo = FakeLlmCallLogRepo()
    app.dependency_overrides[get_llm_call_log_repo] = lambda: repo
    return TestClient(app), repo


def test_list_llm_logs_requires_admin_token(client):
    test_client, _repo = client
    response = test_client.get("/admin/llm-logs")
    assert response.status_code == 401


def test_list_llm_logs_returns_summary_and_passes_filters(client):
    test_client, repo = client
    response = test_client.get(
        "/admin/llm-logs",
        params={"status": "failed", "model": "gpt-4o-mini", "thread_id": "10"},
        headers={"X-Admin-Token": settings.ADMIN_TOKEN},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["model"] == "gpt-4o-mini"
    assert repo.last_filters == {
        "limit": 50,
        "offset": 0,
        "status": "failed",
        "model": "gpt-4o-mini",
        "requester_id": None,
        "thread_id": "10",
    }


def test_get_llm_log_returns_detail_payload(client):
    test_client, repo = client
    response = test_client.get(
        f"/admin/llm-logs/{repo.log_id}",
        headers={"X-Admin-Token": settings.ADMIN_TOKEN},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == repo.log_id
    assert body["status"] == "failed"
    assert body["context_json"]["thread_id"] == "10"
    assert len(body["messages"]) == 2
