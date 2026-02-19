from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.bot.adapters.driver.fastapi.dependencies.auth import require_admin
from src.bot.adapters.driver.fastapi.dependencies.repositories import get_workshop_repo
from src.bot.adapters.driver.fastapi.routers.workshops import router as workshops_router
from src.bot.domain.errors import ConflictError, ValidationError, WorkshopNotFound
from src.bot.infrastructure.errors.http_exceptions import register_exception_handlers


def allow_admin_override():
	return None


class FakeWorkshopRepo:
	def __init__(self) -> None:
		self._next_id = 1
		self._by_id: dict[int, dict] = {}
		self._by_phone: dict[str, int] = {}
		self._linked_mechanics_by_workshop: dict[int, int] = {}

	def _now(self) -> str:
		return "2026-02-14T00:00:00+00:00"

	def create(self, payload: dict) -> dict:
		phone_raw = payload["whatsapp_phone_e164"]
		phone = phone_raw if phone_raw.startswith("+") else "+" + phone_raw
		if phone in self._by_phone:
			raise ConflictError("workshop already exists")
		wid = self._next_id
		self._next_id += 1
		row = {
			"id": wid,
			"name": payload["name"],
			"whatsapp_phone_e164": phone,
			"city": payload["city"],
			"state_uf": payload["state_uf"],
			"status": payload.get("status") or "active",
			"address": payload.get("address"),
			"email": payload.get("email"),
			"notes": payload.get("notes"),
			"soft_delete": False,
			"created_at": self._now(),
			"updated_at": self._now(),
		}
		self._by_id[wid] = row
		self._by_phone[phone] = wid
		return row

	def get_row(self, workshop_id: int):
		row = self._by_id.get(workshop_id)
		if row and row.get("soft_delete") is True:
			return None
		return dict(row) if row else None

	def list_rows(self, *, limit: int = 50, offset: int = 0, status=None):
		items = [x for x in self._by_id.values() if not x.get("soft_delete")]
		if status is not None:
			items = [x for x in items if x.get("status") == status]
		return [dict(x) for x in items[offset : offset + limit]]

	def update(self, workshop_id: int, payload: dict) -> dict:
		if workshop_id not in self._by_id or self._by_id[workshop_id].get("soft_delete"):
			raise WorkshopNotFound("workshop not found")
		allowed = {
			"name",
			"whatsapp_phone_e164",
			"city",
			"state_uf",
			"status",
			"address",
			"email",
			"notes",
		}
		updates = {k: v for k, v in payload.items() if k in allowed}
		if not updates:
			raise ValidationError("no fields to update")

		row = self._by_id[workshop_id]
		if "whatsapp_phone_e164" in updates:
			new_phone_raw = updates["whatsapp_phone_e164"]
			new_phone = (
				new_phone_raw if new_phone_raw.startswith("+") else "+" + new_phone_raw
			)
			old_phone = row["whatsapp_phone_e164"]
			if new_phone != old_phone and new_phone in self._by_phone:
				raise ConflictError("workshop update conflicts with existing data")
			self._by_phone.pop(old_phone, None)
			self._by_phone[new_phone] = workshop_id

		row.update(updates)
		row["updated_at"] = self._now()
		return dict(row)

	def delete(self, workshop_id: int) -> None:
		row = self._by_id.get(workshop_id)
		if row is None or row.get("soft_delete"):
			raise WorkshopNotFound("workshop not found")
		if self._linked_mechanics_by_workshop.get(workshop_id, 0) > 0:
			raise ConflictError("cannot delete workshop with active mechanics")
		row["soft_delete"] = True
		row["updated_at"] = self._now()
		self._by_phone.pop(row["whatsapp_phone_e164"], None)


@pytest.fixture
def client():
	app = FastAPI()
	register_exception_handlers(app)
	app.include_router(workshops_router)

	repo = FakeWorkshopRepo()
	app.state.workshop_repo = repo
	app.dependency_overrides[require_admin] = allow_admin_override
	app.dependency_overrides[get_workshop_repo] = lambda: repo

	return TestClient(app)


def test_create_get_list_patch_delete_flow(client):
	payload = {
		"name": "Oficina do Zé",
		"whatsapp_phone_e164": "5511999999999",
		"city": "São Paulo",
		"state_uf": "SP",
		"status": "active",
		"notes": "tester",
	}

	r = client.post("/workshops", json=payload)
	assert r.status_code == 200
	created = r.json()
	assert created["id"] == 1
	assert created["whatsapp_phone_e164"] == "+5511999999999"

	r2 = client.get("/workshops/1")
	assert r2.status_code == 200

	r3 = client.get("/workshops")
	assert r3.status_code == 200
	assert isinstance(r3.json(), list)
	assert len(r3.json()) == 1

	r4 = client.patch("/workshops/1", json={"name": "Oficina 2"})
	assert r4.status_code == 200
	assert r4.json()["name"] == "Oficina 2"

	r5 = client.delete("/workshops/1")
	assert r5.status_code == 204

	r6 = client.get("/workshops/1")
	assert r6.status_code == 404


def test_create_conflict_returns_409(client):
	payload = {
		"name": "A",
		"whatsapp_phone_e164": "5511999999999",
		"city": "SP",
		"state_uf": "SP",
		"status": "active",
	}
	assert client.post("/workshops", json=payload).status_code == 200
	r2 = client.post("/workshops", json=payload)
	assert r2.status_code == 409


def test_patch_empty_returns_422(client):
	payload = {
		"name": "A",
		"whatsapp_phone_e164": "5511999999999",
		"city": "SP",
		"state_uf": "SP",
		"status": "active",
	}
	assert client.post("/workshops", json=payload).status_code == 200
	r = client.patch("/workshops/1", json={})
	assert r.status_code == 422


def test_list_workshops_filters_by_status(client):
	active_payload = {
		"name": "Ativa",
		"whatsapp_phone_e164": "5511999991111",
		"city": "SP",
		"state_uf": "SP",
		"status": "active",
	}
	blocked_payload = {
		"name": "Bloqueada",
		"whatsapp_phone_e164": "5511999992222",
		"city": "SP",
		"state_uf": "SP",
		"status": "blocked",
	}
	assert client.post("/workshops", json=active_payload).status_code == 200
	assert client.post("/workshops", json=blocked_payload).status_code == 200

	r = client.get("/workshops", params={"status": "blocked"})
	assert r.status_code == 200
	items = r.json()
	assert len(items) == 1
	assert items[0]["status"] == "blocked"


def test_delete_workshop_with_linked_mechanics_returns_409(client):
	payload = {
		"name": "Com vínculo",
		"whatsapp_phone_e164": "5511999993333",
		"city": "SP",
		"state_uf": "SP",
		"status": "active",
	}
	r_create = client.post("/workshops", json=payload)
	assert r_create.status_code == 200
	workshop_id = r_create.json()["id"]

	client.app.state.workshop_repo._linked_mechanics_by_workshop[workshop_id] = 1
	r_delete = client.delete(f"/workshops/{workshop_id}")
	assert r_delete.status_code == 409
