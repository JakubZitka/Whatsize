"""test_fixtures — golden cases chosen to cover failure modes (PRD §8.9).

Built on the v3 harvested charts. Expected values were worked out by hand
from the chart rows quoted in each case, not copied from engine output, so
the regression suite checks the engine against an independent calculation.
"""

from __future__ import annotations

FIXTURES: list[dict] = [
    {
        "fixture_id": "TF01",
        "title": "Bust exactly on a shared band boundary",
        "why": "H&M W_TOP: 36 = bust 82–86, 38 = 86–90. A bust of 86 sits on the shared "
               "boundary: the upper size wins and the lower is the runner-up (PRD §8.5).",
        "kind": "recommend",
        "request": {"gender": "W", "brand_id": "BR043", "category_code": "W_TOP",
                    "measurements": {"bust_chest_cm": 86.0, "waist_cm": 70.0, "hip_cm": 95.0}},
        "expected": {"size_label": "38", "runner_up": "36", "fit_code": "regular"},
    },
    {
        "fixture_id": "TF02",
        "title": "Measured brand offset is not applied twice",
        "why": "Levi's carries a +7.6 cm measured waist offset, but its W_JEANS chart is the "
               "brand's own body chart (W29 = waist 75.5–78), which already encodes the label "
               "drift. Waist 76 must read W29 — applying the offset again would give W26. "
               "76 is within 0.6 cm of the W28 boundary, so W28 is the runner-up.",
        "kind": "recommend",
        "request": {"gender": "W", "brand_id": "BR060", "category_code": "W_JEANS",
                    "measurements": {"waist_cm": 76.0, "hip_cm": 99.0}},
        "expected": {"size_label": "29", "runner_up": "28", "fit_code": "regular",
                     "no_note_containing": "vychází v pase"},
    },
    {
        "fixture_id": "TF03",
        "title": "Body in a gap the publisher leaves between sizes",
        "why": "KiK M_TOP publishes 62 = chest 122–126 and 64 = 129–131. Chest 127 is in "
               "neither: the nearer size (62, 1 cm away) wins, 64 is the runner-up, and the "
               "answer says the measurement falls between two published sizes.",
        "kind": "recommend",
        "request": {"gender": "M", "brand_id": "BR054", "category_code": "M_TOP",
                    "measurements": {"bust_chest_cm": 127.0}},
        "expected": {"size_label": "62", "runner_up": "64", "fit_code": "regular",
                     "note_containing": "mezi dvě velikosti"},
    },
    {
        "fixture_id": "TF04",
        "title": "Shirt keyed on neck, not chest",
        "why": "Primary dimension of men's shirts is neck (EN 13402-2). Blažek collar 39 = "
               "neck 38.5–39.5 with chest 94–98; a chest of 104 must not change the collar, "
               "only raise a warning.",
        "kind": "recommend",
        "request": {"gender": "M", "brand_id": "BR012", "category_code": "M_SHIRT",
                    "measurements": {"neck_cm": 39.0, "bust_chest_cm": 104.0}},
        "expected": {"size_label": "39", "runner_up": None, "fit_code": "regular",
                     "warning_dims": ["bust_chest_cm"]},
    },
    {
        "fixture_id": "TF05",
        "title": "Bra where UK and EU cup letters diverge",
        "why": "Hunkemöller 75F = underbust 73–77, bust 99–101. Underbust 74 / bust 100 is "
               "75F; the same size is UK 34E and US 34DDD — 'E' means different volumes in "
               "EU and UK. Neighbouring cups are 0.75 band-widths away: no runner-up.",
        "kind": "recommend",
        "request": {"gender": "W", "brand_id": "BR049", "category_code": "W_BRA",
                    "measurements": {"underbust_cm": 74.0, "bust_chest_cm": 100.0}},
        "expected": {"size_label": "75F", "runner_up": None, "fit_code": "regular",
                     "equivalents": {"BRA_UK": "34E", "BRA_US": "34DDD", "BRA_FR": "90F"}},
    },
    {
        "fixture_id": "TF06",
        "title": "Footwear on the brand's own third-size grid",
        "why": "adidas grids men's shoes in thirds: 42 2/3 = foot 261–265 mm. A 263 mm foot "
               "is that size, centred — a label that exists on no generic EU table, which is "
               "why charts are kept on each brand's native grid (FR-2.6).",
        "kind": "recommend",
        "request": {"gender": "M", "brand_id": "BR110", "category_code": "M_SHOES",
                    "measurements": {"foot_length_mm": 263}},
        "expected": {"size_label": "42 2/3", "runner_up": None, "fit_code": "regular"},
    },
    {
        "fixture_id": "TF07",
        "title": "Reverse measurement with no direct measurements",
        "why": "H&M 38 (perfect) gives bust 87–89; Reserved S (bust 84–88, a bit tight) gives "
               "86–89: bust ≈ 88. Levi's 27 (waist 70.5–73, perfect) gives 71.1–72.4, clipped "
               "by the tops' waist ranges to ≈ 71.6. No offset: Levi's chart is the brand's "
               "own. Three brands, so the profile is usable.",
        "kind": "estimate",
        "request": {"gender": "W", "references": [
            {"brand_id": "BR043", "category_code": "W_TOP", "size_label": "38",
             "fit_verdict": "perfect"},
            {"brand_id": "BR086", "category_code": "W_TOP", "size_label": "S",
             "fit_verdict": "a_bit_tight"},
            {"brand_id": "BR060", "category_code": "W_JEANS", "size_label": "27",
             "fit_verdict": "perfect"},
        ]},
        "expected": {"bust_chest_cm": 88.0, "waist_cm": 71.6, "tolerance_cm": 1.0,
                     "min_confidence": 0.6, "usable": True},
    },
    {
        "fixture_id": "TF08",
        "title": "Above the regular range: the plus range answers",
        "why": "Sinsay's regular W_TOP ends at XXL (bust 107–113); its plus table continues "
               "with 1XL = 115–122. Bust 118 is above the regular range, so the engine "
               "answers 1XL from the plus range instead of refusing.",
        "kind": "recommend",
        "request": {"gender": "W", "brand_id": "BR092", "category_code": "W_TOP",
                    "measurements": {"bust_chest_cm": 118.0, "waist_cm": 100.0,
                                     "stature_cm": 170.0}},
        "expected": {"size_label": "1XL", "runner_up": None, "fit_code": "plus",
                     "warnings": []},
    },
]
