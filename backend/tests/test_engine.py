import pytest

from app.engine.estimator import estimate
from app.engine.matching import recommend, recommend_brand
from app.engine.store import ChartStore
from app.engine.validation import validate
from app.reference.dataset import build_dataset
from app.reference.fixtures import FIXTURES
from app.reference.quality import chart_shape, check_dataset


@pytest.fixture(scope="module")
def store():
    return ChartStore.from_dataset(build_dataset())


def test_dataset_passes_quality_checks():
    assert check_dataset(build_dataset()) == []


def test_v3_import_shape():
    data = build_dataset()
    tables = data["tables"]
    assert len(tables["dim_brand"]) == 111  # 112 in v3 minus the duplicate G-STAR RAW
    rows = tables["fact_brand_size_chart"]
    assert sum(r["source_type"] == "publisher_size_guide" for r in rows) > 2000
    assert all(r["measurement_basis"] in ("body", "unknown") for r in rows)
    reasons = " ".join(q["reason"] for q in tables["import_quarantine"])
    assert "Garment measurements" in reasons and "Duplicate brand" in reasons
    conv = ("ref_conv_women_tops", "ref_conv_men_tops", "ref_conv_footwear", "ref_conv_bra")
    assert sum(len(tables[t]) for t in conv) == 142
    shape = chart_shape(data)
    assert shape["with_gaps"] > 0 and shape["with_overlaps"] > 0


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
    if "note_containing" in exp:
        assert any(exp["note_containing"] in n for n in result["notes"])
    if "no_note_containing" in exp:
        assert not any(exp["no_note_containing"] in n for n in result["notes"])


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


def _synthetic_store(source_type):
    brand = {"brand_id": "X", "brand_name": "X", "segment": "denim",
             "primary_size_system": "WL", "vanity_offset_waist_cm": 7.6}
    rows = []
    for i, n in enumerate(range(26, 34)):
        rows.append({"row_id": i, "brand_id": "X", "category_code": "W_JEANS",
                     "fit_code": "regular", "size_system": "WL", "size_label": str(n),
                     "size_sort": i, "measurement_basis": "body", "confidence": "low",
                     "source_type": source_type, "waist_cm_min": round((n - 0.5) * 2.54, 1),
                     "waist_cm_max": round((n + 0.5) * 2.54, 1)})
    return ChartStore.from_rows("t", [brand], rows)


def test_vanity_offset_only_on_derived_charts():
    body = {"waist_cm": 76.0}
    derived = recommend(_synthetic_store("derived_from_standard"), body, "W", "X", "W_JEANS")
    published = recommend(_synthetic_store("publisher_size_guide"), body, "W", "X", "W_JEANS")
    assert derived["size_label"] == "27"  # 76 - 7.6 = 68.4 cm = 26.9 in
    assert published["size_label"] == "30"  # 76 cm = 29.9 in, offset not applied
    assert any("vychází v pase" in n for n in derived["notes"])
    assert not any("vychází v pase" in n for n in published["notes"])


def test_overlap_picks_nearer_centre(store):
    # Reserved ALPHA W_TOP: S = 84-88, M = 88-93 share 88; a bust of 90.5 is M only.
    result = recommend(store, {"bust_chest_cm": 90.5}, "W", "BR086", "W_TOP")
    assert result["size_label"] == "38"  # primary system EU_DE: 38 = 88-92
    assert result["also"] == {"ALPHA": "M"}


def test_tall_series_suggested_by_stature(store):
    result = recommend(store, {"bust_chest_cm": 100.0, "stature_cm": 192.0}, "M", "BR012",
                       "M_SUIT")
    assert result["fit_code"] == "tall"
    assert result["size_label"] == "102"


def test_childrens_shoes_reclassified(store):
    bata = next(b for b, info in store.brands.items() if info["brand_name"] == "Baťa")
    assert "K_SHOES" in store.brand_categories(bata)
    assert "K_ALL" not in store.brand_categories(bata)
    result = recommend(store, {"foot_length_mm": 180}, "K", bata, "K_SHOES")
    assert result["status"] == "ok"


def test_missing_primary_asks_for_one_number(store):
    result = recommend(store, {"waist_cm": 80}, "W", "BR043", "W_DRESS")
    assert result["status"] == "needs_measurement"
    assert result["missing"] == ["bust_chest_cm"]


def test_out_of_range_refuses_instead_of_guessing(store):
    result = recommend(store, {"bust_chest_cm": 160}, "W", "BR043", "W_TOP")
    assert result["status"] == "no_answer"
    assert result["size_label"] is None


def test_category_not_carried(store):
    result = recommend(store, {"underbust_cm": 75, "bust_chest_cm": 90}, "W", "BR043", "W_BRA")
    assert result["status"] == "no_answer"


def test_fit_preference_moves_borderline_size(store):
    body = {"bust_chest_cm": 89.5}
    perfect = recommend(store, body, "W", "BR043", "W_TOP")
    loose = recommend(store, body, "W", "BR043", "W_TOP", preference="a_bit_loose")
    assert perfect["size_label"] == "38"
    assert loose["size_label"] == "40"


def test_bra_never_inferred_from_torso_data(store):
    result = recommend(store, {"bust_chest_cm": 92}, "W", "BR049", "W_BRA")
    assert result["status"] == "needs_measurement"
    assert "underbust_cm" in result["missing"]


def test_brand_first_lists_every_category_for_gender(store):
    body = {"bust_chest_cm": 88, "waist_cm": 72, "hip_cm": 97, "stature_cm": 168}
    results = recommend_brand(store, body, "W", "BR043")
    cats = [r["category_code"] for r in results]
    assert "W_TOP" in cats and all(c.startswith("W_") for c in cats)
    assert all(r["status"] in ("ok", "needs_measurement") for r in results)


def test_reverse_measurement_needs_two_brands(store):
    refs = [{"brand_id": "BR043", "category_code": "W_TOP", "size_label": "38",
             "fit_verdict": "perfect"}]
    result = estimate(store, "W", refs)
    assert result["usable"] is False
    assert result["guidance"]


def test_declared_market_resolves_foreign_label(store):
    # A French "40" bought abroad equals a German 38 at H&M (US-21).
    refs = [{"brand_id": "BR043", "category_code": "W_TOP", "size_label": "40",
             "size_system": "EU_FR", "fit_verdict": "perfect"},
            {"brand_id": "BR086", "category_code": "W_TOP", "size_label": "S",
             "fit_verdict": "a_bit_tight"}]
    result = estimate(store, "W", refs)
    assert result["problems"] == []
    assert result["dimensions"]["bust_chest_cm"]["value"] == pytest.approx(88, abs=1)


def test_validation_blocks_and_warns():
    assert validate({"bust_chest_cm": 300}, "W")["valid"] is False
    bad = validate({"bust_chest_cm": 80, "underbust_cm": 85}, "W")
    assert bad["valid"] is False
    assert bad["errors"][0]["conflicts_with"] == "underbust_cm"
    leg = validate({"inside_leg_cm": 100, "stature_cm": 160}, "W")
    assert leg["valid"] is False
    odd = validate({"stature_cm": 205}, "W")
    assert odd["valid"] is True and odd["warnings"]
