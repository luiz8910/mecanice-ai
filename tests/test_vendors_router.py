from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.bot.adapters.driver.fastapi.dependencies.auth import require_admin
from src.bot.adapters.driver.fastapi.dependencies.repositories import get_vendor_repo
from src.bot.adapters.driver.fastapi.routers.vendors import router as vendors_router
from src.bot.domain.errors import ConflictError, ValidationError, VendorNotFound
from src.bot.infrastructure.errors.http_exceptions import register_exception_handlers


def allow_admin_override():
    return None


class FakeVendorRepo:
    def __init__(self) -> None:
        self._next_id = 1
        self._vendors: dict[int, dict] = {}

    def _now(self) -> str:
        return "2026-02-19T00:00:00+00:00"

    def create_vendor(self, payload: dict) -> dict:
        email = payload.get("email")
        autopart_id = int(payload["autopart_id"])
        for v in self._vendors.values():
            if v.get("soft_delete"):
                continue
            if v["autopart_id"] == autopart_id and email and v.get("email") == email:
                raise ConflictError("vendor already exists for this autopart/email")

        vid = self._next_id
        self._next_id += 1
        row = {
            "id": vid,
            "autopart_id": autopart_id,
            "name": payload["name"],
            "email": email,
            "active": payload.get("active", True),
            "soft_delete": False,
            "served_workshops_count": 0,
            "quotes_received_count": 0,
            "sales_converted_count": 0,
            "metrics_updated_at": self._now(),
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        self._vendors[vid] = row
        return dict(row)

    def get_vendor(self, vendor_id: int) -> dict:
        row = self._vendors.get(vendor_id)
        if row is None or row.get("soft_delete"):
            raise VendorNotFound("vendor not found")
        return dict(row)

    def list_vendors(self, *, limit=50, offset=0, autopart_id=None, active=None):
        items = [v for v in self._vendors.values() if not v.get("soft_delete")]
        if autopart_id is not None:
            items = [v for v in items if v["autopart_id"] == int(autopart_id)]
        if active is not None:
            items = [v for v in items if bool(v["active"]) is bool(active)]
        return [dict(v) for v in items[offset : offset + limit]]

    def update_vendor(self, vendor_id: int, payload: dict) -> dict:
        row = self._vendors.get(vendor_id)
        if row is None or row.get("soft_delete"):
            raise VendorNotFound("vendor not found")
        allowed = {"name", "email", "active"}
        updates = {k: v for k, v in payload.items() if k in allowed}
        if not updates:
            raise ValidationError("no fields to update")

        if "email" in updates:
            target_email = updates["email"]
            for vid, vendor in self._vendors.items():
                if vid == vendor_id or vendor.get("soft_delete"):
                    continue
                if (
                    vendor["autopart_id"] == row["autopart_id"]
                    and target_email
                    and vendor.get("email") == target_email
                ):
                    raise ConflictError("vendor update conflicts with existing data")

        row.update(updates)
        row["updated_at"] = self._now()
        return dict(row)

    def delete_vendor(self, vendor_id: int) -> None:
        row = self._vendors.get(vendor_id)
        if row is None or row.get("soft_delete"):
            raise VendorNotFound("vendor not found")
        row["soft_delete"] = True
        row["active"] = False
        row["updated_at"] = self._now()

    def assign_vendor_to_workshop(self, *, workshop_id: int, autopart_id: int, vendor_id: int):
        return {
            "id": 1,
            "workshop_id": workshop_id,
            "workshop_name": "Oficina A",
            "autopart_id": autopart_id,
            "autopart_name": "Autopeça A",
            "vendor_id": vendor_id,
            "vendor_name": "Vendedor A",
            "created_at": self._now(),
            "updated_at": self._now(),
        }

    def list_assignments(self, **_kwargs):
        return []

    def get_metric_events(self, **_kwargs):
        return []


@pytest.fixture
def client():
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(vendors_router)

    repo = FakeVendorRepo()
    app.dependency_overrides[require_admin] = allow_admin_override
    app.dependency_overrides[get_vendor_repo] = lambda: repo

    return TestClient(app)


def test_create_get_list_patch_delete_vendor_flow(client):
    create_payload = {
        "autopart_id": 1,
        "name": "João",
        "email": "joao@peca.com",
        "active": True,
    }

    r_create = client.post("/vendors", json=create_payload)
    assert r_create.status_code == 200
    created = r_create.json()
    assert created["id"] == 1

    r_get = client.get("/vendors/1")
    assert r_get.status_code == 200
    assert r_get.json()["name"] == "João"

    r_list = client.get("/vendors")
    assert r_list.status_code == 200
    assert len(r_list.json()) == 1

    r_patch = client.patch("/vendors/1", json={"name": "João Silva", "active": False})
    assert r_patch.status_code == 200
    assert r_patch.json()["name"] == "João Silva"
    assert r_patch.json()["active"] is False

    r_delete = client.delete("/vendors/1")
    assert r_delete.status_code == 204

    r_get_deleted = client.get("/vendors/1")
    assert r_get_deleted.status_code == 404


def test_create_vendor_conflict_returns_409(client):
    payload = {
        "autopart_id": 1,
        "name": "João",
        "email": "joao@peca.com",
        "active": True,
    }
    assert client.post("/vendors", json=payload).status_code == 200
    r2 = client.post("/vendors", json=payload)
    assert r2.status_code == 409


def test_patch_vendor_empty_payload_returns_422(client):
    payload = {
        "autopart_id": 1,
        "name": "João",
        "email": "joao@peca.com",
        "active": True,
    }
    assert client.post("/vendors", json=payload).status_code == 200

    r = client.patch("/vendors/1", json={})
    assert r.status_code == 422
