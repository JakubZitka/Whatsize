from fastapi import APIRouter, HTTPException

from app.api.v1.deps import Store
from app.api.v1.schemas import (
    BrandRecommendationRequest,
    EstimateRequest,
    RecommendationRequest,
    ValidateRequest,
)
from app.engine.estimator import estimate
from app.engine.matching import recommend, recommend_brand
from app.engine.validation import validate

router = APIRouter(tags=["recommendations"])


@router.post("/recommendations")
def recommendation(req: RecommendationRequest, store: Store) -> dict:
    return recommend(store, req.measurements.present(), req.gender, req.brand_id,
                     req.category_code, fit_code=req.fit_code, preference=req.preference)


@router.post("/brands/{brand_id}/recommendations")
def brand_recommendations(brand_id: str, req: BrandRecommendationRequest,
                          store: Store) -> dict:
    if brand_id not in store.brands:
        raise HTTPException(status_code=404, detail="Značku neznáme.")
    results = recommend_brand(store, req.measurements.present(), req.gender, brand_id,
                              preference=req.preference, include_kids=req.include_kids)
    return {"brand_id": brand_id, "brand_name": store.brands[brand_id]["brand_name"],
            "results": results}


@router.post("/profile/estimate")
def profile_estimate(req: EstimateRequest, store: Store) -> dict:
    return estimate(store, req.gender, [r.model_dump() for r in req.references])


@router.post("/measurements/validate")
def measurements_validate(req: ValidateRequest) -> dict:
    return validate(req.measurements.present(), req.gender)
