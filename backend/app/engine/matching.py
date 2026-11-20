"""Size matching and recommendation (PRD FR-2.1 – FR-2.7).

Publisher charts are used as published: sizes can leave gaps between them or
overlap. A body in a gap gets the nearer size with the other as runner-up; a
body in an overlap gets the size whose centre it is closer to.
"""

from __future__ import annotations

import re

from app.engine.store import ChartStore
from app.reference import standards as s
from app.reference.catalog import FIT_BY_CODE, LENGTH_DIMENSIONS

PREFERENCES = ("a_bit_tight", "perfect", "a_bit_loose")
# A preference for a tighter fit lowers the effective girth, so a borderline
# body lands in the smaller size, and vice versa.
PREFERENCE_SHIFT_CM = {"a_bit_tight": -2.0, "perfect": 0.0, "a_bit_loose": 2.0}
PREFERENCE_SHIFT_MM = {"a_bit_tight": -2.0, "perfect": 0.0, "a_bit_loose": 3.0}
GIRTHS = ("bust_chest_cm", "waist_cm", "hip_cm", "neck_cm")
DATA_CONFIDENCE = {"low": 0.5, "medium": 0.7, "high": 0.9}

DIM_NAMES_CS = {
    "bust_chest_cm": {"W": "obvod přes prsa", "M": "obvod hrudníku", "K": "obvod hrudníku"},
    "underbust_cm": {"W": "obvod pod prsy"},
    "waist_cm": {"W": "obvod pasu"},
    "hip_cm": {"W": "obvod boků"},
    "neck_cm": {"W": "obvod krku"},
    "stature_cm": {"W": "výška"},
    "inside_leg_cm": {"W": "vnitřní délka nohy"},
    "sleeve_cm": {"W": "délka rukávu"},
    "foot_length_mm": {"W": "délka chodidla"},
}


def dim_name(dim: str, gender: str) -> str:
    return DIM_NAMES_CS[dim].get(gender, DIM_NAMES_CS[dim]["W"])


def unit(dim: str) -> str:
    return "mm" if dim.endswith("_mm") else "cm"


def fmt(x: float) -> str:
    return f"{round(x, 1):g}"


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
            return "petite", f"Výška {fmt(stature)} cm je pod výškou běžné řady."
        if stature >= hi and "tall" in available:
            return "tall", f"Výška {fmt(stature)} cm je nad výškou běžné řady."
    return None


# --------------------------------------------------------------------------
# Range helpers
# --------------------------------------------------------------------------


def _range(row: dict, dim: str) -> tuple[float, float] | None:
    lo, hi = row.get(f"{dim}_min"), row.get(f"{dim}_max")
    if lo is None or hi is None:
        return None
    return float(lo), float(hi)


def _inside(value: float, rng: tuple[float, float]) -> bool:
    return rng[0] <= value <= rng[1]


def _centre(rng: tuple[float, float]) -> float:
    return (rng[0] + rng[1]) / 2


def _width(rng: tuple[float, float]) -> float:
    return max(rng[1] - rng[0], 0.1)


def _margin(rng: tuple[float, float], dim: str) -> float:
    return min(1.5 if dim.endswith("_mm") else 1.0, 0.25 * _width(rng))


def _position_factor(value: float, rng: tuple[float, float]) -> float:
    """1.0 at the centre of the band, 0.0 on or beyond its edge."""
    half = _width(rng) / 2
    return max(0.0, 1 - abs(value - _centre(rng)) / half)


def _distance(value: float, rng: tuple[float, float]) -> float:
    """0 inside the band, else the distance to it in band widths."""
    if _inside(value, rng):
        return 0.0
    edge = rng[0] if value < rng[0] else rng[1]
    return abs(value - edge) / _width(rng)


def _warning(dim: str, value: float, rng: tuple[float, float], gender: str) -> dict | None:
    lo, hi = rng
    if lo <= value <= hi:
        return None
    name = dim_name(dim, gender)
    u = unit(dim)
    if dim in LENGTH_DIMENSIONS:
        direction = "long" if value < lo else "short"
        text = "může být dlouhé" if value < lo else "může být krátké"
        message = (f"Délka: tvoje {name} {fmt(value)} {u} je mimo rozsah velikosti "
                   f"({fmt(lo)}–{fmt(hi)} {u}) — {text}.")
    else:
        direction = "loose" if value < lo else "tight"
        text = "může být volné" if value < lo else "může být těsné"
        message = (f"{name[0].upper() + name[1:]}: {fmt(value)} {u} je mimo rozsah velikosti "
                   f"({fmt(lo)}–{fmt(hi)} {u}) — {text}.")
    return {"dimension": dim, "direction": direction, "message": message}


def _secondary_fits(row: dict, eff: dict, secondaries: list[str]) -> int:
    return sum(1 for d in secondaries
               if d in eff and _range(row, d) and _inside(eff[d], _range(row, d)))


# --------------------------------------------------------------------------
# Matching on one chart
# --------------------------------------------------------------------------


def _match_scalar(rows: list[dict], eff: dict, dim: str, secondaries: list[str]):
    """Return (winner, runner_up, flag) with flag in {None, 'boundary', 'overlap', 'gap'}."""
    value = eff[dim]
    ordered = sorted((r for r in rows if _range(r, dim)), key=lambda r: _centre(_range(r, dim)))
    if not ordered:
        return None, None, None
    if value < min(_range(r, dim)[0] for r in ordered) or \
            value > max(_range(r, dim)[1] for r in ordered):
        return None, None, None

    containing = [r for r in ordered if _inside(value, _range(r, dim))]
    if len(containing) >= 2:
        starts = [r for r in containing if _range(r, dim)[0] == value]
        ends = [r for r in containing if _range(r, dim)[1] == value]
        if starts and ends:
            # On a shared boundary the upper size wins, the lower is the runner-up (§8.5).
            return starts[0], ends[-1], "boundary"
        containing.sort(key=lambda r: abs(value - _centre(_range(r, dim))) / _width(_range(r, dim)))
        return containing[0], containing[1], "overlap"

    if len(containing) == 1:
        row = containing[0]
        rng = _range(row, dim)
        i = ordered.index(row)
        lower = ordered[i - 1] if i > 0 else None
        upper = ordered[i + 1] if i + 1 < len(ordered) else None
        margin = _margin(rng, dim)
        runner = None
        if lower is not None and value - rng[0] < margin:
            runner = lower
        elif upper is not None and rng[1] - value <= margin:
            runner = upper
        if runner is not None and \
                _secondary_fits(runner, eff, secondaries) > _secondary_fits(row, eff, secondaries):
            return runner, row, None  # secondary dimensions break near-ties (FR-2.1)
        return row, runner, None

    # In a gap the chart leaves between two published sizes.
    lower = max((r for r in ordered if _range(r, dim)[1] < value), key=lambda r: _range(r, dim)[1])
    upper = min((r for r in ordered if _range(r, dim)[0] > value), key=lambda r: _range(r, dim)[0])
    d_low = value - _range(lower, dim)[1]
    d_up = _range(upper, dim)[0] - value
    winner, runner = (upper, lower) if d_up <= d_low else (lower, upper)
    if _secondary_fits(runner, eff, secondaries) > _secondary_fits(winner, eff, secondaries):
        winner, runner = runner, winner
    return winner, runner, "gap"


def _match_grid(rows: list[dict], eff: dict, dims: list[str]):
    """Bras: band (underbust) and cup (bust) together, as the brand publishes them."""
    usable = [r for r in rows if all(_range(r, d) for d in dims)]
    for d in dims:
        if not usable or eff[d] < min(_range(r, d)[0] for r in usable) - 1 or \
                eff[d] > max(_range(r, d)[1] for r in usable) + 1:
            return None, None, None

    def score(r):
        outside = sum(_distance(eff[d], _range(r, d)) for d in dims)
        centre = sum(abs(eff[d] - _centre(_range(r, d))) / _width(_range(r, d)) for d in dims)
        return outside, centre

    ranked = sorted(usable, key=score)
    best, second = ranked[0], ranked[1] if len(ranked) > 1 else None
    outside = score(best)[0]
    if outside > 1.0:
        return None, None, None
    flag = "gap" if outside > 0 else None
    runner = second if second is not None and score(second)[0] <= 0.5 else None
    return best, runner, flag


_BRA_LABEL = re.compile(r"^\s*(\d{2,3})\s*([A-K]{1,3})\s*$", re.IGNORECASE)


def _bra_equivalents(row: dict) -> dict:
    """Render a bra size in every system from its EU/UK label (FR-2.7: the cup
    letter is presentation; published retail equivalences, not arithmetic)."""
    match = _BRA_LABEL.match(row["size_label"])
    if not match:
        return {}
    band, cup = int(match.group(1)), match.group(2).upper()
    if row["size_system"] == "BRA_EU" and cup in s.BRA_EU_CUPS and 60 <= band <= 95:
        eu_band, cup_index = band, s.BRA_EU_CUPS.index(cup)
    elif row["size_system"] == "BRA_UK" and cup in s.BRA_UK_CUPS and 28 <= band <= 42:
        eu_band, cup_index = 60 + (band - 28) // 2 * 5, s.BRA_UK_CUPS.index(cup)
    else:
        return {}
    return {system: s.bra_label(eu_band, cup_index, system) for system in s.BRA_SYSTEMS}


def _required_dims(cat: dict, rows: list[dict]) -> list[str]:
    if cat["kind"] == "bra":
        return [d for d in ("underbust_cm", "bust_chest_cm") if any(_range(r, d) for r in rows)]
    return [cat["primary_dimension"]]


def _match_chart(rows, cat, eff, secondaries):
    required = _required_dims(cat, rows)
    if len(required) == 2:
        return _match_grid(rows, eff, required)
    return _match_scalar(rows, eff, required[0], secondaries)


# --------------------------------------------------------------------------
# Result assembly
# --------------------------------------------------------------------------


def _alternatives(store: ChartStore, brand_id: str, category_code: str) -> list[str]:
    segment = store.brands[brand_id].get("segment")
    return [b for b, info in store.brands.items()
            if b != brand_id and info.get("segment") == segment
            and category_code in store.brand_categories(b)][:3]


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
        "also": {},
        "confidence": 0.0,
        "data_confidence": None,
        "source": None,
        "explanation": "",
        "warnings": [],
        "notes": [],
        "equivalents": {},
        "missing": [],
        "alternatives": [],
    }


def _effective(measurements, cat, fit, preference, offset):
    eff = dict(measurements)
    if cat["kind"] != "bra":
        shift = PREFERENCE_SHIFT_CM[preference] + FIT_BY_CODE[fit]["size_shift_cm"]
        for d in GIRTHS:
            if d in eff:
                eff[d] += shift
        if "foot_length_mm" in eff:
            eff["foot_length_mm"] += PREFERENCE_SHIFT_MM[preference]
    if offset:
        for d in ("waist_cm", "hip_cm"):
            if d in eff:
                eff[d] -= offset
    return eff


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
    if preference not in PREFERENCES:
        preference = "perfect"
    cat = store.categories[category_code]
    secondaries = [d for d in cat["secondary_dimensions"].split("|") if d]
    measurements = {k: float(v) for k, v in measurements.items() if v is not None}

    available = store.fits(brand_id, category_code)
    suggestion = suggest_fit(measurements, gender, available)
    notes = []
    if fit_code and fit_code not in available:
        notes.append(f"Řadu {fit_code} tato značka nemá, použili jsme jinou.")
        fit_code = None
    chosen = fit_code or (suggestion[0] if suggestion else "regular")
    if chosen not in available:
        chosen = available[0]

    attempt = _recommend_fit(store, brand_id, category_code, cat, chosen, measurements, gender,
                             preference, secondaries)
    # Above the regular range of a brand with a plus range: answer from the plus range.
    if attempt["status"] == "no_answer" and attempt.get("above") and "plus" in available \
            and chosen == "regular" and not fit_code:
        plus = _recommend_fit(store, brand_id, category_code, cat, "plus", measurements, gender,
                              preference, secondaries)
        if plus["status"] == "ok":
            attempt, chosen = plus, "plus"
            notes.append("Míra je nad běžnou řadou značky, použili jsme řadu Plus.")
    attempt.pop("above", None)

    result.update(attempt)
    result.update(fit_code=chosen, fits_available=available,
                  fit_suggestion=({"fit_code": suggestion[0], "reason": suggestion[1]}
                                  if suggestion else None),
                  notes=notes + attempt.get("notes", []))
    if result["status"] == "no_answer":
        result["alternatives"] = _alternatives(store, brand_id, category_code)
    return result


def _recommend_fit(store, brand_id, category_code, cat, fit, measurements, gender, preference,
                   secondaries) -> dict:
    systems = store.systems(brand_id, category_code, fit)
    results = [_recommend_chart(store, brand_id, category_code, cat, fit, system, measurements,
                                gender, preference, secondaries) for system in systems]
    main = next((r for r in results if r["status"] == "ok"), results[0])
    main["also"] = {r["size_system"]: r["size_label"] for r in results
                    if r is not main and r["status"] == "ok"
                    and r["size_label"] != main["size_label"]}
    return main


def _recommend_chart(store, brand_id, category_code, cat, fit, system, measurements, gender,
                     preference, secondaries) -> dict:
    rows = store.chart(brand_id, category_code, fit, system)
    required = _required_dims(cat, rows)
    missing = [d for d in required if d not in measurements]
    if missing:
        names = ", ".join(dim_name(d, gender) for d in missing)
        return {"status": "needs_measurement", "missing": missing, "size_system": system,
                "explanation": f"Pro tuto kategorii potřebujeme jen: {names}."}

    offset = store.vanity_offset(brand_id, category_code, rows)
    eff = _effective(measurements, cat, fit, preference, offset)
    notes = []
    if offset:
        notes.append(f"{store.brands[brand_id]['brand_name']} podle naměřených dat vychází "
                     f"v pase o {fmt(offset)} cm větší, než říká štítek — proto doporučujeme "
                     "menší číslo.")

    winner, runner, flag = _match_chart(rows, cat, eff, secondaries)
    primary = required[-1] if cat["kind"] == "bra" else required[0]
    if winner is None:
        ranges = [_range(r, primary) for r in rows if _range(r, primary)]
        above = bool(ranges) and eff[primary] > max(hi for _lo, hi in ranges)
        name = dim_name(primary, gender)
        return {"status": "no_answer", "size_system": system, "above": above, "notes": notes,
                "explanation": (f"Tvoje míra ({name}) je mimo rozsah velikostí, které značka "
                                "v této kategorii vede. Raději nehádáme.")}

    warnings = []
    for d in secondaries:
        rng = _range(winner, d)
        if d in eff and d not in required and rng:
            w = _warning(d, eff[d], rng, gender)
            if w:
                warnings.append(w)

    if len(required) == 2:
        position = min(_position_factor(eff[d], _range(winner, d)) for d in required)
        diff = measurements["bust_chest_cm"] - measurements["underbust_cm"]
        explanation = (f"Obvod pod prsy {fmt(measurements['underbust_cm'])} cm a přes prsa "
                       f"{fmt(measurements['bust_chest_cm'])} cm (rozdíl {fmt(diff)} cm) "
                       f"odpovídají velikosti {winner['size_label']}.")
    else:
        rng = _range(winner, primary)
        position = _position_factor(eff[primary], rng)
        explanation = (f"Velikost určuje {dim_name(primary, gender)} "
                       f"{fmt(measurements[primary])} {unit(primary)}; velikost "
                       f"{winner['size_label']} pokrývá {fmt(rng[0])}–{fmt(rng[1])} "
                       f"{unit(primary)}.")
    if runner is not None:
        explanation += f" Jsi blízko hranice — zvaž i velikost {runner['size_label']}."
    if flag == "gap":
        notes.append("Tvoje míra padá mezi dvě velikosti, které značka uvádí — vybrali jsme "
                     "bližší.")
    elif flag == "overlap":
        notes.append("Velikosti se v tabulce značky překrývají — vybrali jsme tu, do jejíhož "
                     "středu padneš blíž.")
    if preference != "perfect":
        notes.append("Upraveno podle preference: " +
                     ("spíš těsnější." if preference == "a_bit_tight" else "spíš volnější."))
    if winner["source_type"] == "derived_from_standard":
        notes.append("Tabulka velikostí je zatím odvozená z normy EN 13402-3, ne převzatá od "
                     "značky — přesnost je proto nižší.")
    elif winner.get("measurement_basis") == "unknown":
        notes.append("Značka neuvádí, zda jde o míry těla, nebo oblečení.")

    confidence = DATA_CONFIDENCE.get(winner["confidence"], 0.5)
    confidence *= 0.75 + 0.25 * position
    if winner.get("measurement_basis") == "unknown":
        confidence *= 0.9
    confidence -= {"gap": 0.15, "overlap": 0.05}.get(flag, 0.0)
    confidence -= 0.1 * len(warnings)

    return {
        "status": "ok",
        "size_system": system,
        "size_label": winner["size_label"],
        "runner_up": runner["size_label"] if runner else None,
        "confidence": round(max(0.05, min(confidence, 0.99)), 2),
        "data_confidence": winner["confidence"],
        "source": {"type": winner["source_type"], "market": winner.get("market") or None,
                   "url": winner.get("publisher_guide_url") or None},
        "explanation": explanation,
        "warnings": warnings,
        "notes": notes,
        "equivalents": _bra_equivalents(winner) if cat["kind"] == "bra" else {},
    }


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
