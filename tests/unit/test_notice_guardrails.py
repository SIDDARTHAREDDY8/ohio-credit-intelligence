"""Unit tests for adverse-action notice guardrails and the fallback notice.

No Claude API or DB needed — these run in CI and lock down the compliance rules.
"""

import pytest

from api.services.claude_service import build_fallback_notice
from api.services.notice_guardrails import (
    expected_citation_numbers,
    is_compliant,
    validate_adverse_action_notice,
)

COMPLIANT_NOTICE = (
    "Thank you for your recent credit application. After reviewing your "
    "application we are unable to approve your request at this time. This "
    "decision was based on the following factors:\n"
    "1. Your debt-to-income ratio of 42.0 weighed against approval.\n"
    "2. Your credit utilization of 0.95 weighed against approval.\n"
    "You have the right to a free copy of any credit report used in this "
    "decision. To improve a future application, reduce your outstanding balances."
)

SHAP_FACTORS = [
    {"feature": "dti", "shap_value": 1.2, "feature_value": 42.0, "direction": "increases_risk"},
    {"feature": "revol_util", "shap_value": 0.9, "feature_value": 0.95, "direction": "increases_risk"},
    {"feature": "fico_mid", "shap_value": 0.7, "feature_value": 570, "direction": "increases_risk"},
    {"feature": "annual_inc", "shap_value": 0.4, "feature_value": 28000, "direction": "increases_risk"},
    {"feature": "loan_amount", "shap_value": -0.2, "feature_value": 35000, "direction": "decreases_risk"},
]


def test_compliant_notice_passes():
    assert validate_adverse_action_notice(COMPLIANT_NOTICE, ["42.0", "0.95"]) == []
    assert is_compliant(COMPLIANT_NOTICE)


@pytest.mark.parametrize(
    "bad,expected_fragment",
    [
        ("", "empty"),
        ("You were **declined** for reason 1. you may reapply.", "banned"),
        ("Declined for reason 1. Reduce balances.", "second person"),
        ("You were declined. Reduce your balances and reapply soon.", "numbered"),
    ],
)
def test_noncompliant_notices_flagged(bad, expected_fragment):
    violations = validate_adverse_action_notice(bad)
    assert any(expected_fragment in v for v in violations), violations


def test_word_limit_enforced():
    long_notice = "You 1. " + ("word " * 250)
    violations = validate_adverse_action_notice(long_notice, max_words=200)
    assert any("too long" in v for v in violations)


def test_missing_citation_flagged_when_expected():
    notice = (
        "Thank you for your application. 1. Your debt level was too high. "
        "You may reduce your balances and reapply."
    )
    violations = validate_adverse_action_notice(notice, expected_numbers=["42.0", "0.95"])
    assert any("specific figures" in v for v in violations)


def test_expected_citation_numbers_from_shap():
    tokens = expected_citation_numbers(SHAP_FACTORS)
    assert "42.0" in tokens
    assert "0.95" in tokens
    assert "28,000" in tokens  # formatted thousands variant


def test_fallback_notice_is_compliant():
    notice = build_fallback_notice(
        applicant={"dti": 42.0}, score=88.0, tier=5, shap_factors=SHAP_FACTORS
    )
    expected = expected_citation_numbers(SHAP_FACTORS)
    violations = validate_adverse_action_notice(notice, expected)
    assert violations == [], violations
    # Cites at least one of the applicant's own figures and is second person.
    assert "your" in notice.lower()
