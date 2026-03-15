from __future__ import annotations

import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_browser_auth_repo,
)
from src.bot.adapters.driver.fastapi.routers.auth import router as auth_router
from src.bot.infrastructure.config.settings import settings
from src.bot.infrastructure.errors.http_exceptions import register_exception_handlers


class FakeBrowserAuthRepo:
    def authenticate(self, email: str, password: str) -> dict:
        if email == "mec@test.com" and password == "secret123":
            return {
                "user_id": 11,
                "role": "mechanic",
                "shop_id": 7,
                "vendor_id": None,
                "mechanic_id": 11,
                "name": "Mecânico Teste",
                "email": email,
            }
        if email == "seller@test.com" and password == "secret123":
            return {
                "user_id": 21,
                "role": "seller",
                "shop_id": 9,
                "vendor_id": 21,
                "mechanic_id": None,
                "email": email,
                "name": "Vendedor Teste",
            }
        raise Exception("unexpected authenticate call")

    def create_credential(self, payload: dict) -> dict:
        return {
            "id": 1,
            "role": payload["role"],
            "actor_id": payload.get("actor_id"),
            "email": payload["email"],
            "active": True,
            "created_at": "2026-03-10T00:00:00+00:00",
            "updated_at": "2026-03-10T00:00:00+00:00",
            "name": "Created User",
            "shop_id": 1,
        }


@pytest.fixture
def client():
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(auth_router)
    app.dependency_overrides[get_browser_auth_repo] = lambda: FakeBrowserAuthRepo()
    return TestClient(app)


def test_auth_login_and_me(client: TestClient):
    response = client.post(
        "/auth/login",
        json={"email": "mec@test.com", "password": "secret123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "mechanic"
    decoded = jwt.decode(body["token"], options={"verify_signature": False})
    assert decoded["mechanic_id"] == 11

    me_response = client.get("/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me_response.status_code == 200
    assert me_response.json()["name"] == "Mecânico Teste"


def test_auth_create_credential_with_admin_token(client: TestClient):
    response = client.post(
        "/auth/credentials",
        json={
            "role": "mechanic",
            "actor_id": 11,
            "email": "new@test.com",
            "password": "secret123",
        },
        headers={"X-Admin-Token": settings.ADMIN_TOKEN},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "mechanic"
