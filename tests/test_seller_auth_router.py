"""Tests for POST /seller/login and POST /seller/credentials."""

from __future__ import annotations

import bcrypt
import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.bot.adapters.driver.fastapi.dependencies.auth import require_admin
from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_seller_credential_repo,
)
from src.bot.adapters.driver.fastapi.routers.seller_auth import router as seller_auth_router
from src.bot.domain.errors import ConflictError, UnauthorizedError, ValidationError
from src.bot.infrastructure.errors.http_exceptions import register_exception_handlers


def allow_admin_override():
    return None


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


class FakeSellerCredentialRepo:
    """In-memory substitute for SellerCredentialRepoSqlAlchemy."""

    def __init__(self) -> None:
        self._next_id = 1
        self._creds: dict[int, dict] = {}
        # seed one pre-existing vendor
        self._vendors = {
            1: {"id": 1, "autopart_id": 10, "name": "Carlos Silva"},
            2: {"id": 2, "autopart_id": 10, "name": "Maria Souza"},
        }

    def _now(self) -> str:
        return "2026-06-01T00:00:00+00:00"

    def create_credential(self, payload: dict) -> dict:
        seller_id = int(payload["seller_id"])
        autopart_id = int(payload["autopart_id"])

        vendor = self._vendors.get(seller_id)
        if vendor is None:
            raise ValidationError("seller (vendor) not found")
        if vendor["autopart_id"] != autopart_id:
            raise ValidationError("autopart_id does not match vendor's store")

        # check uniqueness
        for c in self._creds.values():
            if c["email"] == payload["email"].strip().lower():
                raise ConflictError("email already registered")

        cid = self._next_id
        self._next_id += 1
        row = {
            "id": cid,
            "seller_id": seller_id,
            "autopart_id": autopart_id,
            "email": payload["email"].strip().lower(),
            "password_hash": _hash(payload["password"]),
            "active": True,
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        self._creds[cid] = row
        return {k: v for k, v in row.items() if k != "password_hash"}

    def authenticate(self, email: str, password: str) -> dict:
        email_lower = email.strip().lower()
        for c in self._creds.values():
            if c["email"] == email_lower and c["active"]:
                if bcrypt.checkpw(password.encode(), c["password_hash"].encode()):
                    vendor = self._vendors[c["seller_id"]]
                    return {
                        "seller_id": c["seller_id"],
                        "autopart_id": c["autopart_id"],
                        "email": c["email"],
                        "seller_name": vendor["name"],
                    }
                raise UnauthorizedError("E-mail ou senha inválidos.")
        raise UnauthorizedError("E-mail ou senha inválidos.")


@pytest.fixture
def fake_repo():
    return FakeSellerCredentialRepo()


@pytest.fixture
def client(fake_repo):
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(seller_auth_router)

    app.dependency_overrides[require_admin] = allow_admin_override
    app.dependency_overrides[get_seller_credential_repo] = lambda: fake_repo

    return TestClient(app)


# ── credential creation ─────────────────────────────────────────

def test_create_credential_success(client):
    r = client.post(
        "/seller/credentials",
        json={
            "seller_id": 1,
            "autopart_id": 10,
            "email": "carlos@autoparts.com",
            "password": "senha123",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["seller_id"] == 1
    assert body["email"] == "carlos@autoparts.com"
    assert "password_hash" not in body


def test_create_credential_duplicate_email(client):
    payload = {
        "seller_id": 1,
        "autopart_id": 10,
        "email": "dup@autoparts.com",
        "password": "senha123",
    }
    r1 = client.post("/seller/credentials", json=payload)
    assert r1.status_code == 200

    r2 = client.post("/seller/credentials", json=payload)
    assert r2.status_code == 409


def test_create_credential_vendor_not_found(client):
    r = client.post(
        "/seller/credentials",
        json={
            "seller_id": 999,
            "autopart_id": 10,
            "email": "nope@test.com",
            "password": "senha123",
        },
    )
    assert r.status_code == 422


def test_create_credential_wrong_autopart(client):
    r = client.post(
        "/seller/credentials",
        json={
            "seller_id": 1,
            "autopart_id": 99,
            "email": "wrong@test.com",
            "password": "senha123",
        },
    )
    assert r.status_code == 422


# ── login ────────────────────────────────────────────────────────

def test_login_success(client, fake_repo):
    # first create a credential
    fake_repo.create_credential(
        {
            "seller_id": 1,
            "autopart_id": 10,
            "email": "login@autoparts.com",
            "password": "senha123",
        }
    )

    r = client.post(
        "/seller/login",
        json={"email": "login@autoparts.com", "password": "senha123"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "token" in body
    assert body["vendor_id"] == 1
    assert body["store_id"] == 10
    assert body["seller_name"] == "Carlos Silva"

    # verify JWT payload
    decoded = jwt.decode(body["token"], options={"verify_signature": False})
    assert decoded["vendor_id"] == 1
    assert decoded["store_id"] == 10


def test_login_wrong_password(client, fake_repo):
    fake_repo.create_credential(
        {
            "seller_id": 2,
            "autopart_id": 10,
            "email": "maria@autoparts.com",
            "password": "senha123",
        }
    )

    r = client.post(
        "/seller/login",
        json={"email": "maria@autoparts.com", "password": "wrongpass"},
    )
    assert r.status_code == 401


def test_login_unknown_email(client):
    r = client.post(
        "/seller/login",
        json={"email": "ghost@test.com", "password": "anything"},
    )
    assert r.status_code == 401


def test_login_short_password_validation(client):
    """Password < 6 chars should be rejected by schema (422)."""
    r = client.post(
        "/seller/login",
        json={"email": "x@test.com", "password": "abc"},
    )
    assert r.status_code == 422
