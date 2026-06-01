"""End-to-end integration tests against the live app.

These exercise the full stack: MLflow champion model, SHAP, PostgreSQL writes,
and (on DECLINE) the Claude adverse-action notice. They require the local
stack to be up (Docker postgres on 5433, MLflow on 5001, ANTHROPIC_API_KEY in
.env) and are excluded from CI's unit-only run via the `integration` marker.

Run locally with:  pytest tests/integration -m integration -v
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def live_client():
    # Context manager triggers the lifespan so the model loads.
    with TestClient(app) as c:
        yield c


def test_health_reports_model_loaded(live_client):
    body = live_client.get("/health").json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["model_version"] != "unknown"


def test_score_high_risk_declines_with_notice(live_client, high_risk_applicant):
    resp = live_client.post("/score", json=high_risk_applicant)
    assert resp.status_code == 200
    body = resp.json()

    assert body["decision"] == "DECLINE"
    assert body["tier"] in (4, 5)
    assert 0 <= body["score"] <= 100
    assert len(body["top_shap_factors"]) == 5
    assert body["applicant_id"]

    notice = body["adverse_action_notice"]
    assert notice and len(notice) > 0
    # The compliance prompt forbids markdown formatting.
    for sym in ("*", "#", "---", "**"):
        assert sym not in notice


def test_score_low_risk_approves_without_notice(live_client, low_risk_applicant):
    body = live_client.post("/score", json=low_risk_applicant).json()
    assert body["decision"] in ("APPROVE", "REVIEW")
    assert body["adverse_action_notice"] is None


def test_score_response_shape(live_client, sample_applicant):
    body = live_client.post("/score", json=sample_applicant).json()
    for key in (
        "applicant_id", "score", "tier", "decision",
        "default_probability", "top_shap_factors", "model_version", "scored_at",
    ):
        assert key in body
    for f in body["top_shap_factors"]:
        assert f["direction"] in ("increases_risk", "decreases_risk")


def test_score_then_explain_roundtrip(live_client, high_risk_applicant):
    scored = live_client.post("/score", json=high_risk_applicant).json()
    applicant_id = scored["applicant_id"]

    resp = live_client.post("/explain", params={"applicant_id": applicant_id})
    assert resp.status_code == 200
    explained = resp.json()
    assert explained["applicant_id"] == applicant_id
    assert explained["decision"] == scored["decision"]
    assert explained["score"] == scored["score"]


def test_explain_unknown_applicant_404(live_client):
    resp = live_client.post("/explain", params={"applicant_id": "does-not-exist"})
    assert resp.status_code == 404


def test_score_rejects_invalid_payload(live_client):
    resp = live_client.post("/score", json={"loan_amount": -5})
    assert resp.status_code == 422


def test_decisions_endpoint_lists_recent(live_client, sample_applicant):
    live_client.post("/score", json=sample_applicant)
    resp = live_client.get("/decisions", params={"limit": 5})
    assert resp.status_code == 200
    rows = resp.json()
    assert isinstance(rows, list)
    assert len(rows) <= 5
    if rows:
        assert "decision" in rows[0]
        assert "risk_score" in rows[0]


def test_decisions_limit_validation(live_client):
    assert live_client.get("/decisions", params={"limit": 0}).status_code == 422
    assert live_client.get("/decisions", params={"limit": 1000}).status_code == 422


def test_fairness_endpoint(live_client):
    resp = live_client.get("/fairness")
    assert resp.status_code == 200
    rows = resp.json()
    assert isinstance(rows, list)
    if rows:
        assert "race_label" in rows[0]
        assert "approval_rate_pct" in rows[0]


def test_drift_endpoint(live_client):
    resp = live_client.get("/drift")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
