"""Generate 1000 synthetic Ohio loan applicants with Faker.

Produces realistic-looking but entirely fake applicants used for tests and
the API demo. No real customer data is involved. Writes both a CSV snapshot
(data/synthetic/applicants.csv) and raw.synthetic_applicants in PostgreSQL.
"""

import os
import uuid

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from faker import Faker
from sqlalchemy import create_engine

load_dotenv()

N_APPLICANTS = 1000
CSV_OUT = "data/synthetic/applicants.csv"
SEED = 42

GRADES = ["A", "B", "C", "D", "E", "F", "G"]
HOME_OWNERSHIP = ["RENT", "MORTGAGE", "OWN"]
HOME_WEIGHTS = [0.50, 0.35, 0.15]
PURPOSES = [
    "debt_consolidation",
    "credit_card",
    "home_improvement",
    "major_purchase",
    "medical",
    "car",
    "other",
]
PURPOSE_WEIGHTS = [0.45, 0.25, 0.10, 0.06, 0.05, 0.05, 0.04]
VERIFICATION = ["Verified", "Source Verified", "Not Verified"]
# Base interest rate by grade (annual %)
GRADE_RATE = {"A": 6.5, "B": 9.5, "C": 13.5, "D": 17.0, "E": 20.5, "F": 24.0, "G": 27.5}


def fico_to_grade(fico: int) -> str:
    """Map a FICO score to a LendingClub-style letter grade."""
    if fico >= 760:
        return "A"
    if fico >= 720:
        return "B"
    if fico >= 690:
        return "C"
    if fico >= 660:
        return "D"
    if fico >= 630:
        return "E"
    if fico >= 600:
        return "F"
    return "G"


def monthly_installment(principal: float, annual_rate_pct: float, term_months: int) -> float:
    """Standard amortized monthly payment."""
    r = (annual_rate_pct / 100) / 12
    if r == 0:
        return round(principal / term_months, 2)
    payment = principal * r * (1 + r) ** term_months / ((1 + r) ** term_months - 1)
    return round(payment, 2)


def generate() -> pd.DataFrame:
    Faker.seed(SEED)
    rng = np.random.default_rng(SEED)

    rows = []
    for _ in range(N_APPLICANTS):
        annual_income = float(np.clip(rng.normal(70000, 20000), 30000, 120000))
        loan_amount = float(rng.uniform(5000, 35000))
        fico_score = int(np.clip(round(rng.triangular(580, 680, 780)), 580, 780))
        dti = round(float(rng.uniform(8.0, 45.0)), 2)
        emp_length_years = int(rng.integers(0, 16))
        home_ownership = str(rng.choice(HOME_OWNERSHIP, p=HOME_WEIGHTS))
        loan_purpose = str(rng.choice(PURPOSES, p=PURPOSE_WEIGHTS))
        term_months = int(rng.choice([36, 60], p=[0.7, 0.3]))

        grade = fico_to_grade(fico_score)
        sub_grade = f"{grade}{int(rng.integers(1, 6))}"
        int_rate = round(GRADE_RATE[grade] + float(rng.normal(0, 1.0)), 2)
        installment = monthly_installment(loan_amount, int_rate, term_months)

        delinq_2yrs = int(rng.choice([0, 1, 2, 3], p=[0.80, 0.13, 0.05, 0.02]))
        open_accounts = int(np.clip(rng.poisson(9), 1, 40))
        total_acc = int(open_accounts + rng.integers(2, 20))
        revolving_utilization = round(float(np.clip(rng.beta(2, 3), 0, 1)), 4)
        revol_bal = round(float(rng.uniform(0, 40000)), 2)
        pub_rec = int(rng.choice([0, 1, 2], p=[0.90, 0.08, 0.02]))
        verification_status = str(rng.choice(VERIFICATION))

        rows.append(
            {
                "applicant_id": str(uuid.uuid4()),
                "loan_amount": round(loan_amount, 2),
                "term_months": term_months,
                "annual_income": round(annual_income, 2),
                "dti": dti,
                "fico_score": fico_score,
                "emp_length_years": emp_length_years,
                "home_ownership": home_ownership,
                "loan_purpose": loan_purpose,
                "delinq_2yrs": delinq_2yrs,
                "open_accounts": open_accounts,
                "revolving_utilization": revolving_utilization,
                "grade": grade,
                "sub_grade": sub_grade,
                "verification_status": verification_status,
                "int_rate": int_rate,
                "installment": installment,
                "revol_bal": revol_bal,
                "pub_rec": pub_rec,
                "total_acc": total_acc,
            }
        )

    return pd.DataFrame(rows)


def main() -> int:
    df = generate()

    os.makedirs(os.path.dirname(CSV_OUT), exist_ok=True)
    df.to_csv(CSV_OUT, index=False)

    database_url = os.getenv("DATABASE_URL")
    engine = create_engine(database_url)
    df.to_sql(
        "synthetic_applicants",
        engine,
        schema="raw",
        if_exists="replace",
        index=False,
    )

    print(f"raw.synthetic_applicants loaded: {len(df)} rows")
    print(f"CSV written: {CSV_OUT}")
    return len(df)


if __name__ == "__main__":
    main()
