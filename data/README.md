# WhatSize sizing data model — v3

| Where | What |
|---|---|
| `backend/app/reference/data/v3/*.csv` | **Source of truth**: brands, categories and size charts as harvested (v3). Shipped inside the API image. |
| `data/v3/harvest_all_v3.json` | Raw values exactly as each brand published them, with the harvest notes — the audit trail. |
| `data/v3/real_charts.json` | The harvested charts normalised per chart, before flattening into the CSV. |
| `data/WhatSize_SizingDataModel_v3.xlsx` | Generated workbook: every table as served, plus the import report. Do not edit by hand. |

## Provenance

- 74 brands have charts taken from their own published size guides
  (`source_type = publisher_size_guide`); the rest are derived from EN 13402-3
  (`derived_from_standard`, `confidence = low`) because their guide could not be
  retrieved — `harvest_note` in `dim_brand` says why, brand by brand.
- `measurement_basis = unknown` means the page does not say whether figures are
  body or garment measurements. Garment-basis charts are **quarantined** (PRD §8.1:
  conflating the two is wrong by a full size).
- Published ranges are kept as published, including gaps between sizes and
  overlaps; the engine handles both.

## Import rules (`backend/app/reference/v3_import.py`)

Every change is listed in the workbook's `import_adjustments` sheet and every
withheld chart in `import_quarantine`, each with its reason:

- A chart whose size ordinal restarts holds two tables: the second becomes the
  **Plus** fit (Sinsay, Takko), or **Tall / Petite** for long and short suit
  series (Blažek); otherwise it is quarantined.
- A missing primary dimension is read from the label only where the label is the
  measurement: height (`98/104`), collar (`39/40`), waist in inches (`W30`).
- Single published values become bands at the midpoints to neighbouring sizes.
- Children's shoes filed under `K_ALL` move to a `K_SHOES` category.
- The derived duplicate `G-STAR RAW` (BR037) is dropped for the harvested
  `G-Star RAW` (BR038).
- Band-only bra tables (no cup) and charts with fewer than two usable sizes are
  quarantined.

Vanity offsets (Levi's, Wrangler, H&M, Lee — PRD §8.6) apply only to charts
derived from the standard: a brand's own body chart already encodes its drift.

## Regenerate the workbook

```bash
cd backend
pip install -e ".[dev]"
python scripts/export_workbook.py      # writes data/WhatSize_SizingDataModel_v3.xlsx
```

The export refuses to write if a data-quality check fails — the same checks run
in the test suite.

## Shipping a new data version

Replace the CSVs in `backend/app/reference/data/v3/` (or add a `v4/` and point
the import at it), bump `DATA_VERSION` in `backend/app/reference/__init__.py`,
run the tests and push. Every environment reloads the seed on its next start.
