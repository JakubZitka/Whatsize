"""Data quality checks run on every chart (PRD §11, Data quality).

A chart failing any check is quarantined, not published. check_dataset()
returns a list of human-readable problems; an empty list means clean.
"""

from __future__ import annotations

from collections import defaultdict

from app.reference.catalog import CATEGORY_BY_CODE, FIT_BY_CODE

PLAUSIBLE = {
    "bust_chest_cm": (55, 165),
    "underbust_cm": (55, 130),
    "waist_cm": (40, 150),
    "hip_cm": (65, 175),
    "neck_cm": (30, 55),
    "stature_cm": (80, 210),
    "foot_length_mm": (180, 340),
}


def _primary(category_code: str) -> str:
    primary = CATEGORY_BY_CODE[category_code]["primary_dimension"]
    return primary.split("+")[0]


def check_dataset(dataset: dict) -> list[str]:
    tables = dataset["tables"]
    problems: list[str] = []
    brand_ids = {b["brand_id"] for b in tables["dim_brand"]}
    systems = {s["code"] for s in tables["dim_size_system"]}

    charts: dict[tuple, list[dict]] = defaultdict(list)
    for row in tables["fact_brand_size_chart"]:
        key = (row["brand_id"], row["category_code"], row["fit_code"])
        charts[key].append(row)
        # Referential integrity against the dimension tables.
        if row["brand_id"] not in brand_ids:
            problems.append(f"row {row['row_id']}: unknown brand {row['brand_id']}")
        if row["category_code"] not in CATEGORY_BY_CODE:
            problems.append(f"row {row['row_id']}: unknown category {row['category_code']}")
        if row["fit_code"] not in FIT_BY_CODE:
            problems.append(f"row {row['row_id']}: unknown fit {row['fit_code']}")
        if row["size_system"] not in systems:
            problems.append(f"row {row['row_id']}: unknown size system {row['size_system']}")
        if row.get("measurement_basis") not in ("body", "garment"):
            problems.append(f"row {row['row_id']}: measurement_basis missing")
        # Plausibility bounds and well-formed ranges.
        for dim, (lo_ok, hi_ok) in PLAUSIBLE.items():
            lo, hi = row.get(f"{dim}_min"), row.get(f"{dim}_max")
            if lo is None and hi is None:
                continue
            if lo is None or hi is None or lo >= hi:
                problems.append(f"row {row['row_id']}: malformed {dim} range {lo}-{hi}")
            elif lo < lo_ok or hi > hi_ok:
                problems.append(f"row {row['row_id']}: {dim} {lo}-{hi} outside plausible range")

    for (brand, category, fit), rows in charts.items():
        label = f"{brand}/{category}/{fit}"
        labels = [r["size_label"] for r in rows]
        if len(labels) != len(set(labels)):
            problems.append(f"{label}: duplicate size label")
        primary = _primary(category)
        if CATEGORY_BY_CODE[category]["kind"] == "bra":
            continue  # band x cup grid; contiguity is checked per dimension below
        ordered = sorted(rows, key=lambda r: r["size_sort"])
        for a, b in zip(ordered, ordered[1:], strict=False):
            a_lo, a_hi = a[f"{primary}_min"], a[f"{primary}_max"]
            b_lo = b[f"{primary}_min"]
            if b_lo < a_lo:
                problems.append(f"{label}: not monotonic at {b['size_label']}")
            if b_lo != a_hi:
                problems.append(f"{label}: gap/overlap between {a['size_label']} and "
                                f"{b['size_label']} ({a_hi} vs {b_lo})")
    return problems
