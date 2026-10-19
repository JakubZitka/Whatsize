"""fact_brand_size_chart — brand x category x fit x size label -> body ranges.

Grain: one row per brand, garment category, fit type and size label (PRD §8.3).
Ranges are body measurements (measurement_basis = body), half-open
[min, max) and contiguous along the primary dimension (PRD §8.5).
"""

from __future__ import annotations

from app.reference import standards as s
from app.reference.brands import RUNS
from app.reference.catalog import CATEGORY_BY_CODE

RANGE_COLUMNS = [
    ("bust_chest_cm", "bust_chest_cm_min", "bust_chest_cm_max"),
    ("waist_cm", "waist_cm_min", "waist_cm_max"),
    ("hip_cm", "hip_cm_min", "hip_cm_max"),
    ("underbust_cm", "underbust_cm_min", "underbust_cm_max"),
    ("neck_cm", "neck_cm_min", "neck_cm_max"),
    ("stature_cm", "stature_cm_min", "stature_cm_max"),
    ("foot_length_mm", "foot_length_mm_min", "foot_length_mm_max"),
]


def _rng(lo: float, hi: float) -> tuple[float, float]:
    return (s.r1(lo), s.r1(hi))


def _map_band(points, band):
    lo, hi = band
    return _rng(s.interp(points, lo), s.interp(points, hi))


def _alpha_slice(bands, run):
    first, last = run
    labels = [b[0] for b in bands]
    i, j = labels.index(first), labels.index(last)
    return bands[i:j + 1]


# --------------------------------------------------------------------------
# Size runs per category kind. Each returns [(system, label, sort, {dim: (lo, hi)})].
# --------------------------------------------------------------------------


def _women_numeric(run, system, primary):
    centres_bust = [b for _, b, _, _ in s.WOMEN_BASE]
    bust_bands = s.bands_from_centres(centres_bust)
    waist_bands = s.bands_from_centres([w for _, _, w, _ in s.WOMEN_BASE])
    hip_bands = s.bands_from_centres([h for _, _, _, h in s.WOMEN_BASE])
    lo, hi = run["w_de"]
    out = []
    for i, (de, *_rest) in enumerate(s.WOMEN_BASE):
        if not lo <= de <= hi:
            continue
        dims = {"bust_chest_cm": bust_bands[i], "waist_cm": waist_bands[i],
                "hip_cm": hip_bands[i]}
        if primary == "waist_cm":
            dims.pop("bust_chest_cm")
        label = str(de + s.WOMEN_NUMERIC_OFFSETS[system])
        out.append((system, label, i, dims))
    return out


def _women_alpha(run, primary):
    out = []
    for i, (label, lo, hi) in enumerate(_alpha_slice(s.WOMEN_ALPHA_BUST, run["w_alpha"])):
        dims = {"bust_chest_cm": (lo, hi),
                "waist_cm": _map_band(s.W_BUST_TO_WAIST, (lo, hi)),
                "hip_cm": _map_band(s.W_BUST_TO_HIP, (lo, hi))}
        if primary == "waist_cm":
            dims.pop("bust_chest_cm")
        out.append(("ALPHA", label, i, dims))
    return out


def _wl(lo_in, hi_in, waist_to_hip):
    out = []
    for i, n in enumerate(range(lo_in, hi_in + 1)):
        band = _rng((n - 0.5) * 2.54, (n + 0.5) * 2.54)
        out.append(("WL", f"W{n}", i, {"waist_cm": band, "hip_cm": _map_band(waist_to_hip, band)}))
    # Make the waist bands exactly contiguous after rounding.
    for a, b in zip(out, out[1:], strict=False):
        b[3]["waist_cm"] = (a[3]["waist_cm"][1], b[3]["waist_cm"][1])
    return out


def _men_numeric(run, system, primary):
    chest_bands = s.bands_from_centres([c for _, c, _, _, _ in s.MEN_BASE])
    waist_bands = s.bands_from_centres([w for _, _, w, _, _ in s.MEN_BASE])
    hip_bands = s.bands_from_centres([h for _, _, _, h, _ in s.MEN_BASE])
    lo, hi = run["m_eu"]
    out = []
    for i, (eu, *_rest) in enumerate(s.MEN_BASE):
        if not lo <= eu <= hi:
            continue
        if primary == "waist_cm":
            dims = {"waist_cm": waist_bands[i], "hip_cm": hip_bands[i]}
        else:
            dims = {"bust_chest_cm": chest_bands[i], "waist_cm": waist_bands[i]}
        label = str(eu + s.MEN_NUMERIC_OFFSETS[system])
        out.append((system, label, i, dims))
    return out


def _men_alpha(run, primary):
    out = []
    for i, (label, lo, hi) in enumerate(_alpha_slice(s.MEN_ALPHA_CHEST, run["m_alpha"])):
        waist = _map_band(s.M_CHEST_TO_WAIST, (lo, hi))
        if primary == "waist_cm":
            dims = {"waist_cm": waist, "hip_cm": _map_band(s.M_WAIST_TO_HIP, waist)}
        elif primary == "neck_cm":
            dims = {"neck_cm": _map_band(s.M_CHEST_TO_NECK, (lo, hi)),
                    "bust_chest_cm": (lo, hi)}
        else:
            dims = {"bust_chest_cm": (lo, hi), "waist_cm": waist}
        out.append(("ALPHA", label, i, dims))
    return out


def _men_neck(system):
    out = []
    if system == "NECK_IN":
        values = [x / 2 for x in range(28, 37)]  # 14 … 18 in
        for i, inch in enumerate(values):
            band = _rng((inch - 0.25) * 2.54, (inch + 0.25) * 2.54)
            out.append((system, f"{inch:g}", i, {"neck_cm": band}))
        for a, b in zip(out, out[1:], strict=False):
            b[3]["neck_cm"] = (a[3]["neck_cm"][1], b[3]["neck_cm"][1])
    else:
        for i, n in enumerate(range(37, 47)):
            out.append((system, str(n), i, {"neck_cm": (n - 0.5, n + 0.5)}))
    for row in out:
        row[3]["bust_chest_cm"] = _map_band(s.M_NECK_TO_CHEST, row[3]["neck_cm"])
    return out


def _kids():
    return [("KIDS_HEIGHT", str(h), i, {"stature_cm": (h - 3, h + 3)})
            for i, h in enumerate(s.KIDS_HEIGHTS)]


def _bras(brand):
    system = brand["bra_system"]
    cup_lo, cup_hi = (s.BRA_EU_CUPS.index(c) for c in brand["bra_cups"])
    band_lo, band_hi = brand["bra_bands"]
    out = []
    sort = 0
    for band in s.BRA_EU_BANDS:
        if not band_lo <= band <= band_hi:
            continue
        for ci in range(cup_lo, cup_hi + 1):
            d_lo, d_hi = s.bra_cup_diff(ci)
            out.append((system, s.bra_label(band, ci, system), sort, {
                "underbust_cm": (band - 2.5, band + 2.5),
                "bust_chest_cm": (band + d_lo, band + d_hi),
            }))
            sort += 1
    return out


def _footwear(brand, gender):
    grid = s.footwear_grid(brand["shoe_grid"], gender, brand["shoe_us_w_offset"],
                           brand["shoe_us_uk_offset"])
    centres = [c for _, _, _, c, _ in grid]
    width = grid[0][4]
    edges = [round(c - width / 2, 1) for c in centres] + [round(centres[-1] + width / 2, 1)]
    return [(system, label, sort, {"foot_length_mm": (edges[i], edges[i + 1])})
            for i, (system, label, sort, _, _) in enumerate(grid)]


def size_run(brand: dict, category_code: str):
    cat = CATEGORY_BY_CODE[category_code]
    kind, primary = cat["kind"], cat["primary_dimension"]
    run = RUNS[brand["size_run"]]
    w_sys, m_sys = brand["women_size_system"], brand["men_size_system"]
    if kind == "w_upper":
        if category_code == "W_TOPS" and not brand["tops_numeric"]:
            return _women_alpha(run, primary)
        if w_sys in s.WOMEN_NUMERIC_OFFSETS:
            return _women_numeric(run, w_sys, primary)
        return _women_alpha(run, primary)
    if kind == "w_lower":
        if w_sys in s.WOMEN_NUMERIC_OFFSETS:
            return _women_numeric(run, w_sys, primary)
        return _women_alpha(run, primary)
    if kind == "w_jeans":
        return _wl(*run["w_wl"], s.W_WAIST_TO_HIP)
    if kind == "m_upper":
        if category_code == "M_TOPS" or m_sys not in s.MEN_NUMERIC_OFFSETS:
            return _men_alpha(run, primary)
        return _men_numeric(run, m_sys, primary)
    if kind == "m_shirt":
        if m_sys == "ALPHA":
            return _men_alpha(run, primary)
        return _men_neck(brand["shirt_system"])
    if kind == "m_lower":
        if m_sys in ("UK", "US", "WL"):
            return _wl(*run["m_wl"], s.M_WAIST_TO_HIP)
        if m_sys in s.MEN_NUMERIC_OFFSETS:
            return _men_numeric(run, m_sys, primary)
        return _men_alpha(run, primary)
    if kind == "m_jeans":
        return _wl(*run["m_wl"], s.M_WAIST_TO_HIP)
    if kind == "kids":
        return _kids()
    if kind == "bra":
        return _bras(brand)
    if kind == "foot":
        return _footwear(brand, cat["gender"])
    raise ValueError(kind)


def _apply_fit(dims: dict, fit: str, cat: dict) -> dict:
    dims = dict(dims)
    gender = cat["gender"]
    if gender in ("W", "M") and cat["kind"] not in ("bra", "foot"):
        band = s.STATURE_BANDS[gender].get(fit, s.STATURE_BANDS[gender]["regular"])
        if cat["category_code"] != "W_SKIRTS":
            dims["stature_cm"] = band
    if fit == "curvy" and "hip_cm" in dims:
        lo, hi = dims["hip_cm"]
        dims["hip_cm"] = (s.r1(lo + 5), s.r1(hi + 5))
    if fit == "athletic":
        if cat["primary_dimension"] == "bust_chest_cm" and "waist_cm" in dims:
            lo, hi = dims["waist_cm"]
            dims["waist_cm"] = (s.r1(lo - 6), s.r1(hi - 6))
        elif "hip_cm" in dims:
            lo, hi = dims["hip_cm"]
            dims["hip_cm"] = (s.r1(lo + 4), s.r1(hi + 4))
    return dims


INSEAMS = {"W_JEANS": "30|32|34", "M_JEANS": "30|32|34|36"}


def build_chart_rows(brands: list[dict]) -> list[dict]:
    rows = []
    row_id = 0
    for brand in brands:
        verification = ("pending_manual_capture" if brand["ingest_priority"] == "P3"
                        else "pending_publisher_ingest")
        for category_code in brand["categories"]:
            cat = CATEGORY_BY_CODE[category_code]
            base_run = size_run(brand, category_code)
            for fit in brand["fits"].get(category_code, ["regular"]):
                for system, label, sort, dims in base_run:
                    dims = _apply_fit(dims, fit, cat)
                    row_id += 1
                    row = {
                        "row_id": row_id,
                        "brand_id": brand["brand_id"],
                        "category_code": category_code,
                        "fit_code": fit,
                        "size_system": system,
                        "size_label": label,
                        "size_sort": sort,
                        "measurement_basis": "body",
                    }
                    for dim, c_min, c_max in RANGE_COLUMNS:
                        lo, hi = dims.get(dim, (None, None))
                        row[c_min], row[c_max] = lo, hi
                    row["inseam_options_in"] = INSEAMS.get(category_code, "")
                    row["confidence"] = "low"
                    row["source_type"] = "derived_from_standard"
                    row["verification_status"] = verification
                    row["publisher_guide_url"] = brand["publisher_guide_url"]
                    rows.append(row)
    return rows
