import pytest
from fastapi.testclient import TestClient

from app.main import app, load_reference_data


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_loads_seed_from_database(client):
    body = client.get("/readyz").json()
    assert body["status"] == "ready"
    assert body["store_source"] == "database"
    assert body["brands"] == 100
    assert body["chart_rows"] > 5000
    assert body["db_error"] is None


def test_seed_is_idempotent(client):
    from app.db import get_engine
    from app.seed import migrate_and_seed

    assert migrate_and_seed(get_engine()) is False


def test_brands_list_and_filter(client):
    all_brands = client.get("/v1/brands").json()
    assert len(all_brands) == 100
    assert "vanity_offset_waist_cm" not in all_brands[0]  # private layer stays private
    women = client.get("/v1/brands", params={"gender": "W", "q": "lev"}).json()
    assert [b["brand_id"] for b in women] == ["levis"]


def test_brand_detail(client):
    body = client.get("/v1/brands/hunkemoller").json()
    assert body["categories"] == ["W_BRA"]
    assert "75F" in body["sizes"]["W_BRA"]
    assert client.get("/v1/brands/nope").status_code == 404


def test_recommendation_endpoint(client):
    response = client.post("/v1/recommendations", json={
        "gender": "W", "brand_id": "levis", "category_code": "W_JEANS",
        "measurements": {"waist_cm": 76, "hip_cm": 106, "stature_cm": 168}})
    assert response.status_code == 200
    body = response.json()
    assert body["size_label"] == "W27"
    assert body["fit_code"] == "curvy"


def test_brand_recommendations_endpoint(client):
    response = client.post("/v1/brands/hm/recommendations", json={
        "gender": "M", "measurements": {"bust_chest_cm": 104, "waist_cm": 85}})
    assert response.status_code == 200
    results = {r["category_code"]: r for r in response.json()["results"]}
    assert results["M_JACKETS"]["size_label"] == "52"
    assert results["M_SHIRTS"]["status"] == "needs_measurement"


def test_unknown_measurement_is_rejected(client):
    response = client.post("/v1/recommendations", json={
        "gender": "W", "brand_id": "zara", "category_code": "W_TOPS",
        "measurements": {"bust": 88}})
    assert response.status_code == 422


def test_estimate_and_validate_endpoints(client):
    est = client.post("/v1/profile/estimate", json={"gender": "W", "references": [
        {"brand_id": "s_oliver", "category_code": "W_TOPS", "size_label": "38"},
        {"brand_id": "only", "category_code": "W_TOPS", "size_label": "S",
         "fit_verdict": "a_bit_tight"}]}).json()
    assert est["usable"] is True
    val = client.post("/v1/measurements/validate", json={
        "gender": "W", "measurements": {"bust_chest_cm": 80, "underbust_cm": 85}}).json()
    assert val["valid"] is False


def test_falls_back_to_bundled_seed_when_db_is_down(monkeypatch):
    import app.db as db

    def broken():
        raise ConnectionError("database unreachable")

    monkeypatch.setattr(db, "get_engine", broken)
    load_reference_data(app)
    try:
        assert app.state.store_source == "bundled"
        assert "unreachable" in app.state.db_error
        assert len(app.state.store.brands) == 100
    finally:
        monkeypatch.undo()
        load_reference_data(app)
