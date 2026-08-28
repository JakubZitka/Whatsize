from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_recommendations_refuses_until_implemented():
    response = client.post(
        "/v1/recommendations",
        json={"profile_id": "p1", "brand_id": "levis", "garment_category": "trousers"},
    )
    assert response.status_code == 501
