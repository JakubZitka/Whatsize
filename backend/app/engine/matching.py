"""Size matching and recommendation (PRD FR-2.1 – FR-2.7)."""

from __future__ import annotations

from app.engine.store import ChartStore
from app.reference import standards as s
from app.reference.catalog import FIT_BY_CODE

PREFERENCES = ("a_bit_tight", "perfect", "a_bit_loose")
# A preference for a tighter fit lowers the effective girth, so a borderline
# body lands in the smaller size, and vice versa.
PREFERENCE_SHIFT_CM = {"a_bit_tight": -2.0, "perfect": 0.0, "a_bit_loose": 2.0}
PREFERENCE_SHIFT_MM = {"a_bit_tight": -2.0, "perfect": 0.0, "a_bit_loose": 3.0}
GIRTHS = ("bust_chest_cm", "waist_cm", "hip_cm", "neck_cm")
DATA_CONFIDENCE = {"low": 0.5, "medium": 0.7, "high": 0.9}

DIM_NAMES_CS = {
    "bust_chest_cm": {"W": "obvod přes prsa", "M": "obvod hrudníku"},
    "underbust_cm": {"W": "obvod pod prsy", "M": "obvod pod prsy"},
    "waist_cm": {"W": "obvod pasu", "M": "obvod pasu"},
    "hip_cm": {"W": "obvod boků", "M": "obvod boků"},
    "neck_cm": {"W": "obvod krku", "M": "obvod krku"},
    "stature_cm": {"W": "výška", "M": "výška"},
    "foot_length_mm": {"W": "délka chodidla", "M": "délka chodidla"},
}


def dim_name(dim: str, gender: str) -> str:
    return DIM_NAMES_CS[dim].get(gender, DIM_NAMES_CS[dim]["W"])


def unit(dim: str) -> str:
    return "mm" if dim.endswith("_mm") else "cm"


def fmt(x: float) -> str:
    return f"{x:g}"


# --------------------------------------------------------------------------
# Fit recommendation (FR-2.2): fit is orthogonal to size.
# --------------------------------------------------------------------------


def suggest_fit(measurements: dict, gender: str, available: list[str]) -> tuple[str, str] | None:
    """Return (fit_code, reason) for the proportional fit this body suggests."""
    m = measurements
    if gender == "W" and "curvy" in available and m.get("hip_cm") and m.get("waist_cm"):
        if m["hip_cm"] - m["waist_cm"] >= 30:
            return "curvy", (f"Rozdíl boků a pasu {fmt(m['hip_cm'] - m['waist_cm'])} cm "
                             "odpovídá střihu Curvy.")
    if gender == "M" and "athletic" in available and m.get("bust_chest_cm") and m.get("waist_cm"):
        if m["bust_chest_cm"] - m["waist_cm"] >= 18:
            return "athletic", (f"Rozdíl hrudníku a pasu {fmt(m['bust_chest_cm'] - m['waist_cm'])}"
                                " cm odpovídá střihu Athletic.")
    stature = m.get("stature_cm")
    if stature and gender in s.STATURE_BANDS:
        lo, hi = s.STATURE_BANDS[gender]["regular"]
        if stature < lo and "petite" in available:
            return "petite", f"Výška {fmt(stature)} cm je pod výškou běžného střihu."
        if stature >= hi and "tall" in available:
            return "tall", f"Výška {fmt(stature)} cm je nad výškou běžného střihu."
    return None


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _range(row: dict, dim: str) -> tuple[float, float] | None:
    lo, hi = row.get(f"{dim}_min"), row.get(f"{dim}_max")
    if lo is None or hi is None:
        return None
    return float(lo), float(hi)


def _inside(value: float, rng: tuple[float, float]) -> bool:
    return rng[0] <= value < rng[1]


def _margin(rng: tuple[float, float], dim: str) -> float:
    width = rng[1] - rng[0]
    return min(1.5 if dim.endswith("_mm") else 1.0, 0.25 * width)


def _position_factor(value: float, rng: tuple[float, float]) -> float:
    """1.0 at the centre of the band, 0.0 on its edge."""
    half = (rng[1] - rng[0]) / 2
    centre = rng[0] + half
    return max(0.0, 1 - abs(value - centre) / half) if half else 0.0


def _warning(dim: str, value: float, rng: tuple[float, float], gender: str) -> dict | None:
    lo, hi = rng
    if lo <= value < hi:
        return None
    name = dim_name(dim, gender)
    u = unit(dim)
    if dim == "stature_cm":
        direction = "long" if value < lo else "short"
        text = ("může být dlouhé" if value < lo else "může být krátké")
        message = (f"Délka: tvoje {name} {fmt(value)} {u} je mimo výškový rozsah střihu "
                   f"({fmt(lo)}–{fmt(hi)} {u}) — {text}.")
    else:
        direction = "loose" if value < lo else "tight"
        text = "může být volné" if value < lo else "může být těsné"
        message = (f"{name[0].upper() + name[1:]}: {fmt(value)} {u} je mimo rozsah velikosti "
                   f"({fmt(lo)}–{fmt(hi)} {u}) — {text}.")
    return {"dimension": dim, "direction": direction, "message": message}


def _alternatives(store: ChartStore, brand_id: str, category_code: str) -> list[str]:
    segment = store.brands[brand_id].get("segment")
    return [b for b, info in store.brands.items()
            if b != brand_id and info.get("segment") == segment
            and category_code in store.brand_categories(b)][:3]


def _bra_equivalents(row: dict) -> dict:
    ub_lo, ub_hi = _range(row, "underbust_cm")
    band = round((ub_lo + ub_hi) / 2)
    cup_index = round((row["bust_chest_cm_min"] - band - 10) / 2)
    return {system: s.bra_label(band, cup_index, system) for system in s.BRA_SYSTEMS}


def _base_result(store, brand_id, category_code, gender) -> dict:
    return {
        "brand_id": brand_id,
        "brand_name": store.brands.get(brand_id, {}).get("brand_name", brand_id),
        "category_code": category_code,
        "category_name": store.categories.get(category_code, {}).get("name_cs", category_code),
        "gender": gender,
        "status": "ok",
        "fit_code": None,
        "fit_suggestion": None,
        "fits_available": [],
        "size_system": None,
        "size_label": None,
        "runner_up": None,
        "confidence": 0.0,
        "data_confidence": None,
        "explanation": "",
        "warnings": [],
        "notes": [],
        "equivalents": {},
        "missing": [],
        "alternatives": [],
    }


# --------------------------------------------------------------------------
# Core recommendation
# --------------------------------------------------------------------------


def recommend(store: ChartStore, measurements: dict, gender: str, brand_id: str,
              category_code: str, fit_code: str | None = None,
              preference: str = "perfect") -> dict:
    result = _base_result(store, brand_id, category_code, gender)
    if brand_id not in store.brands:
        return {**result, "status": "no_answer", "explanation": "Značku neznáme."}
    if category_code not in store.brand_categories(brand_id):
        return {**result, "status": "no_answer",
                "explanation": "Tuto kategorii značka v našich datech nemá.",
                "alternatives": _alternatives(store, brand_id, category_code)}
    cat = store.categories[category_code]
    primaries = cat["primary_dimension"].split("+")
    secondaries = [d for d in cat["secondary_dimensions"].split("|") if d]
    measurements = {k: float(v) for k, v in measurements.items() if v is not None}

    missing = [d for d in primaries if d not in measurements]
    if missing:
        names = ", ".join(dim_name(d, gender) for d in missing)
        return {**result, "status": "needs_measurement", "missing": missing,
                "explanation": f"Pro tuto kategorii potřebujeme jen: {names}."}

    available = store.fits(brand_id, category_code)
    suggestion = suggest_fit(measurements, gender, available)
    notes = []
    if fit_code and fit_code not in available:
        notes.append(f"Střih {fit_code} tato značka nemá, použili jsme jiný.")
        fit_code = None
    chosen_fit = fit_code or (suggestion[0] if suggestion else "regular")
    if chosen_fit not in available:
        chosen_fit = available[0]
    rows = store.chart(brand_id, category_code, chosen_fit)
    result.update(fit_code=chosen_fit, fits_available=available,
                  fit_suggestion=({"fit_code": suggestion[0], "reason": suggestion[1]}
                                  if suggestion else None))

    # Effective measurements: preference, fit ease and calibrated brand drift.
    if preference not in PREFERENCES:
        preference = "perfect"
    eff = dict(measurements)
    if cat["kind"] != "bra":
        shift = PREFERENCE_SHIFT_CM[preference] + FIT_BY_CODE[chosen_fit]["size_shift_cm"]
        for d in GIRTHS:
            if d in eff:
                eff[d] += shift
        if "foot_length_mm" in eff:
            eff["foot_length_mm"] += PREFERENCE_SHIFT_MM[preference]
    offset = store.vanity_offset(brand_id, category_code)
    if offset:
        for d in ("waist_cm", "hip_cm"):
            if d in eff:
                eff[d] -= offset
        brand_name = store.brands[brand_id]["brand_name"]
        notes.append(f"{brand_name} podle naměřených dat vychází v pase o {fmt(offset)} cm "
                     "větší, než říká štítek — proto doporučujeme menší číslo.")

    if cat["kind"] == "bra":
        winner, runner = _match_bra(rows, eff)
    else:
        winner, runner = _match_scalar(rows, eff, primaries[0], secondaries)

    if winner is None:
        name = dim_name(primaries[0], gender)
        return {**result, "status": "no_answer", "notes": notes,
                "explanation": (f"Tvůj {name} je mimo rozsah velikostí, které značka v této "
                                "kategorii vede. Raději nehádáme."),
                "alternatives": _alternatives(store, brand_id, category_code)}

    warnings = []
    for d in secondaries:
        rng = _range(winner, d)
        if d in eff and rng:
            w = _warning(d, eff[d], rng, gender)
            if w:
                warnings.append(w)

    primary = primaries[0]
    if cat["kind"] == "bra":
        diff = eff["bust_chest_cm"] - eff["underbust_cm"]
        ub_rng = _range(winner, "underbust_cm")
        band = (ub_rng[0] + ub_rng[1]) / 2
        cup_rng = (winner["bust_chest_cm_min"] - band, winner["bust_chest_cm_max"] - band)
        position = min(_position_factor(eff["underbust_cm"], ub_rng),
                       _position_factor(diff, cup_rng))
        explanation = (f"Obvod pod prsy {fmt(measurements['underbust_cm'])} cm určuje obvod "
                       f"a rozdíl přes prsa a pod prsy {fmt(diff)} cm košíček: "
                       f"{winner['size_label']}.")
        result["equivalents"] = _bra_equivalents(winner)
    else:
        rng = _range(winner, primary)
        position = _position_factor(eff[primary], rng)
        explanation = (f"Velikost určuje {dim_name(primary, gender)} "
                       f"{fmt(measurements[primary])} {unit(primary)}, který spadá do rozsahu "
                       f"{fmt(rng[0])}–{fmt(rng[1])} {unit(primary)} velikosti "
                       f"{winner['size_label']}.")
    if runner:
        explanation += f" Jsi blízko hranice — zvaž i velikost {runner['size_label']}."
    if preference != "perfect":
        notes.append("Upraveno podle preference: " +
                     ("spíš těsnější." if preference == "a_bit_tight" else "spíš volnější."))
    if winner["confidence"] != "high":
        notes.append("Tabulka velikostí je zatím odvozená z normy EN 13402-3, ne převzatá od "
                     "značky — přesnost je proto nižší.")

    confidence = DATA_CONFIDENCE.get(winner["confidence"], 0.5)
    confidence *= 0.75 + 0.25 * position
    confidence -= 0.1 * len(warnings)
    if fit_code is None and suggestion is None and chosen_fit != "regular":
        confidence -= 0.05

    result.update(
        size_system=winner["size_system"],
        size_label=winner["size_label"],
        runner_up=runner["size_label"] if runner else None,
        confidence=round(max(0.05, min(confidence, 0.99)), 2),
        data_confidence=winner["confidence"],
        explanation=explanation,
        warnings=warnings,
        notes=notes,
    )
    return result


def _match_scalar(rows, eff, primary, secondaries):
    value = eff[primary]
    i = next((k for k, r in enumerate(rows)
              if _range(r, primary) and _inside(value, _range(r, primary))), None)
    if i is None:
        return None, None
    row, rng = rows[i], _range(rows[i], primary)
    lower = rows[i - 1] if i > 0 else None
    upper = rows[i + 1] if i + 1 < len(rows) else None
    margin = _margin(rng, primary)
    if lower is not None and value == rng[0]:
        # Exactly on a boundary: the upper size wins, the lower is the runner-up.
        return row, lower
    runner = None
    if lower is not None and value - rng[0] < margin:
        runner = lower
    elif upper is not None and rng[1] - value <= margin:
        runner = upper
    if runner is not None:
        # Secondary dimensions break near-ties (FR-2.1 step 2).
        def fits(r):
            return sum(1 for d in secondaries
                       if d in eff and _range(r, d) and _inside(eff[d], _range(r, d)))
        if fits(runner) > fits(row):
            return runner, row
    return row, runner


def _match_bra(rows, eff):
    ub = eff["underbust_cm"]
    diff = eff["bust_chest_cm"] - ub
    best = None
    for row in rows:
        ub_rng = _range(row, "underbust_cm")
        band = (ub_rng[0] + ub_rng[1]) / 2
        cup_rng = (row["bust_chest_cm_min"] - band, row["bust_chest_cm_max"] - band)
        if _inside(ub, ub_rng) and _inside(diff, cup_rng):
            best = (row, band, ub_rng, cup_rng)
            break
    if best is None:
        return None, None
    row, band, ub_rng, cup_rng = best
    runner = None
    for other in rows:
        if other is row:
            continue
        o_ub = _range(other, "underbust_cm")
        o_band = (o_ub[0] + o_ub[1]) / 2
        o_cup = (other["bust_chest_cm_min"] - o_band, other["bust_chest_cm_max"] - o_band)
        same_band = o_band == band
        if same_band and (
            (diff - cup_rng[0] < 0.5 and o_cup[1] == cup_rng[0])
            or (cup_rng[1] - diff <= 0.5 and o_cup[0] == cup_rng[1])
        ):
            runner = other
            break
    return row, runner


def recommend_brand(store: ChartStore, measurements: dict, gender: str, brand_id: str,
                    preference: str = "perfect", include_kids: bool = False) -> list[dict]:
    """Brand-first browsing (FR-3.1): the user's size in every category the brand carries."""
    out = []
    for category_code in store.brand_categories(brand_id):
        cat_gender = store.categories[category_code]["gender"]
        if cat_gender == gender or (include_kids and cat_gender == "K"):
            out.append(recommend(store, measurements, gender, brand_id, category_code,
                                 preference=preference))
    return out
