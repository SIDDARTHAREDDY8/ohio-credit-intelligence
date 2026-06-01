"""Unit tests for ApplicantInput pydantic validation (no DB/MLflow needed)."""

import pytest
from pydantic import ValidationError

from api.schemas.applicant import ApplicantInput

VALID = {
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


def test_valid_applicant_parses():
    a = ApplicantInput(**VALID)
    assert a.loan_amount == 15000
    assert a.term_months == 36


def test_defaults_applied():
    a = ApplicantInput(**VALID)
    assert a.grade == "C"
    assert a.sub_grade == "C3"
    assert a.verification_status == "Not Verified"
    assert a.int_rate == 12.5


@pytest.mark.parametrize(
    "field, bad_value",
    [
        ("loan_amount", 0),          # gt=0
        ("loan_amount", 50000),      # le=40000
        ("term_months", 48),         # Literal[36, 60]
        ("annual_income", 0),        # gt=0
        ("dti", -1),                 # ge=0
        ("dti", 150),                # le=100
        ("fico_score", 250),         # ge=300
        ("fico_score", 900),         # le=850
        ("emp_length_years", -1),    # ge=0
        ("emp_length_years", 50),    # le=40
        ("home_ownership", "CONDO"), # not in Literal
        ("revolving_utilization", -0.1),  # ge=0
        ("revolving_utilization", 1.5),   # le=1
        ("delinq_2yrs", -1),         # ge=0
        ("open_accounts", -1),       # ge=0
    ],
)
def test_invalid_values_rejected(field, bad_value):
    payload = {**VALID, field: bad_value}
    with pytest.raises(ValidationError):
        ApplicantInput(**payload)


def test_missing_required_field_rejected():
    payload = {k: v for k, v in VALID.items() if k != "fico_score"}
    with pytest.raises(ValidationError):
        ApplicantInput(**payload)


def test_boundary_values_accepted():
    a = ApplicantInput(
        **{**VALID, "loan_amount": 40000, "dti": 100, "fico_score": 850,
           "revolving_utilization": 1.0, "term_months": 60}
    )
    assert a.loan_amount == 40000
    assert a.term_months == 60
