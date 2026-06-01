from typing import Literal

from pydantic import BaseModel, Field


class ApplicantInput(BaseModel):
    """Loan applicant features submitted to the /score endpoint."""

    loan_amount: float = Field(..., gt=0, le=40000, description="Requested loan amount in dollars")
    term_months: Literal[36, 60] = Field(..., description="Loan term in months")
    annual_income: float = Field(..., gt=0, description="Annual income in dollars")
    dti: float = Field(..., ge=0, le=100, description="Debt-to-income ratio")
    fico_score: int = Field(..., ge=300, le=850, description="FICO credit score")
    emp_length_years: float = Field(..., ge=0, le=40, description="Employment length in years")
    home_ownership: Literal["RENT", "OWN", "MORTGAGE", "OTHER"] = Field(...)
    loan_purpose: str = Field(..., description="Stated purpose of the loan")
    delinq_2yrs: int = Field(..., ge=0, description="Delinquencies in the last 2 years")
    open_accounts: int = Field(..., ge=0, description="Number of open credit accounts")
    revolving_utilization: float = Field(..., ge=0, le=1, description="Revolving utilization rate")

    # Fields with sensible defaults (not required from the caller)
    grade: str = Field(default="C", description="LendingClub loan grade")
    sub_grade: str = Field(default="C3", description="LendingClub loan sub-grade")
    verification_status: str = Field(default="Not Verified")
    int_rate: float = Field(default=12.5, description="Interest rate assigned")
    installment: float = Field(default=0.0, description="Monthly payment amount")
    revol_bal: float = Field(default=10000.0, description="Revolving balance")
    pub_rec: int = Field(default=0, description="Number of public records")
    total_acc: int = Field(default=10, description="Total credit accounts")

    model_config = {
        "json_schema_extra": {
            "example": {
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
        }
    }
