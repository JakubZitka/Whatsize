from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["recommendations"])


class RecommendationRequest(BaseModel):
    profile_id: str
    brand_id: str
    garment_category: str
    fit_type: str | None = Field(default=None, description="e.g. slim / regular / relaxed")


@router.post("/recommendations")
def recommend(request: RecommendationRequest) -> dict:
    # Matching engine lands here (PRD FR-2.1). Per FR-2.5 the API must refuse
    # rather than guess while no chart data is loaded.
    raise HTTPException(status_code=501, detail="Matching engine not implemented yet")
