from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class ShapFactor(BaseModel):
    """A single SHAP feature contribution to the model score."""

    feature: str
    shap_value: float
    feature_value: float | str
    direction: Literal["increases_risk", "decreases_risk"]


class DecisionResponse(BaseModel):
    """Full response returned by the /score endpoint."""

    applicant_id: str
    score: float
    tier: int
    decision: Literal["APPROVE", "REVIEW", "DECLINE"]
    default_probability: float
    top_shap_factors: list[ShapFactor]
    adverse_action_notice: Optional[str] = None
    fairness_flags: list[str] = []
    model_version: str
    scored_at: datetime


class DecisionRecord(BaseModel):
    """A persisted decision row read back from public.decisions."""

    applicant_id: str
    score: float
    tier: int
    decision: str
    default_probability: float
    top_shap_factors: list[ShapFactor]
    adverse_action_notice: Optional[str] = None
    fairness_flags: list[str] = []
    model_version: str
    scored_at: datetime
