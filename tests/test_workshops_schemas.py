import pytest

from src.bot.adapters.driver.fastapi.schemas.workshops import (
	WorkshopCreateSchema,
	WorkshopUpdateSchema,
)


def test_e164_validation_accepts_mask_and_normalizes():
	data = WorkshopCreateSchema(
		name="Oficina do Zé",
		whatsapp_phone_e164="+55(11)99999-9999",
		city="São Paulo",
		state_uf="SP",
		status="active",
	)
	assert data.whatsapp_phone_e164 == "+5511999999999"


def test_e164_validation_rejects_invalid():
	with pytest.raises(Exception):
		WorkshopCreateSchema(
			name="Oficina do Zé",
			whatsapp_phone_e164="abc",
			city="São Paulo",
			state_uf="SP",
			status="active",
		)


def test_normalize_state():
	data = WorkshopCreateSchema(
		name="Oficina do Zé",
		whatsapp_phone_e164="5511999999999",
		city="Sao Paulo",
		state_uf="sp",
		status="active",
	)
	assert data.state_uf == "SP"
	assert data.whatsapp_phone_e164 == "+5511999999999"


def test_update_allows_partial_and_validates():
	upd = WorkshopUpdateSchema(whatsapp_phone_e164="+5511999888777", state_uf="rj")
	assert upd.whatsapp_phone_e164 == "+5511999888777"
	assert upd.state_uf == "RJ"


def test_status_validation_rejects_invalid_value():
	with pytest.raises(Exception):
		WorkshopCreateSchema(
			name="Oficina do Zé",
			whatsapp_phone_e164="+5511999999999",
			city="São Paulo",
			state_uf="SP",
			status="paused",
		)
