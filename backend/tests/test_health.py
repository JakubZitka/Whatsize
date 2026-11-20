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
    assert body["data_version"] == "v3.0"
    assert body["brands"] == 111
    assert body["chart_rows"] > 3500
    assert body["db_error"] is None


def test_seed_is_idempotent(client):
    from app.db import get_engine
    from app.seed import migrate_and_seed

    assert migrate_and_seed(get_engine()) is False


def test_brands_list_and_filter(client):
    all_brands = client.get("/v1/brands").json()
    names = {b["brand_name"] for b in all_brands}
    assert len(all_brands) == 108  # 111 brands minus 3 whose charts are all quarantined
    assert "CCC" not in names and "Triumph" not in names
    assert "vanity_offset_waist_cm" not in all_brands[0]  # private layer stays private
    women = client.get("/v1/brands", params={"gender": "W", "q": "lev"}).json()
    assert [b["brand_id"] for b in women] == ["BR060"]
    assert women[0]["data_source"] == "publisher_size_guide"


def test_meta_reports_provenance(client):
    meta = client.get("/v1/meta").json()
    assert meta["brands"] == 108
    assert meta["brands_with_publisher_charts"] > 60


def test_brand_detail(client):
    body = client.get("/v1/brands/BR049").json()
    assert "W_BRA" in body["categories"]
    assert "75F" in body["sizes"]["W_BRA"]
    assert body["harvest_note"]
    assert client.get("/v1/brands/nope").status_code == 404


def test_recommendation_endpoint(client):
    response = client.post("/v1/recommendations", json={
        "gender": "W", "brand_id": "BR060", "category_code": "W_JEANS",
        "measurements": {"waist_cm": 76, "hip_cm": 99, "inside_leg_cm": 78}})
    assert response.status_code == 200
    body = response.json()
    assert body["size_label"] == "29"
    assert body["source"]["type"] == "publisher_size_guide"


def test_brand_recommendations_endpoint(client):
    response = client.post("/v1/brands/BR012/recommendations", json={
        "gender": "M", "measurements": {"bust_chest_cm": 104, "waist_cm": 85}})
    assert response.status_code == 200
    results = {r["category_code"]: r for r in response.json()["results"]}
    assert results["M_SUIT"]["size_label"] == "52"
    assert results["M_SHIRT"]["status"] == "needs_measurement"


def test_unknown_measurement_is_rejected(client):
    response = client.post("/v1/recommendations", json={
        "gender": "W", "brand_id": "BR043", "category_code": "W_TOP",
        "measurements": {"bust": 88}})
    assert response.status_code == 422


def test_estimate_and_validate_endpoints(client):
    est = client.post("/v1/profile/estimate", json={"gender": "W", "references": [
        {"brand_id": "BR043", "category_code": "W_TOP", "size_label": "38"},
        {"brand_id": "BR086", "category_code": "W_TOP", "size_label": "S",
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
        assert len(app.state.store.brands) == 111
    finally:
        monkeypatch.undo()
        load_reference_data(app)
