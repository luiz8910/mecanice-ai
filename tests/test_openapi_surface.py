from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


def test_openapi_excludes_whatsapp_and_test_routes():
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"].keys()
    assert "/whatsapp/webhook" not in paths
    assert "/test/whatsapp" not in paths
    assert "/test/whatsapp/api/messages" not in paths
    assert "/auth/login" in paths
    assert "/threads" in paths
    assert "/offers/{offer_id}/submit" in paths
    assert "/offers/{offer_id}/finalize" in paths
    assert "/mechanic/service-orders" in paths
    assert "/mechanic/service-orders/{service_order_id}" in paths
