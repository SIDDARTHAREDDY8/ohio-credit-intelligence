"""Monitoring endpoints: GET /fairness and GET /drift."""

from fastapi import APIRouter

from api.db.connection import execute_query

router = APIRouter(tags=["monitoring"])


@router.get("/fairness")
def fairness() -> list[dict]:
    """Approval rates by demographic group from the HMDA bias audit mart."""
    return execute_query(
        """
        SELECT race_label, sex_label, total_applications, approvals, approval_rate_pct
        FROM public.mart_bias_audit
        ORDER BY approval_rate_pct DESC
        """
    )


@router.get("/drift")
def drift() -> list[dict]:
    """Weekly PSI drift scores logged by the drift detector."""
    return execute_query(
        """
        SELECT id, psi_score, status, week_start, logged_at
        FROM public.drift_log
        ORDER BY week_start DESC
        LIMIT 52
        """
    )
