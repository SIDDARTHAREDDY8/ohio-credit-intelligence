"""Scoring endpoints: POST /score and POST /explain."""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from api.db.connection import execute_query, execute_write
from api.schemas.applicant import ApplicantInput
from api.schemas.decision import DecisionResponse, ShapFactor
from api.services.claude_service import generate_adverse_action_notice
from api.services.model_loader import model_service

router = APIRouter(tags=["scoring"])

INSERT_DECISION = """
    INSERT INTO public.decisions (
        applicant_id, loan_amount, annual_income, dti, fico_score,
        risk_score, risk_tier, decision, top_shap_factors,
        adverse_action_notice, fairness_flags, model_version
    ) VALUES (
        :applicant_id, :loan_amount, :annual_income, :dti, :fico_score,
        :risk_score, :risk_tier, :decision, CAST(:top_shap_factors AS JSONB),
        :adverse_action_notice, CAST(:fairness_flags AS JSONB), :model_version
    )
    RETURNING created_at
"""


class ExplainRequest(ApplicantInput):
    """/explain accepts the same applicant payload as /score (no DB write)."""


@router.post("/score", response_model=DecisionResponse)
def score_applicant(applicant: ApplicantInput) -> DecisionResponse:
    result = model_service.score(applicant)

    decision = result["decision"]
    factors = result["top_shap_factors"]
    notice = None
    if decision == "DECLINE":
        notice = generate_adverse_action_notice(
            applicant.model_dump(), result["score"], result["tier"], factors
        )

    applicant_id = str(uuid.uuid4())
    fairness_flags: list[str] = []

    row = execute_write(
        INSERT_DECISION,
        {
            "applicant_id": applicant_id,
            "loan_amount": applicant.loan_amount,
            "annual_income": applicant.annual_income,
            "dti": applicant.dti,
            "fico_score": applicant.fico_score,
            "risk_score": result["score"],
            "risk_tier": result["tier"],
            "decision": decision,
            "top_shap_factors": json.dumps(factors),
            "adverse_action_notice": notice,
            "fairness_flags": json.dumps(fairness_flags),
            "model_version": result["model_version"],
        },
    )
    scored_at = row["created_at"] if row else datetime.now(timezone.utc)

    return DecisionResponse(
        applicant_id=applicant_id,
        score=result["score"],
        tier=result["tier"],
        decision=decision,
        default_probability=result["default_probability"],
        top_shap_factors=[ShapFactor(**f) for f in factors],
        adverse_action_notice=notice,
        fairness_flags=fairness_flags,
        model_version=result["model_version"],
        scored_at=scored_at,
    )


@router.post("/explain")
def explain_decision(applicant_id: str) -> dict:
    """Return the stored SHAP factors and notice for an existing decision."""
    rows = execute_query(
        """
        SELECT applicant_id, risk_score, risk_tier, decision,
               top_shap_factors, adverse_action_notice, model_version, created_at
        FROM public.decisions
        WHERE applicant_id = :applicant_id
        ORDER BY created_at DESC
        LIMIT 1
        """,
        {"applicant_id": applicant_id},
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"No decision for applicant_id {applicant_id}")

    r = rows[0]
    return {
        "applicant_id": r["applicant_id"],
        "score": float(r["risk_score"]),
        "tier": r["risk_tier"],
        "decision": r["decision"],
        "top_shap_factors": r["top_shap_factors"],
        "adverse_action_notice": r["adverse_action_notice"],
        "model_version": r["model_version"],
        "scored_at": r["created_at"],
    }
