"""Translate an ApplicantInput payload into the model's feature row.

The column order and engineered features must match ml/config/features.yaml
and the dbt mart that trained the model. Categorical values are produced in
their training-time form (e.g. term as "36 months") so the label encoders
map them correctly.
"""

import pandas as pd

from api.schemas.applicant import ApplicantInput
from ml.common import feature_lists, load_features_config

_features_cfg = load_features_config()
_numeric, _categorical, _ = feature_lists(_features_cfg)
ALL_FEATURES = _numeric + _categorical


def build_feature_row(applicant: ApplicantInput) -> pd.DataFrame:
    """Return a single-row DataFrame of model features in the trained order."""
    row = {
        "loan_amount": applicant.loan_amount,
        "int_rate": applicant.int_rate,
        "installment": applicant.installment,
        "annual_inc": applicant.annual_income,
        "dti": applicant.dti,
        "delinq_2yrs": applicant.delinq_2yrs,
        # FICO mid-point: the applicant supplies a single score, used directly.
        "fico_mid": float(applicant.fico_score),
        "open_acc": applicant.open_accounts,
        "pub_rec": applicant.pub_rec,
        "revol_bal": applicant.revol_bal,
        # Training data stores utilization on a 0-100 scale; the API takes 0-1.
        "revol_util": applicant.revolving_utilization * 100.0,
        "total_acc": applicant.total_acc,
        "loan_to_income_ratio": applicant.loan_amount / applicant.annual_income,
        "emp_length_years": float(applicant.emp_length_years),
        "term": f"{applicant.term_months} months",
        "grade": applicant.grade,
        "sub_grade": applicant.sub_grade,
        "home_ownership": applicant.home_ownership,
        "verification_status": applicant.verification_status,
        "purpose": applicant.loan_purpose,
    }
    return pd.DataFrame([row])[ALL_FEATURES]
