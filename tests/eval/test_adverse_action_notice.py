"""Adverse-action notice evaluation harness.

Generates notices for a set of declined applicant profiles and asserts that
every notice satisfies the ECOA/FCRA compliance guardrails. This is a regression
test for the compliance behaviour of the generation pipeline, not just a single
absence-of-markdown check.

Calls the Claude API, so it is marked ``eval`` and excluded from CI's unit run.
Run locally with:  pytest tests/eval -m eval -v
"""

import pytest

from api.services.claude_service import generate_adverse_action_notice
from api.services.notice_guardrails import (
    expected_citation_numbers,
    validate_adverse_action_notice,
)

pytestmark = pytest.mark.eval


# Declined-applicant fixtures with their model output. Each carries the SHAP
# factors that the notice must explain. Designed to span the decline tiers.
DECLINE_CASES = [
    {
        "name": "high_dti_subprime",
        "applicant": {"dti": 42.0, "fico_score": 570, "annual_income": 28000},
        "score": 88.0,
        "tier": 5,
        "shap_factors": [
            {"feature": "dti", "shap_value": 1.3, "feature_value": 42.0, "direction": "increases_risk"},
            {"feature": "fico_mid", "shap_value": 1.1, "feature_value": 570, "direction": "increases_risk"},
            {"feature": "revol_util", "shap_value": 0.8, "feature_value": 0.95, "direction": "increases_risk"},
            {"feature": "annual_inc", "shap_value": 0.5, "feature_value": 28000, "direction": "increases_risk"},
            {"feature": "delinq_2yrs", "shap_value": 0.4, "feature_value": 4, "direction": "increases_risk"},
        ],
    },
    {
        "name": "thin_file_high_util",
        "applicant": {"dti": 33.0, "fico_score": 640, "annual_income": 41000},
        "score": 68.0,
        "tier": 4,
        "shap_factors": [
            {"feature": "revol_util", "shap_value": 0.9, "feature_value": 0.88, "direction": "increases_risk"},
            {"feature": "open_acc", "shap_value": 0.6, "feature_value": 14, "direction": "increases_risk"},
            {"feature": "fico_mid", "shap_value": 0.5, "feature_value": 640, "direction": "increases_risk"},
            {"feature": "int_rate", "shap_value": 0.4, "feature_value": 22.5, "direction": "increases_risk"},
            {"feature": "annual_inc", "shap_value": -0.2, "feature_value": 41000, "direction": "decreases_risk"},
        ],
    },
    {
        "name": "public_record_borrower",
        "applicant": {"dti": 29.0, "fico_score": 600, "annual_income": 52000},
        "score": 74.0,
        "tier": 4,
        "shap_factors": [
            {"feature": "pub_rec", "shap_value": 1.0, "feature_value": 2, "direction": "increases_risk"},
            {"feature": "fico_mid", "shap_value": 0.7, "feature_value": 600, "direction": "increases_risk"},
            {"feature": "delinq_2yrs", "shap_value": 0.6, "feature_value": 3, "direction": "increases_risk"},
            {"feature": "dti", "shap_value": 0.4, "feature_value": 29.0, "direction": "increases_risk"},
            {"feature": "loan_amount", "shap_value": 0.3, "feature_value": 30000, "direction": "increases_risk"},
        ],
    },
]


@pytest.mark.parametrize("case", DECLINE_CASES, ids=[c["name"] for c in DECLINE_CASES])
def test_generated_notice_is_compliant(case):
    result = generate_adverse_action_notice(
        case["applicant"], case["score"], case["tier"], case["shap_factors"]
    )
    notice = result["notice"]
    assert result["status"] in ("generated", "fallback")

    expected = expected_citation_numbers(case["shap_factors"])
    violations = validate_adverse_action_notice(notice, expected)
    assert violations == [], f"{case['name']} violations: {violations}\n---\n{notice}"


def test_notice_status_reported():
    case = DECLINE_CASES[0]
    result = generate_adverse_action_notice(
        case["applicant"], case["score"], case["tier"], case["shap_factors"]
    )
    assert "notice" in result and "status" in result
