from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
import pytest

from app.autoparts_router import router as autoparts_router
from app.auth import require_admin


def allow_admin_override():
    return None


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(autoparts_router, prefix="/autoparts")
    app.dependency_overrides[require_admin] = allow_admin_override

    import app.autoparts_repo as repo

    def fake_create(payload):
        d = payload.model_dump()
        d.update({"id": 1, "created_at": "now", "updated_at": "now"})
        return d

    def fake_get(_id):
        if _id != 1:
            from app.exceptions import NotFoundError
            raise NotFoundError("autopart not found")
        return {"id": 1, "name": "Part", "whatsapp_phone_e164": "+5511999999999", "city": "SP", "state_uf": "SP", "status": "active", "created_at": "now", "updated_at": "now", "address": None, "opening_hours": None, "delivery_types": [], "radius_km": None, "categories": [], "responsible_name": None, "notes": None}

    def fake_list(limit=50, offset=0, status=None):
        return [fake_get(1)]

    def fake_update(_id, payload):
        return fake_get(_id)

    def fake_set_status(_id, status):
        return fake_get(_id)

    monkeypatch.setattr(repo, "create_autopart", fake_create)
    monkeypatch.setattr(repo, "get_autopart", fake_get)
    monkeypatch.setattr(repo, "list_autoparts", fake_list)
    monkeypatch.setattr(repo, "update_autopart", fake_update)
    monkeypatch.setattr(repo, "set_autopart_status", fake_set_status)

    import app.autoparts_router as router_mod
    monkeypatch.setattr(router_mod, "create_autopart", fake_create)
    monkeypatch.setattr(router_mod, "get_autopart", fake_get)
    monkeypatch.setattr(router_mod, "list_autoparts", fake_list)
    monkeypatch.setattr(router_mod, "update_autopart", fake_update)
    monkeypatch.setattr(router_mod, "set_autopart_status", fake_set_status)

    return TestClient(app)


def test_create_and_get(client):
    payload = {
        "name": "Part",
        "whatsapp_phone_e164": "+5511999999999",
        "city": "São Paulo",
        "state_uf": "SP",
    }
    r = client.post("/autoparts", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == 1

    r2 = client.get("/autoparts/1")
    assert r2.status_code == 200


def test_list_and_patch_and_status(client):
    r = client.get("/autoparts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    r2 = client.patch("/autoparts/1", json={"name": "Part2"})
    assert r2.status_code == 200

    r3 = client.patch("/autoparts/1/status", params={"status": "paused"})
    assert r3.status_code == 200
