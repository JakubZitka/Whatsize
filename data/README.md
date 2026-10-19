# WhatSize sizing data model

`WhatSize_SizingDataModel_v1.xlsx` is the companion workbook to the PRD (§8):
100 brands, their size charts as body-measurement ranges, the dimension
tables, cross-system conversions and the 8 golden test fixtures.

## Provenance

The workbook is **generated**, not hand-edited. Its source of truth is
`backend/app/reference/` — the same code seeds the database, so the
workbook, the database and the engine cannot drift apart.

- Measurement ranges are derived from EN 13402-3 intervals and documented
  regional conversion rules. They are a structurally correct reference grid,
  not transcribed vendor charts. Every chart row is therefore
  `source_type = derived_from_standard`, `confidence = low` (PRD §8.5).
- Brand websites and CEE presence are best-effort and unverified;
  `publisher_guide_url` is empty until researched.
- Vanity offsets are seeded for Levi's, Wrangler, H&M and Lee only (PRD §8.6),
  with sources to re-verify.

| Sheet | Rows | PRD |
|---|---|---|
| dim_brand | 100 | 100 |
| dim_garment_category | 17 | 17 |
| dim_measurement_point | 25 | 25 |
| dim_size_system | 25 | 25 |
| dim_fit_type | 11 | 11 |
| fact_brand_size_chart | 6 980 | 13 697 |
| ref_base_body_table_women / _men | 13 + 12 | 25 |
| ref_conv_* (4 sheets) | 142 | 142 |
| test_fixtures | 8 | 8 |

The chart row count differs from the PRD's original workbook because this
grid is generated per brand size run; it is not padded to match.

## Regenerate

```bash
cd backend
pip install -e ".[dev]"
python scripts/export_workbook.py      # writes data/WhatSize_SizingDataModel_v1.xlsx
```

The export refuses to write if any data-quality check fails (monotonicity,
contiguity, duplicate labels, referential integrity, plausibility bounds,
measurement_basis) — the same checks run in the test suite.

Bumping `DATA_VERSION` in `backend/app/reference/__init__.py` makes every
environment reload the seed on its next start.
