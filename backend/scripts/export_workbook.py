"""Render the reference dataset as WhatSize_SizingDataModel_v1.xlsx.

Usage (from backend/):  python scripts/export_workbook.py [output.xlsx]
The workbook is a view of app.reference — edit the generator, not the xlsx.
"""

from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.reference.dataset import build_dataset  # noqa: E402
from app.reference.quality import check_dataset  # noqa: E402

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "data" / "WhatSize_SizingDataModel_v1.xlsx"

FONT = Font(name="Arial", size=10)
BOLD = Font(name="Arial", size=10, bold=True)
HEADER_FONT = Font(name="Arial", size=10, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="35558A")
EDIT_FILL = PatternFill("solid", fgColor="FFF2CC")
TITLE = Font(name="Arial", size=14, bold=True)

# Columns the data team fills in during ingestion (highlighted in yellow).
EDITABLE = {"publisher_guide_url", "verification_status", "confidence", "website",
            "cee_presence"}

DESCRIPTIONS = {
    "dim_brand": "Brand metadata, label systems, footwear grid and US offsets, CEE presence, "
                 "calibrated vanity offset, ingestion priority.",
    "dim_garment_category": "Categories with primary / secondary dimensions per gender "
                            "(EN 13402-2) and silhouette zone.",
    "dim_measurement_point": "Measurement vocabulary (ISO 8559-1 aligned) with how-to and "
                             "self-measurability.",
    "dim_size_system": "Every labelling system with its conversion rule and its traps.",
    "dim_fit_type": "Fit names with girth ease (cm), length delta and engine size shift.",
    "fact_brand_size_chart": "Core table: brand x category x fit x size -> body measurement "
                             "ranges [min, max).",
    "ref_base_body_table_women": "Women's reference grid every chart is compared against.",
    "ref_base_body_table_men": "Men's reference grid every chart is compared against.",
    "ref_conv_women_tops": "Women's cross-system label lookup.",
    "ref_conv_men_tops": "Men's cross-system label lookup.",
    "ref_conv_footwear": "Foot length -> every retail scale, computed directly (never chained).",
    "ref_conv_bra": "Band x cup grid with published retail equivalences per system.",
    "test_fixtures": "Golden regression cases for the matching engine (PRD §8.9).",
}


def _fixture_rows(fixtures):
    rows = []
    for f in fixtures:
        req, exp = f["request"], f["expected"]
        rows.append({
            "fixture_id": f["fixture_id"],
            "title": f["title"],
            "kind": f["kind"],
            "gender": req.get("gender", ""),
            "brand_id": req.get("brand_id", ""),
            "category_code": req.get("category_code", ""),
            "measurements": ", ".join(f"{k}={v}" for k, v in req.get("measurements", {}).items()),
            "reference_garments": "; ".join(
                f"{r['brand_id']} {r['category_code']} {r['size_label']} ({r['fit_verdict']})"
                for r in req.get("references", [])),
            "expected_size": exp.get("size_label", ""),
            "expected_runner_up": exp.get("runner_up") or "",
            "expected_fit": exp.get("fit_code", ""),
            "other_expectations": ", ".join(
                f"{k}={v}" for k, v in exp.items()
                if k not in ("size_label", "runner_up", "fit_code")),
            "why": f["why"],
        })
    return rows


def _cell(value):
    if isinstance(value, bool):
        return "Y" if value else "N"
    if isinstance(value, list | tuple):
        return "|".join(str(v) for v in value)
    return value


def _write_table(ws, rows):
    headers = list(rows[0].keys())
    ws.append(headers)
    for row in rows:
        ws.append([_cell(v) for v in row.values()])
    for cell in ws[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(vertical="center")
    for col_idx, header in enumerate(headers, start=1):
        letter = get_column_letter(col_idx)
        width = max(len(str(header)), *(len(str(r[header] or "")) for r in rows[:300]))
        ws.column_dimensions[letter].width = min(max(width + 2, 8), 60)
        if header in EDITABLE:
            ws.cell(row=1, column=col_idx).fill = PatternFill("solid", fgColor="B8860B")
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = FONT
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions


def build_workbook(out: Path) -> dict:
    dataset = build_dataset()
    problems = check_dataset(dataset)
    if problems:
        raise SystemExit("Data quality checks failed:\n" + "\n".join(problems[:50]))
    tables = dict(dataset["tables"])
    tables["test_fixtures"] = _fixture_rows(dataset["fixtures"])

    wb = Workbook()
    readme = wb.active
    readme.title = "README"
    for name, rows in tables.items():
        _write_table(wb.create_sheet(name), rows)

    lines = [
        ("WhatSize — Sizing Data Model v1", TITLE),
        (f"Data version: {dataset['version']}. Generated from backend/app/reference "
         "(edit the generator, not this file).", FONT),
        ("", FONT),
        ("PROVENANCE — read before using the numbers (PRD §8.5)", BOLD),
        ("Measurement ranges are derived from EN 13402-3 intervals and documented regional "
         "conversion rules. They are a structurally correct reference grid, not scraped "
         "vendor data: no brand chart has been transcribed cell by cell.", FONT),
        ("Every chart row therefore carries source_type = derived_from_standard and "
         "confidence = low. Before launch every P1 brand must be re-ingested from its own "
         "published guide and promoted to confidence = high.", FONT),
        ("Brand websites and CEE presence are best-effort and unverified. Size-guide URLs "
         "(publisher_guide_url) are empty until researched.", FONT),
        ("Vanity offsets are seeded for Levi's, Wrangler, H&M and Lee only (PRD §8.6); "
         "sources must be re-verified against the primary studies.", FONT),
        ("", FONT),
        ("CONVENTIONS", BOLD),
        ("Bands are half-open: min inclusive, max exclusive, boundary at the midpoint "
         "between consecutive sizes. All lengths in cm except foot length (mm).", FONT),
        ("Body measurements are the canonical truth; size labels are derived views. There is "
         "no 'eu_size' column — size_system names the scale (EU_DE vs EU_FR …).", FONT),
        ("Header cells in dark gold mark columns the data team fills in during ingestion "
         "(e.g. publisher_guide_url, verification_status, confidence).", FONT),
        ("", FONT),
        ("SHEETS", BOLD),
    ]
    for text, font in lines:
        readme.append([text])
        readme.cell(row=readme.max_row, column=1).font = font
    header_row = readme.max_row + 1
    readme.append(["Sheet", "Rows", "Contents"])
    for cell in readme[header_row]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
    for name in tables:
        readme.append([name, f"=COUNTA('{name}'!A:A)-1", DESCRIPTIONS[name]])
        for cell in readme[readme.max_row]:
            cell.font = FONT
    readme.column_dimensions["A"].width = 30
    readme.column_dimensions["B"].width = 10
    readme.column_dimensions["C"].width = 100
    for row in readme.iter_rows(max_row=header_row - 1):
        row[0].alignment = Alignment(wrap_text=False)

    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return {name: len(rows) for name, rows in tables.items()}


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    counts = build_workbook(target)
    for name, n in counts.items():
        print(f"{name:28s} {n}")
    print(f"written: {target}")
