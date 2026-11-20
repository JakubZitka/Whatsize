"""Import the v3 harvested size graph (data/v3, PRD §8.8 Tier 1).

The CSVs are the source of truth. This module turns them into chart rows
the engine can serve and records every change it makes:

- adjustments: a value was derived or reshaped, with the rule that did it;
- quarantine: a chart (or a second table inside one) was withheld from
  recommendations, with the reason (PRD §11: a chart failing checks is
  quarantined, not published).

Published ranges are kept exactly as published, including gaps between sizes
and overlaps; the engine handles both.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from app.reference.catalog import CATEGORY_BY_CODE, DIMENSIONS

DATA_DIR = Path(__file__).parent / "data" / "v3"

# Measured label drift (PRD §8.6). It relates a garment to its NOMINAL label,
# so it is applied only to charts derived from the standard; a publisher's
# own body chart already encodes the brand's mapping.
CALIBRATION = {
    "Levi's": (7.6, "PRD v1.0 §8.6 — 2022 measured jeans test; re-verify against the "
                    "primary source. Applied to derived_from_standard charts only."),
    "Wrangler": (5.1, "PRD v1.0 §8.6 — measured evidence; re-verify. Applied to "
                      "derived_from_standard charts only."),
    "H&M": (5.1, "PRD v1.0 §8.6 — measured evidence; re-verify. Applied to "
                 "derived_from_standard charts only."),
    "Lee": (2.5, "PRD v1.0 §8.6 — measured evidence; re-verify. Applied to "
                 "derived_from_standard charts only."),
}

PLAUSIBLE = {
    "bust_chest_cm": (30, 200),
    "underbust_cm": (50, 160),
    "waist_cm": (30, 200),
    "hip_cm": (30, 210),
    "neck_cm": (25, 60),
    "stature_cm": (40, 210),
    "inside_leg_cm": (10, 110),
    "sleeve_cm": (20, 110),
    "foot_length_mm": (90, 380),
}
# Half-width given to a secondary dimension published as a single point.
POINT_HALF_WIDTH = {"stature_cm": 3.0, "inside_leg_cm": 1.5, "sleeve_cm": 1.5,
                    "foot_length_mm": 3.0}
DEFAULT_POINT_HALF_WIDTH = 2.0


def _num(value: str) -> float | None:
    value = (value or "").strip().replace(",", ".")
    return float(value) if value else None


def _norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.casefold())


def _primaries(category_code: str) -> list[str]:
    return CATEGORY_BY_CODE[category_code]["primary_dimension"].split("+")


def _read(name: str) -> list[dict]:
    with (DATA_DIR / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _label_stature(label: str) -> tuple[float, float] | None:
    numbers = [int(n) for n in re.findall(r"\d{2,3}", label) if 40 <= int(n) <= 200]
    if len(numbers) == 1:
        return numbers[0] - 3.0, numbers[0] + 3.0
    if len(numbers) == 2 and numbers[0] < numbers[1]:
        return numbers[0] - 3.0, numbers[1] + 3.0
    return None


def _label_neck(label: str) -> tuple[float, float] | None:
    numbers = [int(n) for n in re.findall(r"\d{2}", label) if 34 <= int(n) <= 52]
    if len(numbers) == 1:
        return numbers[0] - 0.5, numbers[0] + 0.5
    if len(numbers) == 2 and numbers[1] == numbers[0] + 1:
        return numbers[0] - 0.5, numbers[1] + 0.5
    return None


def _label_waist(label: str) -> tuple[float, float] | None:
    match = re.fullmatch(r"W?\s*(\d{2})(\s*/.*|\s*L\d+.*)?", label.strip(), re.IGNORECASE)
    if not match or not 22 <= int(match.group(1)) <= 50:
        return None
    n = int(match.group(1))
    return round((n - 0.5) * 2.54, 1), round((n + 0.5) * 2.54, 1)


class _Report:
    def __init__(self):
        self.adjustments: list[dict] = []
        self.quarantine: list[dict] = []

    def adjust(self, brand, row, action, detail):
        self.adjustments.append({
            "brand_id": brand["brand_id"], "brand_name": brand["brand_name"],
            "category_code": row["category_code"], "size_system": row["size_system"],
            "size_label": row["size_label"], "action": action, "detail": detail})

    def withhold(self, brand, category, system, rows, reason):
        self.quarantine.append({
            "brand_id": brand["brand_id"], "brand_name": brand["brand_name"],
            "category_code": category, "size_system": system,
            "sizes": ", ".join(r["size_label"] for r in rows), "rows": len(rows),
            "reason": reason})


def _segments(rows: list[dict]) -> list[list[dict]]:
    """Split a chart where the published size ordinal restarts — two tables
    (e.g. a regular and a plus range) were merged under one key."""
    segments, current, previous = [], [], None
    for row in rows:
        ordinal = int(row["size_ordinal"] or 0)
        if previous is not None and ordinal <= previous:
            segments.append(current)
            current = []
        current.append(row)
        previous = ordinal
    segments.append(current)
    return segments


def _points_to_bands(rows: list[dict], dim: str, brand, report: _Report) -> None:
    """A primary published as single values becomes contiguous bands with
    boundaries at the midpoints between neighbouring sizes."""
    lo_key, hi_key = f"{dim}_min", f"{dim}_max"
    if not any(r[lo_key] == r[hi_key] for r in rows):
        return
    ordered = sorted(rows, key=lambda r: (r[lo_key] + r[hi_key]) / 2)
    centres = [(r[lo_key] + r[hi_key]) / 2 for r in ordered]
    for i, row in enumerate(ordered):
        if row[lo_key] != row[hi_key]:
            continue
        c = centres[i]
        left = (centres[i - 1] + c) / 2 if i > 0 else c - (centres[1] - c) / 2
        right = (c + centres[i + 1]) / 2 if i + 1 < len(centres) else c + (c - centres[-2]) / 2
        row[lo_key], row[hi_key] = round(left, 1), round(right, 1)
        row["band_type"] = "point_to_midpoint"
        report.adjust(brand, row, "point_to_band",
                      f"{dim} published as {c:g}; band set to {row[lo_key]}–{row[hi_key]} "
                      "at the midpoints to neighbouring sizes")


def _clean_segment(brand, category, system, seg, first_segment, report) -> list[dict] | None:
    primaries = _primaries(category)
    kind = CATEGORY_BY_CODE[category]["kind"]
    if any(r["measurement_basis"] == "garment" for r in seg):
        report.withhold(brand, category, system, seg,
                        "Garment measurements, not body measurements: matching them against "
                        "a body would be off by the ease (PRD §8.1 principle 2). Needs an "
                        "ease model or a body chart.")
        return None

    rows = []
    for raw in seg:
        row = dict(raw)
        for dim in DIMENSIONS:
            row[f"{dim}_min"] = _num(raw.get(f"{dim}_min", ""))
            row[f"{dim}_max"] = _num(raw.get(f"{dim}_max", ""))
        # Unit guard: a foot length under 100 "mm" was published in cm.
        if row["foot_length_mm_min"] is not None and row["foot_length_mm_min"] < 100:
            row["foot_length_mm_min"] *= 10
            row["foot_length_mm_max"] *= 10
            report.adjust(brand, row, "unit_fix", "foot length published in cm, converted to mm")
        # Derive a missing primary from the label where the label IS the measure.
        if "stature_cm" in primaries and row["stature_cm_min"] is None:
            band = _label_stature(row["size_label"])
            if band:
                row["stature_cm_min"], row["stature_cm_max"] = band
                row["band_type"] = "label_derived"
                report.adjust(brand, row, "label_derived",
                              f"stature {band[0]:g}–{band[1]:g} cm read from the size label")
        if "neck_cm" in primaries and row["neck_cm_min"] is None and system == "NECK_CM":
            band = _label_neck(row["size_label"])
            if band:
                row["neck_cm_min"], row["neck_cm_max"] = band
                row["band_type"] = "label_derived"
                report.adjust(brand, row, "label_derived",
                              f"neck {band[0]:g}–{band[1]:g} cm read from the collar label")
        if ("waist_cm" in primaries and row["waist_cm_min"] is None and first_segment
                and system in ("WL", "MEN_IN")):
            band = _label_waist(row["size_label"])
            if band:
                row["waist_cm_min"], row["waist_cm_max"] = band
                row["band_type"] = "label_derived"
                report.adjust(brand, row, "label_derived",
                              f"waist {band[0]:g}–{band[1]:g} cm from the inch label")
        rows.append(row)

    required = list(primaries)
    if kind == "bra":
        has_bust = any(r["bust_chest_cm_min"] is not None for r in rows)
        has_underbust = any(r["underbust_cm_min"] is not None for r in rows)
        if has_bust:
            required = ["bust_chest_cm"] + (["underbust_cm"] if has_underbust else [])
        elif has_underbust and system == "ALPHA":
            required = ["underbust_cm"]  # sports bras sized S/M/L by underbust alone
        else:
            report.withhold(brand, category, system, seg,
                            "Band-only table: underbust per band but no cup, so it cannot "
                            "give a bra size.")
            return None
    usable = []
    for row in rows:
        missing = [d for d in required if row[f"{d}_min"] is None or row[f"{d}_max"] is None]
        bad = [d for d in DIMENSIONS
               if row[f"{d}_min"] is not None and row[f"{d}_max"] is not None
               and (row[f"{d}_min"] > row[f"{d}_max"]
                    or row[f"{d}_min"] < PLAUSIBLE[d][0] or row[f"{d}_max"] > PLAUSIBLE[d][1])]
        if missing:
            report.adjust(brand, row, "row_dropped",
                          f"no value for the primary dimension ({', '.join(missing)})")
        elif bad:
            report.adjust(brand, row, "row_dropped", f"implausible or reversed: {', '.join(bad)}")
        else:
            usable.append(row)
    if len(usable) < 2:
        report.withhold(brand, category, system, seg,
                        "Fewer than two sizes carry the primary dimension "
                        f"({' + '.join(required)}); nothing to match against.")
        return None
    labels = [r["size_label"].strip().casefold() for r in usable]
    if len(labels) != len(set(labels)):
        report.withhold(brand, category, system, usable, "Duplicate size labels in one table.")
        return None

    if kind != "bra":
        _points_to_bands(usable, required[0], brand, report)
    for row in usable:
        for dim in DIMENSIONS:
            if dim in required:
                continue
            lo, hi = row[f"{dim}_min"], row[f"{dim}_max"]
            if lo is not None and lo == hi:
                half = POINT_HALF_WIDTH.get(dim, DEFAULT_POINT_HALF_WIDTH)
                row[f"{dim}_min"], row[f"{dim}_max"] = lo - half, hi + half
    return usable


def _second_table_fit(system, primary, rows, seg_min, base_min) -> str | None:
    """Name a further table found inside one chart, or None if its meaning is unclear."""
    if system in ("MEN_EU_SUIT", "EU_TROUSER"):
        # German/Czech suit numbering: 24-31 short series, 88-118 long series.
        try:
            labels = [int(r["size_label"]) for r in rows]
        except ValueError:
            return None
        if max(labels) <= 35:
            return "petite"
        if min(labels) >= 88:
            return "tall"
        return None
    girths = ("bust_chest_cm", "waist_cm", "hip_cm", "underbust_cm")
    if primary in girths and base_min is not None and seg_min > base_min:
        return "plus"
    return None


@lru_cache(maxsize=1)
def load_v3() -> dict:
    report = _Report()
    raw_brands = _read("dim_brand.csv")
    chart_rows = _read("fact_brand_size_chart.csv")
    unknown_cats = {r["category_code"] for r in chart_rows} - set(CATEGORY_BY_CODE)
    if unknown_cats:
        raise ValueError(f"categories missing from catalog: {sorted(unknown_cats)}")

    # One brand per name: keep the harvested record over a derived duplicate.
    by_name: dict[str, dict] = {}
    dropped_brand_ids = set()
    for b in raw_brands:
        key = _norm_name(b["brand_name"])
        keep = by_name.get(key)
        if keep is None:
            by_name[key] = b
            continue
        winner, loser = ((b, keep) if keep["data_source"] != "publisher_size_guide"
                         and b["data_source"] == "publisher_size_guide" else (keep, b))
        by_name[key] = winner
        dropped_brand_ids.add(loser["brand_id"])
        report.quarantine.append({
            "brand_id": loser["brand_id"], "brand_name": loser["brand_name"],
            "category_code": "*", "size_system": "*", "sizes": "", "rows": sum(
                r["brand_id"] == loser["brand_id"] for r in chart_rows),
            "reason": f"Duplicate brand: same brand as {winner['brand_id']} "
                      f"{winner['brand_name']}, which has the harvested chart."})
    brands = {b["brand_id"]: b for b in by_name.values()}

    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in chart_rows:
        if row["brand_id"] in dropped_brand_ids:
            continue
        grouped[(row["brand_id"], row["category_code"], row["size_system"])].append(row)

    out_rows: list[dict] = []
    for (brand_id, category, system), rows in grouped.items():
        if category == "K_ALL" and system.startswith("SHOE_"):
            # Children's shoes filed under children's clothing: keyed by foot length.
            category = "K_SHOES"
            report.adjust({"brand_id": brand_id, "brand_name": brands[brand_id]["brand_name"]},
                          {**rows[0], "category_code": "K_SHOES"}, "reclassified",
                          f"{len(rows)} rows of children's shoes moved from K_ALL to K_SHOES")
        brand = {"brand_id": brand_id, "brand_name": brands[brand_id]["brand_name"]}
        segments = _segments(rows)
        base_min = None
        for index, seg in enumerate(segments):
            cleaned = _clean_segment(brand, category, system, seg, index == 0, report)
            if cleaned is None:
                continue
            primary = _primaries(category)[0]
            if CATEGORY_BY_CODE[category]["kind"] == "bra":
                primary = ("bust_chest_cm" if all(r["bust_chest_cm_min"] is not None
                                                  for r in cleaned) else "underbust_cm")
            seg_min = min(r[f"{primary}_min"] for r in cleaned)
            fit = "regular"
            if index > 0:
                fit = _second_table_fit(system, primary, cleaned, seg_min, base_min)
                if fit is None:
                    report.withhold(brand, category, system, cleaned,
                                    "A further table inside the chart whose meaning is unclear.")
                    continue
                report.adjust(brand, cleaned[0], "table_split",
                              f"further table in the chart ({len(cleaned)} sizes from "
                              f"{cleaned[0]['size_label']}) stored as the {fit} fit")
            else:
                base_min = seg_min
            for row in cleaned:
                out_rows.append({
                    "row_id": len(out_rows) + 1,
                    "source_chart_id": row["size_chart_id"],
                    "brand_id": brand_id,
                    "category_code": category,
                    "fit_code": fit,
                    "size_system": system,
                    "size_label": row["size_label"].strip(),
                    "size_sort": int(row["size_ordinal"] or 0),
                    "measurement_basis": row["measurement_basis"] or "unknown",
                    **{f"{d}_{e}": row[f"{d}_{e}"] for d in DIMENSIONS for e in ("min", "max")},
                    "band_type": row.get("band_type") or "published",
                    "confidence": row["confidence"] or "low",
                    "source_type": row["source_type"],
                    "verification_status": row["verification_status"],
                    "market": row["market"],
                    "publisher_guide_url": row["publisher_guide_url"],
                    "inseam_options_in": "",
                })

    categories_by_brand = defaultdict(set)
    for row in out_rows:
        categories_by_brand[row["brand_id"]].add(row["category_code"])
    out_brands = []
    for b in brands.values():
        offset, source = CALIBRATION.get(b["brand_name"], (0.0, ""))
        out_brands.append({
            "brand_id": b["brand_id"],
            "brand_name": b["brand_name"],
            "parent_group": b["parent_group"],
            "country": b["home_country"],
            "segment": b["segment"],
            "gender_focus": b["gender_focus"],
            "primary_size_system": b["primary_size_system"],
            "cee_presence": b["present_in_cee"],
            "data_source": b["data_source"],
            "brand_confidence": b["confidence"],
            "harvest_status": b["harvest_status"],
            "harvest_note": b["harvest_note"],
            "market_of_chart": b["market_of_chart"],
            "publisher_guide_url": b["size_guide_url"],
            "website": b["size_guide_url"],
            "categories": "|".join(c for c in CATEGORY_BY_CODE
                                   if c in categories_by_brand[b["brand_id"]]),
            "vanity_offset_waist_cm": offset,
            "vanity_offset_source": source,
        })
    out_brands.sort(key=lambda b: b["brand_name"].casefold())
    return {"brands": out_brands, "rows": out_rows, "quarantine": report.quarantine,
            "adjustments": report.adjustments}
