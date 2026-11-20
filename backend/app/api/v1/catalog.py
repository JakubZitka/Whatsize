from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.v1.deps import Store
from app.engine.store import ChartStore
from app.reference.catalog import FIT_TYPES, GARMENT_CATEGORIES

router = APIRouter(tags=["catalog"])

# Public brand fields only — calibration (vanity offsets) is the private layer.
BRAND_FIELDS = ("brand_id", "brand_name", "segment", "gender_focus", "country",
                "cee_presence", "data_source", "market_of_chart", "publisher_guide_url")


def _brand_summary(store: ChartStore, brand: dict) -> dict:
    out = {k: brand.get(k) for k in BRAND_FIELDS}
    out["categories"] = store.brand_categories(brand["brand_id"])
    return out


@router.get("/meta")
def meta(request: Request, store: Store) -> dict:
    served = [b for b in store.brands.values() if store.brand_categories(b["brand_id"])]
    published = sum(b.get("data_source") == "publisher_size_guide" for b in served)
    return {
        "data_version": store.version,
        "store_source": getattr(request.app.state, "store_source", None),
        "brands": len(served),
        "brands_with_publisher_charts": published,
        "chart_rows": store.row_count,
        "data_note": (f"{published} značek má tabulku velikostí převzatou od značky, "
                      f"{len(served) - published} zatím odvozenou z normy EN 13402-3."),
    }


@router.get("/categories")
def categories() -> list[dict]:
    keys = ("category_code", "gender", "name_cs", "name_en", "primary_dimension",
            "secondary_dimensions", "silhouette_zone")
    return [{k: c[k] for k in keys} for c in GARMENT_CATEGORIES]


@router.get("/fit-types")
def fit_types() -> list[dict]:
    return [{k: f[k] for k in ("fit_code", "name_cs", "kind", "rule")} for f in FIT_TYPES]


@router.get("/brands")
def brands(
    store: Store,
    gender: Annotated[str | None, Query(pattern="^[WMK]$")] = None,
    q: Annotated[str | None, Query(max_length=64)] = None,
    category: str | None = None,
) -> list[dict]:
    out = []
    needle = (q or "").strip().lower()
    for brand in store.brands.values():
        summary = _brand_summary(store, brand)
        cats = summary["categories"]
        if not cats:
            continue  # every chart of this brand is quarantined
        if gender and not any(c.startswith(gender) for c in cats):
            continue
        if category and category not in cats:
            continue
        if needle and needle not in brand["brand_name"].lower():
            continue
        out.append(summary)
    return sorted(out, key=lambda b: b["brand_name"].lower())


@router.get("/brands/{brand_id}")
def brand_detail(brand_id: str, store: Store) -> dict:
    brand = store.brands.get(brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail="Značku neznáme.")
    out = _brand_summary(store, brand)
    out["harvest_note"] = brand.get("harvest_note")
    out["fits"] = {c: store.fits(brand_id, c) for c in out["categories"]}
    out["sizes"] = {c: [r["size_label"] for r in store.chart(brand_id, c, "regular")]
                    for c in out["categories"]}
    out["systems"] = {c: store.systems(brand_id, c, "regular") for c in out["categories"]}
    return out
