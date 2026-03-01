import asyncio

from src.bot.application.services.vehicle_plate_resolver import VehiclePlateResolver


class FakeLookup:
    def __init__(self, payload: dict[str, str] | None) -> None:
        self._payload = payload
        self.called_with: str | None = None

    async def lookup(self, plate: str) -> dict[str, str] | None:
        self.called_with = plate
        return self._payload


def test_extract_plate_accepts_legacy_and_mercosul():
    resolver = VehiclePlateResolver(FakeLookup(payload=None))

    assert resolver.extract_plate("cliente pediu peca para o carro abc-1234") == "ABC1234"
    assert resolver.extract_plate("a placa é BRA2E19 e precisa urgente") == "BRA2E19"


def test_resolve_from_text_merges_lookup_fields_and_formats_info():
    lookup = FakeLookup(
        payload={
            "brand": "FIAT",
            "model": "ARGO",
            "model_year": "2021",
            "state": "SP",
        }
    )
    resolver = VehiclePlateResolver(lookup)

    vehicle = asyncio.run(resolver.resolve_from_text("preciso cotar peça para placa BRA2E19"))

    assert lookup.called_with == "BRA2E19"
    assert vehicle == {
        "plate": "BRA2E19",
        "brand": "FIAT",
        "model": "ARGO",
        "model_year": "2021",
        "state": "SP",
    }
    assert resolver.to_vehicle_info(vehicle) == "Placa: BRA2E19 | Marca: FIAT | Modelo: ARGO | Ano: 2021 | UF: SP"


def test_resolve_from_text_returns_only_plate_when_lookup_fails():
    resolver = VehiclePlateResolver(FakeLookup(payload=None))

    vehicle = asyncio.run(resolver.resolve_from_text("confere para placa abc1234"))

    assert vehicle == {"plate": "ABC1234"}
