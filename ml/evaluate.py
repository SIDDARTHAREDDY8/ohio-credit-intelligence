"""Evaluate the champion model on the held-out test set.

Loads the champion from the MLflow registry, scores mart_training_set
(is_train = FALSE), and logs ROC curve, confusion matrix, and score
distribution plots as artifacts on a new evaluation run.
"""

import os

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
from dotenv import load_dotenv
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)

from ml.common import (
    apply_label_encoders,
    feature_lists,
    get_engine,
    gini_from_auc,
    ks_statistic,
    load_features_config,
    load_model_config,
    load_training_frame,
    mlflow_tracking_uri,
)

load_dotenv()

ENCODER_PATH = os.path.join(os.path.dirname(__file__), "encoders", "label_encoders.joblib")


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
    proba = model.predict_proba(X)[:, 1]
    preds = (proba >= 0.5).astype(int)

    auc = roc_auc_score(y, proba)
    ks = ks_statistic(y, proba)
    gini = gini_from_auc(auc)

    with mlflow.start_run(run_name="evaluation"):
        mlflow.log_metric("test_auc", auc)
        mlflow.log_metric("test_ks", ks)
        mlflow.log_metric("test_gini", gini)

        # ROC curve
        fpr, tpr, _ = roc_curve(y, proba)
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.plot(fpr, tpr, label=f"AUC = {auc:.4f}")
        ax.plot([0, 1], [0, 1], "k--")
        ax.set_xlabel("False Positive Rate")
        ax.set_ylabel("True Positive Rate")
        ax.set_title("ROC Curve (test set)")
        ax.legend(loc="lower right")
        fig.tight_layout()
        mlflow.log_figure(fig, "roc_curve.png")
        plt.close(fig)

        # Confusion matrix
        cm = confusion_matrix(y, preds)
        fig, ax = plt.subplots(figsize=(5, 5))
        ConfusionMatrixDisplay(cm, display_labels=["Paid", "Default"]).plot(ax=ax, colorbar=False)
        ax.set_title("Confusion Matrix (test set)")
        fig.tight_layout()
        mlflow.log_figure(fig, "confusion_matrix.png")
        plt.close(fig)

        # Score distribution
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.hist(proba[y == 0] * 100, bins=50, alpha=0.6, label="Paid")
        ax.hist(proba[y == 1] * 100, bins=50, alpha=0.6, label="Default")
        ax.set_xlabel("Risk score (0-100)")
        ax.set_ylabel("Count")
        ax.set_title("Score Distribution by Outcome")
        ax.legend()
        fig.tight_layout()
        mlflow.log_figure(fig, "score_distribution.png")
        plt.close(fig)

    print(f"Test AUC={auc:.4f}  KS={ks:.4f}  Gini={gini:.4f}")


if __name__ == "__main__":
    main()
