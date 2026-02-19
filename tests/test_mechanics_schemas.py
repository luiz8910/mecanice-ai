import pytest

from src.bot.adapters.driver.fastapi.schemas.mechanics import (
	MechanicCreateSchema,
	MechanicUpdateSchema,
)


def test_e164_validation_accepts_mask_and_normalizes():
	data = MechanicCreateSchema(
		name="Zé",
		whatsapp_phone_e164="+55(11)99999-9999",
		city="São Paulo",
		state_uf="SP",
		status="active",
		workshop_id=1,
	)
	assert data.whatsapp_phone_e164 == "+5511999999999"


def test_e164_validation_rejects_invalid():
	with pytest.raises(Exception):
		MechanicCreateSchema(
			name="Zé",
			whatsapp_phone_e164="abc",
			city="São Paulo",
			state_uf="SP",
			status="active",
			workshop_id=1,
		)


def test_normalize_categories_and_state():
	data = MechanicCreateSchema(
		name="Zé",
		whatsapp_phone_e164="5511999999999",
		city="Sao Paulo",
		state_uf="sp",
		status="active",
		workshop_id=1,
		categories=["Freios", " freios ", "motor"],
	)
	assert data.categories == ["freios", "motor"]
	assert data.state_uf == "SP"
	assert data.whatsapp_phone_e164 == "+5511999999999"


def test_update_allows_partial_and_validates():
	upd = MechanicUpdateSchema(whatsapp_phone_e164="+5511999888777", state_uf="rj")
	assert upd.whatsapp_phone_e164 == "+5511999888777"
	assert upd.state_uf == "RJ"
