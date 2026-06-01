"""Decision history endpoint: GET /decisions."""

from fastapi import APIRouter, Query

from api.db.connection import execute_query

router = APIRouter(tags=["decisions"])


@router.get("/decisions")
def list_decisions(limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    """Return the most recent scoring decisions."""
    rows = execute_query(
        """
        SELECT applicant_id, loan_amount, annual_income, dti, fico_score,
               risk_score, risk_tier, decision, top_shap_factors,
               adverse_action_notice, fairness_flags, model_version, created_at
        FROM public.decisions
        ORDER BY created_at DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )
    return rows
