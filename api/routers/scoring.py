"""Scoring endpoints: POST /score and POST /explain."""

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from api.db.connection import execute_query, execute_write
from api.schemas.applicant import ApplicantInput
from api.schemas.decision import DecisionResponse, ShapFactor
from api.security import SCORE_RATE_LIMIT, limiter, require_api_key
from api.services.claude_service import generate_adverse_action_notice
from api.services.model_loader import model_service

logger = logging.getLogger("api.scoring")

# Auth applies to both mutating/expensive routes in this router.
router = APIRouter(tags=["scoring"], dependencies=[Depends(require_api_key)])

INSERT_DECISION = """
    INSERT INTO public.decisions (
        applicant_id, loan_amount, annual_income, dti, fico_score,
        risk_score, risk_tier, decision, top_shap_factors,
        adverse_action_notice, notice_status, fairness_flags, model_version
    ) VALUES (
        :applicant_id, :loan_amount, :annual_income, :dti, :fico_score,
        :risk_score, :risk_tier, :decision, CAST(:top_shap_factors AS JSONB),
        :adverse_action_notice, :notice_status, CAST(:fairness_flags AS JSONB),
        :model_version
    )
    RETURNING created_at
"""


class ExplainRequest(ApplicantInput):
    """/explain accepts the same applicant payload as /score (no DB write)."""


@router.post("/score", response_model=DecisionResponse)
@limiter.limit(SCORE_RATE_LIMIT)
def score_applicant(request: Request, applicant: ApplicantInput) -> DecisionResponse:
    result = model_service.score(applicant)

    decision = result["decision"]
    factors = result["top_shap_factors"]
    notice = None
    notice_status = "not_applicable"
    if decision == "DECLINE":
        generated = generate_adverse_action_notice(
            applicant.model_dump(), result["score"], result["tier"], factors
        )
        notice = generated["notice"]
        notice_status = generated["status"]

    applicant_id = str(uuid.uuid4())
    fairness_flags: list[str] = []

    # Persisting the decision must not break the response. If the write fails we
    # log it and still return the scored result with a best-effort timestamp.
    scored_at = datetime.now(timezone.utc)
    try:
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
                "notice_status": notice_status,
                "fairness_flags": json.dumps(fairness_flags),
                "model_version": result["model_version"],
            },
        )
        if row:
            scored_at = row["created_at"]
    except Exception as exc:  # decision still returned; log for follow-up
        logger.error("Failed to persist decision %s: %s", applicant_id, exc)

    return DecisionResponse(
        applicant_id=applicant_id,
        score=result["score"],
        tier=result["tier"],
        decision=decision,
        default_probability=result["default_probability"],
        top_shap_factors=[ShapFactor(**f) for f in factors],
        adverse_action_notice=notice,
        notice_status=notice_status,
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
