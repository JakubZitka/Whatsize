"""test_fixtures — golden cases chosen to cover failure modes (PRD §8.9).

Expected values were derived by hand from the rules in standards.py, not
copied from engine output, so the regression suite checks the engine
against an independent calculation.
"""

from __future__ import annotations

FIXTURES: list[dict] = [
    {
        "fixture_id": "TF01",
        "title": "Bust exactly on a band boundary",
        "why": "Bands are half-open: a value on the boundary belongs to the upper size; "
               "the lower one is offered as the runner-up (PRD §8.5).",
        "kind": "recommend",
        "request": {"gender": "W", "brand_id": "s_oliver", "category_code": "W_TOPS",
                    "measurements": {"bust_chest_cm": 86.0, "waist_cm": 70.0,
                                     "hip_cm": 95.5, "stature_cm": 167}},
        "expected": {"size_label": "38", "runner_up": "36", "fit_code": "regular"},
    },
    {
        "fixture_id": "TF02",
        "title": "Curvy profile against a brand with a large documented offset",
        "why": "Levi's carries a +7.6 cm waist vanity offset: body waist 76 cm reads as "
               "W27, not the nominal W30. Hip - waist = 30 cm routes to curvy.",
        "kind": "recommend",
        "request": {"gender": "W", "brand_id": "levis", "category_code": "W_JEANS",
                    "measurements": {"waist_cm": 76.0, "hip_cm": 106.0, "stature_cm": 168}},
        "expected": {"size_label": "W27", "runner_up": None, "fit_code": "curvy"},
    },
    {
        "fixture_id": "TF03",
        "title": "Athletic drop",
        "why": "Chest 104 / waist 85 (drop 19 cm): size by chest, athletic fit recommended "
               "so the waist sits in range instead of 5 cm loose.",
        "kind": "recommend",
        "request": {"gender": "M", "brand_id": "hm", "category_code": "M_JACKETS",
                    "measurements": {"bust_chest_cm": 104.0, "waist_cm": 85.0,
                                     "stature_cm": 180}},
        "expected": {"size_label": "52", "runner_up": None, "fit_code": "athletic",
                     "warnings": []},
    },
    {
        "fixture_id": "TF04",
        "title": "Shirt keyed on neck, not chest",
        "why": "Primary dimension of men's shirts is neck (EN 13402-2). Chest 104 alone "
               "would suggest a larger collar; the engine must answer 39 and warn on chest.",
        "kind": "recommend",
        "request": {"gender": "M", "brand_id": "blazek", "category_code": "M_SHIRTS",
                    "measurements": {"neck_cm": 39.0, "bust_chest_cm": 104.0,
                                     "stature_cm": 178}},
        "expected": {"size_label": "39", "runner_up": None, "fit_code": "regular",
                     "warning_dims": ["bust_chest_cm"]},
    },
    {
        "fixture_id": "TF05",
        "title": "Bra where UK and EU cup letters diverge",
        "why": "Underbust 74 / bust 97: cup difference 23 cm = EU F. The same garment is "
               "UK 34E and US 34DDD — 'E' means different volumes in EU and UK.",
        "kind": "recommend",
        "request": {"gender": "W", "brand_id": "hunkemoller", "category_code": "W_BRA",
                    "measurements": {"underbust_cm": 74.0, "bust_chest_cm": 97.0}},
        "expected": {"size_label": "75F", "runner_up": None, "fit_code": "regular",
                     "equivalents": {"BRA_UK": "34E", "BRA_US": "34DDD", "BRA_FR": "90F"}},
    },
    {
        "fixture_id": "TF06",
        "title": "Footwear US men / US women ambiguity",
        "why": "Foot 245 mm = UK 6 = US men 7. Nike's women's scale is US men + 1.5, so "
               "the answer is US W 8.5 — a global +1 rule would wrongly give 8.",
        "kind": "recommend",
        "request": {"gender": "W", "brand_id": "nike", "category_code": "W_FOOTWEAR",
                    "measurements": {"foot_length_mm": 245}},
        "expected": {"size_label": "8.5", "runner_up": None, "fit_code": "regular"},
    },
    {
        "fixture_id": "TF07",
        "title": "Reverse measurement with no direct measurements",
        "why": "Body inferred only from garments that fit. s.Oliver 38 (perfect) and ONLY S "
               "(a bit tight) narrow the bust to about 88 cm; Levi's W27 (perfect) gives the "
               "waist after its +7.6 cm offset. Three brands, so the profile is usable.",
        "kind": "estimate",
        "request": {"gender": "W", "references": [
            {"brand_id": "s_oliver", "category_code": "W_TOPS", "size_label": "38",
             "fit_verdict": "perfect"},
            {"brand_id": "only", "category_code": "W_TOPS", "size_label": "S",
             "fit_verdict": "a_bit_tight"},
            {"brand_id": "levis", "category_code": "W_JEANS", "size_label": "W27",
             "fit_verdict": "perfect"},
        ]},
        "expected": {"bust_chest_cm": 88.0, "waist_cm": 75.8, "tolerance_cm": 1.0,
                     "min_confidence": 0.6, "usable": True},
    },
    {
        "fixture_id": "TF08",
        "title": "Petite: girth and stature disagree",
        "why": "Bust 88 is a DE 38 (UK 12) but stature 153 cm is below the regular block; "
               "with no fit chosen the engine routes to petite and the length fits.",
        "kind": "recommend",
        "request": {"gender": "W", "brand_id": "asos", "category_code": "W_DRESSES",
                    "measurements": {"bust_chest_cm": 88.0, "waist_cm": 72.0, "hip_cm": 97.0,
                                     "stature_cm": 153}},
        "expected": {"size_label": "12", "runner_up": None, "fit_code": "petite",
                     "warnings": []},
    },
]
