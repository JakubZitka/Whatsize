"""Data quality checks on the published size graph (PRD §11, Data quality).

Hard failures (returned by check_dataset) must never reach recommendations:
referential integrity, measurement basis, primary dimension present, ranges
well-formed and plausible, no duplicate label in one chart. Charts that fail
on import are quarantined by v3_import before they get here.

Gaps and overlaps between consecutive sizes are allowed — publishers' charts
contain both and the engine handles them — and are reported by chart_shape().
"""

from __future__ import annotations

from collections import defaultdict

from app.reference.catalog import CATEGORY_BY_CODE, DIMENSIONS, FIT_BY_CODE
from app.reference.v3_import import PLAUSIBLE


def _charts(rows):
    charts = defaultdict(list)
    for row in rows:
        charts[(row["brand_id"], row["category_code"], row["fit_code"], row["size_system"])] \
            .append(row)
    return charts


def check_dataset(dataset: dict) -> list[str]:
    tables = dataset["tables"]
    problems: list[str] = []
    brand_ids = {b["brand_id"] for b in tables["dim_brand"]}
    systems = {s["code"] for s in tables["dim_size_system"]}
    for row in tables["fact_brand_size_chart"]:
        rid = row["row_id"]
        if row["brand_id"] not in brand_ids:
            problems.append(f"row {rid}: unknown brand {row['brand_id']}")
        if row["category_code"] not in CATEGORY_BY_CODE:
            problems.append(f"row {rid}: unknown category {row['category_code']}")
            continue
        if row["fit_code"] not in FIT_BY_CODE:
            problems.append(f"row {rid}: unknown fit {row['fit_code']}")
        if row["size_system"] not in systems:
            problems.append(f"row {rid}: unknown size system {row['size_system']}")
        if row.get("measurement_basis") not in ("body", "unknown"):
            problems.append(f"row {rid}: measurement_basis {row.get('measurement_basis')!r} "
                            "may not be served (garment charts are quarantined)")
        for dim in DIMENSIONS:
            lo, hi = row.get(f"{dim}_min"), row.get(f"{dim}_max")
            if lo is None and hi is None:
                continue
            if lo is None or hi is None or lo > hi:
                problems.append(f"row {rid}: malformed {dim} range {lo}-{hi}")
            elif lo < PLAUSIBLE[dim][0] or hi > PLAUSIBLE[dim][1]:
                problems.append(f"row {rid}: {dim} {lo}-{hi} outside plausible range")
        cat = CATEGORY_BY_CODE[row["category_code"]]
        primaries = cat["primary_dimension"].split("+")
        if cat["kind"] == "bra":
            if row.get("bust_chest_cm_min") is None and row.get("underbust_cm_min") is None:
                problems.append(f"row {rid}: bra row without underbust or bust")
        elif row.get(f"{primaries[0]}_min") is None:
            problems.append(f"row {rid}: primary {primaries[0]} missing")

    for key, rows in _charts(tables["fact_brand_size_chart"]).items():
        labels = [r["size_label"].casefold() for r in rows]
        if len(labels) != len(set(labels)):
            problems.append(f"{'/'.join(key)}: duplicate size label")
        if len(rows) < 2:
            problems.append(f"{'/'.join(key)}: fewer than two sizes")
    return problems


def chart_shape(dataset: dict) -> dict:
    """Count charts whose consecutive sizes leave gaps or overlap (informational)."""
    shape = {"charts": 0, "with_gaps": 0, "with_overlaps": 0}
    for (_b, category, _f, _s), rows in _charts(dataset["tables"]["fact_brand_size_chart"]).items():
        cat = CATEGORY_BY_CODE[category]
        shape["charts"] += 1
        if cat["kind"] == "bra":
            continue
        dim = cat["primary_dimension"]
        ordered = sorted(rows, key=lambda r: (r[f"{dim}_min"] + r[f"{dim}_max"]) / 2)
        pairs = list(zip(ordered, ordered[1:], strict=False))
        if any(b[f"{dim}_min"] > a[f"{dim}_max"] for a, b in pairs):
            shape["with_gaps"] += 1
        if any(b[f"{dim}_min"] < a[f"{dim}_max"] for a, b in pairs):
            shape["with_overlaps"] += 1
    return shape
