"""Unit tests for the score-to-tier-decision mapping (no DB/MLflow needed)."""

import pytest

from api.services.model_loader import score_to_tier_decision


@pytest.mark.parametrize(
    "score, expected_tier, expected_decision",
    [
        (0, 1, "APPROVE"),
        (20, 1, "APPROVE"),
        (20.0001, 2, "APPROVE"),
        (21, 2, "APPROVE"),
        (40, 2, "APPROVE"),
        (40.5, 3, "REVIEW"),
        (50, 3, "REVIEW"),
        (60, 3, "REVIEW"),
        (60.1, 4, "DECLINE"),
        (75, 4, "DECLINE"),
        (80, 4, "DECLINE"),
        (80.5, 5, "DECLINE"),
        (95, 5, "DECLINE"),
        (100, 5, "DECLINE"),
    ],
)
def test_tier_and_decision_boundaries(score, expected_tier, expected_decision):
    tier, decision = score_to_tier_decision(score)
    assert tier == expected_tier
    assert decision == expected_decision


def test_only_decline_for_high_tiers():
    for score in (61, 70, 81, 99):
        _, decision = score_to_tier_decision(score)
        assert decision == "DECLINE"


def test_approve_only_for_low_tiers():
    for score in (0, 10, 20, 30, 40):
        _, decision = score_to_tier_decision(score)
        assert decision == "APPROVE"


def test_review_band_is_exclusively_tier_three():
    for score in (41, 50, 60):
        tier, decision = score_to_tier_decision(score)
        assert tier == 3
        assert decision == "REVIEW"
