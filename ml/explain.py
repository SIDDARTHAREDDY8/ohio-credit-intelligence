"""Generate global SHAP explanations for the champion model.

Loads the champion from the MLflow registry, samples test rows from
mart_training_set (is_train = FALSE), computes SHAP values with a
TreeExplainer, and logs beeswarm + bar-importance plots plus the top-10
feature ranking as artifacts on a new explanation run.
"""

import os

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import shap
from dotenv import load_dotenv

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

ENCODER_PATH = os.path.join(os.path.dirname(__file__), "encoders", "label_encoders.joblib")
SAMPLE_SIZE = 2000


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
    if len(df) > SAMPLE_SIZE:
        df = df.sample(n=SAMPLE_SIZE, random_state=42).reset_index(drop=True)
    print(f"Explaining {len(df):,} sampled test rows")

    X = apply_label_encoders(df[all_features], encoders)

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    # LightGBM binary classifier may return a list (per-class); take positive class
    if isinstance(shap_values, list):
        shap_values = shap_values[1]

    mean_abs = np.abs(shap_values).mean(axis=0)
    order = np.argsort(mean_abs)[::-1]
    top10 = [(all_features[i], float(mean_abs[i])) for i in order[:10]]

    with mlflow.start_run(run_name="shap_explanation"):
        # Beeswarm summary
        plt.figure()
        shap.summary_plot(shap_values, X, feature_names=all_features, show=False)
        fig = plt.gcf()
        fig.tight_layout()
        mlflow.log_figure(fig, "shap_beeswarm.png")
        plt.close(fig)

        # Bar importance
        plt.figure()
        shap.summary_plot(
            shap_values, X, feature_names=all_features, plot_type="bar", show=False
        )
        fig = plt.gcf()
        fig.tight_layout()
        mlflow.log_figure(fig, "shap_bar_importance.png")
        plt.close(fig)

        for rank, (feat, val) in enumerate(top10, start=1):
            mlflow.log_metric(f"shap_top_{rank:02d}__{feat}", val)

        lines = "\n".join(f"{r:2d}. {f:24s} {v:.5f}" for r, (f, v) in enumerate(top10, 1))
        mlflow.log_text(
            "Top 10 features by mean |SHAP value|\n\n" + lines, "shap_top10.txt"
        )

    print("Top 10 features by mean |SHAP|:")
    for rank, (feat, val) in enumerate(top10, start=1):
        print(f"  {rank:2d}. {feat:24s} {val:.5f}")
    print("SHAP explanation artifacts logged to MLflow.")


if __name__ == "__main__":
    main()
