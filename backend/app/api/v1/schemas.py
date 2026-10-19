from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Gender = Literal["W", "M"]
Preference = Literal["a_bit_tight", "perfect", "a_bit_loose"]


class Measurements(BaseModel):
    """Body measurements. Storage is always metric; display units are a client concern."""

    model_config = ConfigDict(extra="forbid")

    stature_cm: float | None = Field(default=None, description="Height")
    bust_chest_cm: float | None = Field(default=None, description="Bust (W) or chest (M) girth")
    underbust_cm: float | None = None
    waist_cm: float | None = None
    hip_cm: float | None = None
    neck_cm: float | None = None
    foot_length_mm: float | None = None

    def present(self) -> dict:
        return self.model_dump(exclude_none=True)


class RecommendationRequest(BaseModel):
    gender: Gender
    brand_id: str
    category_code: str
    measurements: Measurements
    fit_code: str | None = None
    preference: Preference = "perfect"


class BrandRecommendationRequest(BaseModel):
    gender: Gender
    measurements: Measurements
    preference: Preference = "perfect"
    include_kids: bool = False


class ReferenceGarment(BaseModel):
    brand_id: str
    category_code: str
    size_label: str
    fit_verdict: Preference = "perfect"
    fit_code: str | None = None
    size_system: str | None = Field(
        default=None, description="Declared market of the label, e.g. EU_FR (US-21)")


class EstimateRequest(BaseModel):
    gender: Gender
    references: list[ReferenceGarment] = Field(min_length=1, max_length=12)


class ValidateRequest(BaseModel):
    gender: Gender
    measurements: Measurements
