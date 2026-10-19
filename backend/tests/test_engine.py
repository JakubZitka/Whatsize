import pytest

from app.engine.estimator import estimate
from app.engine.matching import recommend, recommend_brand
from app.engine.store import ChartStore
from app.engine.validation import validate
from app.reference.dataset import build_dataset
from app.reference.fixtures import FIXTURES
from app.reference.quality import check_dataset


@pytest.fixture(scope="module")
def store():
    return ChartStore.from_dataset(build_dataset())


def test_dataset_passes_quality_checks():
    assert check_dataset(build_dataset()) == []


def test_dataset_shape_matches_prd():
    tables = build_dataset()["tables"]
    assert len(tables["dim_brand"]) == 100
    assert len(tables["dim_garment_category"]) == 17
    assert len(tables["dim_measurement_point"]) == 25
    assert len(tables["dim_size_system"]) == 25
    assert len(tables["dim_fit_type"]) == 11
    assert len(tables["ref_base_body_table_women"]) + len(tables["ref_base_body_table_men"]) == 25
    conv = ("ref_conv_women_tops", "ref_conv_men_tops", "ref_conv_footwear", "ref_conv_bra")
    assert sum(len(tables[t]) for t in conv) == 142
    assert sum(b["ingest_priority"] == "P1" for b in tables["dim_brand"]) == 92
    assert all(r["confidence"] == "low" and r["source_type"] == "derived_from_standard"
               for r in tables["fact_brand_size_chart"])


@pytest.mark.parametrize("fx", [f for f in FIXTURES if f["kind"] == "recommend"],
                         ids=lambda f: f["fixture_id"])
def test_golden_recommendation(store, fx):
    req, exp = fx["request"], fx["expected"]
    result = recommend(store, req["measurements"], req["gender"], req["brand_id"],
                       req["category_code"])
    assert result["status"] == "ok", result
    assert result["size_label"] == exp["size_label"]
    assert result["runner_up"] == exp["runner_up"]
    assert result["fit_code"] == exp["fit_code"]
    if "warnings" in exp:
        assert result["warnings"] == exp["warnings"]
    if "warning_dims" in exp:
        assert [w["dimension"] for w in result["warnings"]] == exp["warning_dims"]
    for system, label in exp.get("equivalents", {}).items():
        assert result["equivalents"][system] == label


def test_golden_reverse_measurement(store):
    fx = next(f for f in FIXTURES if f["fixture_id"] == "TF07")
    exp = fx["expected"]
    result = estimate(store, fx["request"]["gender"], fx["request"]["references"])
    assert result["usable"] is exp["usable"]
    for dim in ("bust_chest_cm", "waist_cm"):
        got = result["dimensions"][dim]
        assert got["value"] == pytest.approx(exp[dim], abs=exp["tolerance_cm"])
        assert got["confidence"] >= exp["min_confidence"]
    assert result["problems"] == []


def test_footwear_us_women_offset_is_per_brand(store):
    # Same foot, two brands: Nike US W = US M + 1.5, Crocs unisex grid = US M + 2.
    nike = recommend(store, {"foot_length_mm": 245}, "W", "nike", "W_FOOTWEAR")
    crocs = recommend(store, {"foot_length_mm": 245}, "W", "crocs", "W_FOOTWEAR")
    assert nike["size_label"] == "8.5"
    assert crocs["size_label"] == "9"


def test_missing_primary_asks_for_one_number(store):
    result = recommend(store, {"waist_cm": 80}, "W", "zara", "W_DRESSES")
    assert result["status"] == "needs_measurement"
    assert result["missing"] == ["bust_chest_cm"]


def test_out_of_range_refuses_instead_of_guessing(store):
    result = recommend(store, {"bust_chest_cm": 150}, "W", "zara", "W_DRESSES")
    assert result["status"] == "no_answer"
    assert result["size_label"] is None


def test_category_not_carried(store):
    result = recommend(store, {"underbust_cm": 75, "bust_chest_cm": 90}, "W", "nike", "W_BRA")
    assert result["status"] == "no_answer"


def test_fit_preference_moves_borderline_size(store):
    body = {"bust_chest_cm": 89.5}
    perfect = recommend(store, body, "W", "s_oliver", "W_TOPS")
    loose = recommend(store, body, "W", "s_oliver", "W_TOPS", preference="a_bit_loose")
    assert perfect["size_label"] == "38"
    assert loose["size_label"] == "40"


def test_bra_never_inferred_from_torso_data(store):
    result = recommend(store, {"bust_chest_cm": 92}, "W", "triumph", "W_BRA")
    assert result["status"] == "needs_measurement"
    assert "underbust_cm" in result["missing"]


def test_brand_first_lists_every_category_for_gender(store):
    body = {"bust_chest_cm": 88, "waist_cm": 72, "hip_cm": 97, "stature_cm": 168}
    results = recommend_brand(store, body, "W", "hm")
    cats = [r["category_code"] for r in results]
    assert "W_TOPS" in cats and "M_TOPS" not in cats
    assert all(r["status"] in ("ok", "needs_measurement") for r in results)


def test_reverse_measurement_needs_two_brands(store):
    refs = [{"brand_id": "zara", "category_code": "W_TOPS", "size_label": "M",
             "fit_verdict": "perfect"}]
    result = estimate(store, "W", refs)
    assert result["usable"] is False
    assert result["guidance"]


def test_declared_market_resolves_foreign_label(store):
    # A French "40" bought abroad equals a German 38 at s.Oliver (US-21).
    refs = [{"brand_id": "s_oliver", "category_code": "W_DRESSES", "size_label": "40",
             "size_system": "EU_FR", "fit_verdict": "perfect"},
            {"brand_id": "only", "category_code": "W_TOPS", "size_label": "S",
             "fit_verdict": "a_bit_tight"}]
    result = estimate(store, "W", refs)
    assert result["problems"] == []
    assert result["dimensions"]["bust_chest_cm"]["value"] == pytest.approx(88, abs=1)


def test_validation_blocks_and_warns():
    assert validate({"bust_chest_cm": 300}, "W")["valid"] is False
    bad = validate({"bust_chest_cm": 80, "underbust_cm": 85}, "W")
    assert bad["valid"] is False
    assert bad["errors"][0]["conflicts_with"] == "underbust_cm"
    odd = validate({"stature_cm": 205}, "W")
    assert odd["valid"] is True and odd["warnings"]
