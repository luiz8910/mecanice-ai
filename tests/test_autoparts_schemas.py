from app.autoparts_schemas import AutoPartCreate, AutoPartUpdate
import pytest


def test_e164_validation_rejects_invalid():
    with pytest.raises(Exception):
        AutoPartCreate(
            name="Part X",
            whatsapp_phone_e164="11999999999",
            city="São Paulo",
            state_uf="SP",
        )


def test_normalize_categories_and_delivery():
    data = AutoPartCreate(
        name="Part X",
        whatsapp_phone_e164="+5511999999999",
        city="Sao Paulo",
        state_uf="sp",
        categories=["Brakes", " brakes ", "lighting"],
        delivery_types=["Pickup", "delivery", "delivery"],
    )
    assert data.categories == ["brakes", "lighting"]
    assert data.delivery_types == ["pickup", "delivery"]


def test_update_allows_partial_and_validates():
    upd = AutoPartUpdate(whatsapp_phone_e164="+5511999888777", state_uf="rj")
    assert upd.whatsapp_phone_e164 == "+5511999888777"
    assert upd.state_uf == "RJ"
