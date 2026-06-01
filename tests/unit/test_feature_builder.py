"""Unit tests for build_feature_row: column order and engineered features."""

from api.schemas.applicant import ApplicantInput
from api.services.feature_builder import ALL_FEATURES, build_feature_row


def _applicant(**overrides) -> ApplicantInput:
    base = {
        "loan_amount": 15000,
        "term_months": 36,
        "annual_income": 55000,
        "dti": 28.5,
        "fico_score": 680,
        "emp_length_years": 3,
        "home_ownership": "RENT",
        "loan_purpose": "debt_consolidation",
        "delinq_2yrs": 0,
        "open_accounts": 8,
        "revolving_utilization": 0.45,
    }
    base.update(overrides)
    return ApplicantInput(**base)


def test_column_order_matches_all_features():
    df = build_feature_row(_applicant())
    assert list(df.columns) == ALL_FEATURES


def test_single_row_output():
    df = build_feature_row(_applicant())
    assert len(df) == 1


def test_fico_mid_uses_raw_score():
    df = build_feature_row(_applicant(fico_score=720))
    assert df.iloc[0]["fico_mid"] == 720.0


def test_revol_util_scaled_to_percent():
    df = build_feature_row(_applicant(revolving_utilization=0.45))
    assert df.iloc[0]["revol_util"] == 45.0


def test_loan_to_income_ratio():
    df = build_feature_row(_applicant(loan_amount=20000, annual_income=50000))
    assert df.iloc[0]["loan_to_income_ratio"] == 0.4


def test_term_formatted_as_string():
    assert build_feature_row(_applicant(term_months=36)).iloc[0]["term"] == "36 months"
    assert build_feature_row(_applicant(term_months=60)).iloc[0]["term"] == "60 months"


def test_categorical_passthrough():
    df = build_feature_row(
        _applicant(grade="F", sub_grade="F4", home_ownership="MORTGAGE")
    )
    row = df.iloc[0]
    assert row["grade"] == "F"
    assert row["sub_grade"] == "F4"
    assert row["home_ownership"] == "MORTGAGE"
