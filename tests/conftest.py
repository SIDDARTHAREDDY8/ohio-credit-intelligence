import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_applicant():
    return {
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
        "grade": "C",
        "sub_grade": "C3",
        "verification_status": "Not Verified",
        "int_rate": 13.5,
        "installment": 503.0,
        "revol_bal": 12000.0,
        "pub_rec": 0,
        "total_acc": 12,
    }


@pytest.fixture
def high_risk_applicant():
    return {
        "loan_amount": 35000,
        "term_months": 60,
        "annual_income": 28000,
        "dti": 45.0,
        "fico_score": 580,
        "emp_length_years": 0,
        "home_ownership": "RENT",
        "loan_purpose": "small_business",
        "delinq_2yrs": 3,
        "open_accounts": 4,
        "revolving_utilization": 0.95,
        "grade": "F",
        "sub_grade": "F4",
        "verification_status": "Not Verified",
        "int_rate": 26.5,
        "installment": 760.0,
        "revol_bal": 28000.0,
        "pub_rec": 2,
        "total_acc": 6,
    }


@pytest.fixture
def low_risk_applicant():
    return {
        "loan_amount": 8000,
        "term_months": 36,
        "annual_income": 120000,
        "dti": 8.0,
        "fico_score": 800,
        "emp_length_years": 10,
        "home_ownership": "MORTGAGE",
        "loan_purpose": "home_improvement",
        "delinq_2yrs": 0,
        "open_accounts": 12,
        "revolving_utilization": 0.10,
        "grade": "A",
        "sub_grade": "A1",
        "verification_status": "Verified",
        "int_rate": 6.5,
        "installment": 245.0,
        "revol_bal": 5000.0,
        "pub_rec": 0,
        "total_acc": 25,
    }
