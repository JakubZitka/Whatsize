"""Reverse measurement (PRD FR-1.1): infer a body from garments that fit.

Each reference garment narrows the plausible interval of every dimension its
chart row covers. The fit verdict moves the interval inside the size band;
secondary dimensions contribute a deliberately wide interval. Per dimension
the estimator returns a central value, an interval and a confidence (0-1).
"""

from __future__ import annotations

from collections import defaultdict

from app.engine.matching import dim_name
from app.engine.store import ChartStore
from app.reference import standards as s

CONFIDENCE_THRESHOLD = 0.6  # PRD FR-1.1 — a starting point, to be tuned in P0 (§14.1)
VERDICTS = ("a_bit_tight", "perfect", "a_bit_loose")
SECONDARY_SLACK = {"cm": 2.0, "mm": 3.0}


def _verdict_interval(lo: float, hi: float, verdict: str) -> tuple[float, float]:
    w = hi - lo
    if verdict == "a_bit_tight":  # the body sits high in the band, or just above it
        return lo + w / 2, hi + w / 4
    if verdict == "a_bit_loose":  # the body sits low in the band, or just below it
        return lo - w / 4, lo + w / 2
    return lo + w / 4, hi - w / 4


def _confidence(width: float, dim: str) -> float:
    if dim.endswith("_mm"):
        width /= 2.5
    for limit, conf in ((2, 0.9), (4, 0.75), (6, 0.6), (8, 0.45)):
        if width <= limit:
            return conf
    return 0.3


def _resolve_label(store: ChartStore, ref: dict, rows: list[dict]) -> dict | None:
    """Find the chart row for a reference label, resolving a declared market (US-21)."""
    label = str(ref["size_label"]).strip().upper()
    declared = ref.get("size_system")
    brand_system = rows[0]["size_system"] if rows else None
    if not declared or declared == brand_system:
        return next((r for r in rows if r["size_label"].upper() == label), None)
    gender = store.categories[ref["category_code"]]["gender"]
    to_de = s.women_label_to_de if gender == "W" else s.men_label_to_de
    offsets = s.WOMEN_NUMERIC_OFFSETS if gender == "W" else s.MEN_NUMERIC_OFFSETS
    de = to_de(label, declared)
    if de is None or brand_system not in offsets:
        return None
    target = str(de + offsets[brand_system])
    return next((r for r in rows if r["size_label"] == target), None)


def estimate(store: ChartStore, gender: str, references: list[dict]) -> dict:
    intervals: dict[str, list[tuple[float, float, str, bool]]] = defaultdict(list)
    problems = []
    brands_used = set()
    for ref in references:
        brand_id, category_code = ref["brand_id"], ref["category_code"]
        verdict = ref.get("fit_verdict", "perfect")
        if verdict not in VERDICTS:
            verdict = "perfect"
        fit = ref.get("fit_code") or "regular"
        rows = store.chart(brand_id, category_code, fit)
        row = _resolve_label(store, ref, rows) if rows else None
        if row is None:
            problems.append(f"{brand_id} {category_code} {ref['size_label']}: velikost neznáme.")
            continue
        brands_used.add(brand_id)
        cat = store.categories[category_code]
        primaries = cat["primary_dimension"].split("+")
        offset = store.vanity_offset(brand_id, category_code)
        for dim in ("bust_chest_cm", "underbust_cm", "waist_cm", "hip_cm", "neck_cm",
                    "foot_length_mm"):
            lo, hi = row.get(f"{dim}_min"), row.get(f"{dim}_max")
            if lo is None:
                continue
            # A garment that runs large fits a larger body than its label says.
            if offset and dim in ("waist_cm", "hip_cm"):
                lo, hi = lo + offset, hi + offset
            if dim in primaries:
                a, b = _verdict_interval(lo, hi, verdict)
                intervals[dim].append((a, b, brand_id, True))
            elif cat["kind"] != "bra":
                slack = SECONDARY_SLACK["mm" if dim.endswith("_mm") else "cm"]
                intervals[dim].append((lo - slack, hi + slack, brand_id, False))

    dimensions = {}
    for dim, items in intervals.items():
        lo = max(i[0] for i in items)
        hi = min(i[1] for i in items)
        conflict = lo > hi
        if conflict:
            primaries_only = [i for i in items if i[3]] or items
            lo = max(i[0] for i in primaries_only)
            hi = min(i[1] for i in primaries_only)
            if lo > hi:
                centres = sorted((i[0] + i[1]) / 2 for i in primaries_only)
                mid = centres[len(centres) // 2]
                lo, hi = mid - 2, mid + 2
        conf = 0.3 if conflict else _confidence(hi - lo, dim)
        if len({i[2] for i in items}) < 2:
            # One brand's block cannot be told apart from the body inside it.
            conf = min(conf, 0.5)
        if not any(i[3] for i in items):
            conf = min(conf, 0.45)
        dimensions[dim] = {
            "value": round((lo + hi) / 2, 1),
            "min": round(lo, 1),
            "max": round(hi, 1),
            "confidence": round(conf, 2),
            "conflict": conflict,
            "sources": sorted({i[2] for i in items}),
        }

    confident = [d for d, v in dimensions.items() if v["confidence"] >= CONFIDENCE_THRESHOLD]
    usable = len(brands_used) >= 2 and bool(confident)
    guidance = []
    if len(brands_used) < 2:
        guidance.append("Přidej kousek od jiné značky — jedna značka nestačí, její střih se "
                        "nedá odlišit od postavy.")
    upper = dimensions.get("bust_chest_cm", {}).get("confidence", 0) >= CONFIDENCE_THRESHOLD
    lower = dimensions.get("waist_cm", {}).get("confidence", 0) >= CONFIDENCE_THRESHOLD
    if upper and not lower:
        guidance.append("Horní polovinu těla už určíme. Přidej kalhoty nebo džíny, které ti "
                        "sedí, a určíme i nohy.")
    elif lower and not upper:
        guidance.append("Spodní polovinu těla už určíme. Přidej tričko nebo bundu, které ti "
                        "sedí, a určíme i horní polovinu.")
    for dim, v in dimensions.items():
        if v["conflict"]:
            guidance.append(f"Kousky si odporují v rozměru {dim_name(dim, gender)} — "
                            "zkontroluj, že všechny opravdu dobře sedí.")
    return {
        "gender": gender,
        "dimensions": dimensions,
        "measurements": {d: v["value"] for d, v in dimensions.items()
                         if v["confidence"] >= CONFIDENCE_THRESHOLD},
        "brands_used": sorted(brands_used),
        "usable": usable,
        "threshold": CONFIDENCE_THRESHOLD,
        "guidance": guidance,
        "problems": problems,
    }
