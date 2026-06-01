"""Calibrate the champion model's probabilities and persist the calibrator.

A LightGBM classifier's raw scores are not guaranteed to be well-calibrated
probabilities: a predicted 0.30 may not mean ~30% of such applicants actually
default. For a credit model whose APPROVE/REVIEW/DECLINE tiers are defined on the
probability scale, calibration is a model-risk requirement.

This script loads the registered champion, scores the held-out test set, fits an
isotonic regression calibrator, reports the Brier score before/after on a
disjoint holdout, logs a reliability diagram to MLflow, and saves the calibrator
as an artifact the API loads at startup (ml/encoders/calibrator.joblib).

It does NOT retrain or alter the champion model, so SHAP TreeExplainer keeps
operating on the original tree model.

Run:  python ml/calibrate.py
"""

import os

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
from dotenv import load_dotenv
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import train_test_split

from ml.common import (
    apply_label_encoders,
    feature_lists,
    get_engine,
    load_features_config,
    load_model_config,
    load_training_frame,
    mlflow_tracking_uri,
)

load_dotenv()

ENCODER_DIR = os.path.join(os.path.dirname(__file__), "encoders")
ENCODER_PATH = os.path.join(ENCODER_DIR, "label_encoders.joblib")
CALIBRATOR_PATH = os.path.join(ENCODER_DIR, "calibrator.joblib")
RANDOM_STATE = 42


def load_champion(model_cfg: dict):
    name = model_cfg["mlflow"]["model_name"]
    alias = model_cfg["mlflow"]["champion_alias"]
    return mlflow.lightgbm.load_model(f"models:/{name}@{alias}")


def main():
    features_cfg = load_features_config()
    model_cfg = load_model_config()
    numeric, categorical, target = feature_lists(features_cfg)
    all_features = numeric + categorical

    mlflow.set_tracking_uri(mlflow_tracking_uri())
    mlflow.set_experiment(model_cfg["mlflow"]["experiment_name"])

    model = load_champion(model_cfg)
    encoders = joblib.load(ENCODER_PATH)

    engine = get_engine()
    df = load_training_frame(engine, is_train=False, columns=all_features + [target])
    print(f"Loaded {len(df):,} test rows")

    y = df[target].astype(int).values
    X = apply_label_encoders(df[all_features], encoders)
    proba_raw = model.predict_proba(X)[:, 1]

    # Split: fit the calibrator on one half, measure honestly on the other.
    p_fit, p_hold, y_fit, y_hold = train_test_split(
        proba_raw, y, test_size=0.5, stratify=y, random_state=RANDOM_STATE
    )

    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(p_fit, y_fit)

    brier_raw = brier_score_loss(y_hold, p_hold)
    brier_cal = brier_score_loss(y_hold, iso.predict(p_hold))
    print(f"Brier (holdout)  raw={brier_raw:.4f}  calibrated={brier_cal:.4f}")

    with mlflow.start_run(run_name="calibration"):
        mlflow.log_metric("brier_raw", brier_raw)
        mlflow.log_metric("brier_calibrated", brier_cal)
        mlflow.log_metric("brier_improvement", brier_raw - brier_cal)

        # Reliability diagram: raw vs calibrated on the holdout.
        frac_raw, mean_raw = calibration_curve(y_hold, p_hold, n_bins=10, strategy="quantile")
        frac_cal, mean_cal = calibration_curve(
            y_hold, iso.predict(p_hold), n_bins=10, strategy="quantile"
        )
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.plot([0, 1], [0, 1], "k--", label="Perfectly calibrated")
        ax.plot(mean_raw, frac_raw, marker="o", label=f"Raw (Brier {brier_raw:.3f})")
        ax.plot(mean_cal, frac_cal, marker="s", label=f"Calibrated (Brier {brier_cal:.3f})")
        ax.set_xlabel("Mean predicted probability")
        ax.set_ylabel("Observed default frequency")
        ax.set_title("Reliability Diagram (holdout)")
        ax.legend(loc="upper left")
        fig.tight_layout()
        mlflow.log_figure(fig, "reliability_diagram.png")
        plt.close(fig)

        # Deploy a calibrator fit on ALL available test data for best coverage.
        final = IsotonicRegression(out_of_bounds="clip")
        final.fit(proba_raw, y)
        os.makedirs(ENCODER_DIR, exist_ok=True)
        joblib.dump(final, CALIBRATOR_PATH)
        mlflow.log_artifact(CALIBRATOR_PATH, artifact_path="calibrator")

    print(f"Saved calibrator to {CALIBRATOR_PATH}")


if __name__ == "__main__":
    main()
