from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.bot.adapters.driver.fastapi.dependencies.auth import require_admin
from src.bot.adapters.driver.fastapi.dependencies.repositories import get_mechanic_repo
from src.bot.adapters.driver.fastapi.routers.mechanics import router as mechanics_router
from src.bot.domain.errors import (
	ConflictError,
	MechanicNotFound,
	ValidationError,
	WorkshopNotFound,
)
from src.bot.infrastructure.errors.http_exceptions import register_exception_handlers


def allow_admin_override():
	return None


class FakeMechanicRepo:
	def __init__(self) -> None:
		self._next_id = 1
		self._by_id: dict[int, dict] = {}
		self._by_phone: dict[str, int] = {}
		self._workshops: set[int] = {1, 2}

	def _now(self) -> str:
		return "2026-02-14T00:00:00+00:00"

	def create(self, payload: dict) -> dict:
		if payload.get("workshop_id") is None:
			raise ValidationError("workshop_id is required")
		if payload["workshop_id"] not in self._workshops:
			raise WorkshopNotFound("workshop not found")

		phone_raw = payload["whatsapp_phone_e164"]
		phone = phone_raw if phone_raw.startswith("+") else "+" + phone_raw
		if phone in self._by_phone:
			raise ConflictError("mechanic already exists")
		mid = self._next_id
		self._next_id += 1
		row = {
			"id": mid,
			"name": payload["name"],
			"whatsapp_phone_e164": phone,
			"city": payload["city"],
			"state_uf": payload["state_uf"],
			"status": payload.get("status") or "active",
			"address": payload.get("address"),
			"email": payload.get("email"),
			"workshop_id": payload.get("workshop_id"),
			"categories": payload.get("categories") or [],
			"notes": payload.get("notes"),
			"soft_delete": False,
			"created_at": self._now(),
			"updated_at": self._now(),
		}
		self._by_id[mid] = row
		self._by_phone[phone] = mid
		return row

	def get_row(self, mechanic_id: int):
		row = self._by_id.get(mechanic_id)
		if row and row.get("soft_delete") is True:
			return None
		return dict(row) if row else None

	def list(self, *, limit: int = 50, offset: int = 0, status=None, workshop_id=None):
		items = [x for x in self._by_id.values() if not x.get("soft_delete")]
		if status is not None:
			items = [x for x in items if x.get("status") == status]
		if workshop_id is not None:
			items = [x for x in items if x.get("workshop_id") == workshop_id]
		return [dict(x) for x in items[offset : offset + limit]]

	def update(self, mechanic_id: int, payload: dict) -> dict:
		if mechanic_id not in self._by_id or self._by_id[mechanic_id].get("soft_delete"):
			raise MechanicNotFound("mechanic not found")
		allowed = {
			"name",
			"whatsapp_phone_e164",
			"city",
			"state_uf",
			"status",
			"address",
			"email",
			"workshop_id",
			"categories",
			"notes",
		}
		updates = {k: v for k, v in payload.items() if k in allowed}
		if not updates:
			raise ValidationError("no fields to update")
		if "workshop_id" in updates:
			if updates["workshop_id"] is None:
				raise ValidationError("workshop_id cannot be null")
			if updates["workshop_id"] not in self._workshops:
				raise WorkshopNotFound("workshop not found")

		row = self._by_id[mechanic_id]
		if "whatsapp_phone_e164" in updates:
			new_phone_raw = updates["whatsapp_phone_e164"]
			new_phone = (
				new_phone_raw if new_phone_raw.startswith("+") else "+" + new_phone_raw
			)
			old_phone = row["whatsapp_phone_e164"]
			if new_phone != old_phone and new_phone in self._by_phone:
				raise ConflictError("mechanic update conflicts with existing data")
			self._by_phone.pop(old_phone, None)
			self._by_phone[new_phone] = mechanic_id

		row.update(updates)
		row["updated_at"] = self._now()
		return dict(row)

	def delete(self, mechanic_id: int) -> None:
		row = self._by_id.get(mechanic_id)
		if row is None or row.get("soft_delete"):
			raise MechanicNotFound("mechanic not found")
		row["soft_delete"] = True
		row["updated_at"] = self._now()
		self._by_phone.pop(row["whatsapp_phone_e164"], None)


@pytest.fixture
def client():
	app = FastAPI()
	register_exception_handlers(app)
	app.include_router(mechanics_router)

	repo = FakeMechanicRepo()
	app.dependency_overrides[require_admin] = allow_admin_override
	app.dependency_overrides[get_mechanic_repo] = lambda: repo

	return TestClient(app)


def test_create_get_list_patch_delete_flow(client):
	payload = {
		"name": "Oficina do Zé",
		"whatsapp_phone_e164": "5511999999999",
		"city": "São Paulo",
		"state_uf": "SP",
		"status": "active",
		"workshop_id": 1,
		"categories": ["freios"],
		"notes": "tester",
	}

	r = client.post("/mechanics", json=payload)
	assert r.status_code == 200
	created = r.json()
	assert created["id"] == 1
	assert created["whatsapp_phone_e164"] == "+5511999999999"

	r2 = client.get("/mechanics/1")
	assert r2.status_code == 200

	r3 = client.get("/mechanics")
	assert r3.status_code == 200
	assert isinstance(r3.json(), list)
	assert len(r3.json()) == 1

	r4 = client.patch("/mechanics/1", json={"name": "Zé 2"})
	assert r4.status_code == 200
	assert r4.json()["name"] == "Zé 2"

	r5 = client.delete("/mechanics/1")
	assert r5.status_code == 204

	r6 = client.get("/mechanics/1")
	assert r6.status_code == 404


def test_create_conflict_returns_409(client):
	payload = {
		"name": "A",
		"whatsapp_phone_e164": "5511999999999",
		"city": "SP",
		"state_uf": "SP",
		"status": "active",
		"workshop_id": 1,
	}
	assert client.post("/mechanics", json=payload).status_code == 200
	r2 = client.post("/mechanics", json=payload)
	assert r2.status_code == 409


def test_patch_empty_returns_422(client):
	payload = {
		"name": "A",
		"whatsapp_phone_e164": "5511999999999",
		"city": "SP",
		"state_uf": "SP",
		"status": "active",
		"workshop_id": 1,
	}
	assert client.post("/mechanics", json=payload).status_code == 200
	r = client.patch("/mechanics/1", json={})
	assert r.status_code == 422


def test_create_without_workshop_returns_422(client):
	payload = {
		"name": "A",
		"whatsapp_phone_e164": "5511999999999",
		"city": "SP",
		"state_uf": "SP",
		"status": "active",
	}
	r = client.post("/mechanics", json=payload)
	assert r.status_code == 422


def test_create_with_unknown_workshop_returns_404(client):
	payload = {
		"name": "A",
		"whatsapp_phone_e164": "5511999999999",
		"city": "SP",
		"state_uf": "SP",
		"status": "active",
		"workshop_id": 999,
	}
	r = client.post("/mechanics", json=payload)
	assert r.status_code == 404
