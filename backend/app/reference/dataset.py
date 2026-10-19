"""Assemble every workbook table from the reference modules.

build_dataset() is the single source for both the xlsx workbook
(scripts/export_workbook.py) and the database seed (app.seed).
"""

from __future__ import annotations

from functools import lru_cache

from app.reference import DATA_VERSION
from app.reference import standards as s
from app.reference.brands import build_brands
from app.reference.catalog import (
    FIT_TYPES,
    GARMENT_CATEGORIES,
    MEASUREMENT_POINTS,
    SIZE_SYSTEMS,
)
from app.reference.charts import build_chart_rows
from app.reference.fixtures import FIXTURES


def _base_women():
    return [{"size_de": de, "bust_cm": b, "waist_cm": w, "hip_cm": h,
             "stature_cm": s.WOMEN_REGULAR_STATURE} for de, b, w, h in s.WOMEN_BASE]


def _base_men():
    return [{"size_eu": eu, "chest_cm": c, "waist_cm": w, "hip_cm": h, "neck_cm": n,
             "stature_cm": s.MEN_REGULAR_STATURE} for eu, c, w, h, n in s.MEN_BASE]


def _conv_women():
    rows = []
    for de, bust, waist, hip in s.WOMEN_BASE:
        rows.append({
            "EU_DE": de, "EU_FR": de + 2, "IT": de + 6, "UK": de - 26, "AU": de - 26,
            "US": de - 30, "ALPHA": s.alpha_for(bust, s.WOMEN_ALPHA_BUST) or "",
            "JP_JIS": s.jis_women_label(bust), "CN_GBT": s.gbt_label(160, bust),
            "bust_cm": bust, "waist_cm": waist, "hip_cm": hip,
        })
    return rows


def _conv_men():
    rows = []
    for eu, chest, waist, _hip, neck in s.MEN_BASE:
        rows.append({
            "EU_DE": eu, "IT": eu, "UK": eu - 10, "US": eu - 10,
            "ALPHA": s.alpha_for(chest, s.MEN_ALPHA_CHEST) or "",
            "NECK_CM": round(neck), "NECK_IN": s.neck_in_label(neck),
            "CN_GBT": s.gbt_label(170, chest), "chest_cm": chest, "waist_cm": waist,
            "neck_cm": neck,
        })
    return rows


def _conv_footwear():
    rows = []
    for mm in range(215, 320, 5):
        uk = s.round_half(s.foot_mm_to_uk(mm))
        us_m = uk + 1
        rows.append({
            "foot_length_mm": mm, "SHOE_MONDO": mm, "JP_cm": s.round_half(mm / 10),
            "SHOE_EU": s.round_half(s.foot_mm_to_eu(mm)), "SHOE_UK": uk,
            "SHOE_US_M": us_m, "SHOE_US_W": us_m + 1.5,
            "note": "Generic retail equivalence. Brand charts override US offsets.",
        })
    return rows


def _conv_bra():
    rows = []
    for band in s.BRA_EU_BANDS:
        for ci, cup in enumerate(s.BRA_EU_CUPS):
            d_lo, d_hi = s.bra_cup_diff(ci)
            row = {"eu_band": band, "eu_cup": cup,
                   "underbust_cm_min": band - 2.5, "underbust_cm_max": band + 2.5,
                   "cup_diff_cm_min": d_lo, "cup_diff_cm_max": d_hi}
            for system in s.BRA_SYSTEMS:
                row[system] = s.bra_label(band, ci, system)
            rows.append(row)
    return rows


def _brand_rows(brands):
    keep = ["brand_id", "brand_name", "parent_group", "country", "segment", "gender_focus",
            "women_size_system", "men_size_system", "shirt_system", "bra_system",
            "shoe_grid", "shoe_us_w_offset", "shoe_us_uk_offset", "website", "cee_presence",
            "ingest_priority", "vanity_offset_waist_cm", "vanity_offset_source",
            "publisher_guide_url"]
    out = []
    for b in brands:
        row = {k: b[k] for k in keep}
        row["categories"] = "|".join(b["categories"])
        out.append(row)
    return out


@lru_cache(maxsize=1)
def build_dataset() -> dict:
    brands = build_brands()
    return {
        "version": DATA_VERSION,
        "brands": brands,
        "tables": {
            "dim_brand": _brand_rows(brands),
            "dim_garment_category": GARMENT_CATEGORIES,
            "dim_measurement_point": MEASUREMENT_POINTS,
            "dim_size_system": SIZE_SYSTEMS,
            "dim_fit_type": FIT_TYPES,
            "fact_brand_size_chart": build_chart_rows(brands),
            "ref_base_body_table_women": _base_women(),
            "ref_base_body_table_men": _base_men(),
            "ref_conv_women_tops": _conv_women(),
            "ref_conv_men_tops": _conv_men(),
            "ref_conv_footwear": _conv_footwear(),
            "ref_conv_bra": _conv_bra(),
        },
        "fixtures": FIXTURES,
    }
