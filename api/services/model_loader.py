"""Load the champion model and score applicants with SHAP explanations.

Holds the MLflow champion model, the categorical label encoders, and a SHAP
TreeExplainer as a process-wide singleton so they load once at startup. The
scoring path returns the 0-100 risk score, tier, decision, and the top SHAP
factors that drove the decision.
"""

import os

import joblib
import mlflow
import numpy as np
import shap
from mlflow.tracking import MlflowClient

from api.schemas.applicant import ApplicantInput
from api.services.feature_builder import ALL_FEATURES, build_feature_row
from ml.common import apply_label_encoders, load_model_config, mlflow_tracking_uri

ENCODER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "ml",
    "encoders",
    "label_encoders.joblib",
)

TOP_N_FACTORS = 5


def score_to_tier_decision(score: float) -> tuple[int, str]:
    """Map a 0-100 risk score to a tier (1-5) and decision."""
    if score <= 20:
        return 1, "APPROVE"
    if score <= 40:
        return 2, "APPROVE"
    if score <= 60:
        return 3, "REVIEW"
    if score <= 80:
        return 4, "DECLINE"
    return 5, "DECLINE"


class ModelService:
    def __init__(self) -> None:
        self.model = None
        self.encoders = None
        self.explainer = None
        self.model_version = "unknown"
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        cfg = load_model_config()
        name = cfg["mlflow"]["model_name"]
        alias = cfg["mlflow"]["champion_alias"]

        mlflow.set_tracking_uri(mlflow_tracking_uri())
        self.model = mlflow.lightgbm.load_model(f"models:/{name}@{alias}")
        self.encoders = joblib.load(ENCODER_PATH)
        self.explainer = shap.TreeExplainer(self.model)

        try:
            mv = MlflowClient().get_model_version_by_alias(name, alias)
            self.model_version = str(mv.version)
        except Exception:
            self.model_version = "unknown"

        self._loaded = True

    def score(self, applicant: ApplicantInput) -> dict:
        if not self._loaded:
            self.load()

        raw = build_feature_row(applicant)
        encoded = apply_label_encoders(raw, self.encoders)

        proba = float(self.model.predict_proba(encoded)[:, 1][0])
        score = round(proba * 100, 2)
        tier, decision = score_to_tier_decision(score)

        shap_values = self.explainer.shap_values(encoded)
        if isinstance(shap_values, list):  # binary classifier → positive class
            shap_values = shap_values[1]
        row_shap = np.asarray(shap_values)[0]

        order = np.argsort(np.abs(row_shap))[::-1][:TOP_N_FACTORS]
        factors = []
        for i in order:
            feature = ALL_FEATURES[i]
            value = raw.iloc[0][feature]
            factors.append(
                {
                    "feature": feature,
                    "shap_value": round(float(row_shap[i]), 4),
                    "feature_value": value if isinstance(value, str) else round(float(value), 4),
                    "direction": "increases_risk" if row_shap[i] > 0 else "decreases_risk",
                }
            )

        return {
            "score": score,
            "tier": tier,
            "decision": decision,
            "default_probability": round(proba, 4),
            "top_shap_factors": factors,
            "model_version": self.model_version,
        }


model_service = ModelService()
