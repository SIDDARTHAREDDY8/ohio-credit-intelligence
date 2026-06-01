"""Train the LightGBM credit-risk model and register it as champion in MLflow.

Trains on mart_training_set (is_train = TRUE), evaluates with 5-fold
StratifiedKFold, logs metrics/artifacts to MLflow, registers the final model
in the Model Registry, and writes the training score distribution used by the
drift detector as its baseline.
"""

import json
import os

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import mlflow.lightgbm
import numpy as np
from dotenv import load_dotenv
from lightgbm import LGBMClassifier, early_stopping
from mlflow.tracking import MlflowClient
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from ml.common import (
    apply_label_encoders,
    feature_lists,
    fit_label_encoders,
    get_engine,
    gini_from_auc,
    ks_statistic,
    load_features_config,
    load_model_config,
    load_training_frame,
    mlflow_tracking_uri,
)

load_dotenv()

ENCODER_DIR = os.path.join(os.path.dirname(__file__), "encoders")
ENCODER_PATH = os.path.join(ENCODER_DIR, "label_encoders.joblib")
SCORE_DIST_PATH = os.path.join(ENCODER_DIR, "training_score_distribution.json")


def main():
    features_cfg = load_features_config()
    model_cfg = load_model_config()
    numeric, categorical, target = feature_lists(features_cfg)
    all_features = numeric + categorical

    engine = get_engine()
    df = load_training_frame(engine, is_train=True, columns=all_features + [target])
    print(f"Loaded {len(df):,} training rows")

    y = df[target].astype(int).values

    # Fit + persist categorical encoders
    os.makedirs(ENCODER_DIR, exist_ok=True)
    encoders = fit_label_encoders(df, categorical)
    joblib.dump(encoders, ENCODER_PATH)
    X = apply_label_encoders(df[all_features], encoders)

    params = dict(features_cfg["model_params"])
    params.pop("algorithm", None)
    early_stop = model_cfg["training"]["early_stopping_rounds"]

    mlflow.set_tracking_uri(mlflow_tracking_uri())
    mlflow.set_experiment(model_cfg["mlflow"]["experiment_name"])

    cv = StratifiedKFold(
        n_splits=features_cfg["cross_validation"]["n_folds"],
        shuffle=features_cfg["cross_validation"]["shuffle"],
        random_state=features_cfg["cross_validation"]["random_state"],
    )

    with mlflow.start_run() as run:
        mlflow.log_params(params)

        fold_metrics = {"auc": [], "precision": [], "recall": [], "f1": []}
        for fold, (tr_idx, va_idx) in enumerate(cv.split(X, y), start=1):
            X_tr, X_va = X.iloc[tr_idx], X.iloc[va_idx]
            y_tr, y_va = y[tr_idx], y[va_idx]

            model = LGBMClassifier(**params, verbose=-1)
            model.fit(
                X_tr,
                y_tr,
                eval_set=[(X_va, y_va)],
                callbacks=[early_stopping(early_stop, verbose=False)],
            )
            proba = model.predict_proba(X_va)[:, 1]
            preds = (proba >= 0.5).astype(int)

            auc = roc_auc_score(y_va, proba)
            prec = precision_score(y_va, preds, zero_division=0)
            rec = recall_score(y_va, preds, zero_division=0)
            f1 = f1_score(y_va, preds, zero_division=0)

            fold_metrics["auc"].append(auc)
            fold_metrics["precision"].append(prec)
            fold_metrics["recall"].append(rec)
            fold_metrics["f1"].append(f1)

            for name, val in [("auc", auc), ("precision", prec), ("recall", rec), ("f1", f1)]:
                mlflow.log_metric(f"fold_{name}", val, step=fold)
            print(f"Fold {fold}: AUC={auc:.4f} P={prec:.4f} R={rec:.4f} F1={f1:.4f}")

        for name, vals in fold_metrics.items():
            mlflow.log_metric(f"mean_{name}", float(np.mean(vals)))

        # Final model on full training set
        final_model = LGBMClassifier(**params, verbose=-1)
        final_model.fit(X, y)
        train_proba = final_model.predict_proba(X)[:, 1]

        ks = ks_statistic(y, train_proba)
        gini = gini_from_auc(float(np.mean(fold_metrics["auc"])))
        mlflow.log_metric("ks_statistic", ks)
        mlflow.log_metric("gini", gini)
        print(f"KS={ks:.4f}  Gini={gini:.4f}")

        # Feature importance chart
        importances = final_model.feature_importances_
        order = np.argsort(importances)[::-1]
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.barh(
            [all_features[i] for i in order][::-1],
            [importances[i] for i in order][::-1],
        )
        ax.set_title("LightGBM Feature Importance")
        ax.set_xlabel("Importance (gain split count)")
        fig.tight_layout()
        mlflow.log_figure(fig, "feature_importance.png")
        plt.close(fig)

        # Log + register model
        artifact_path = model_cfg["mlflow"]["artifact_path"]
        model_name = model_cfg["mlflow"]["model_name"]
        mlflow.lightgbm.log_model(
            final_model,
            artifact_path=artifact_path,
            registered_model_name=model_name,
        )

        # Resolve the version we just registered and set the champion alias
        client = MlflowClient()
        versions = client.search_model_versions(f"name='{model_name}'")
        new_version = max(int(v.version) for v in versions if v.run_id == run.info.run_id)
        client.set_registered_model_alias(
            model_name, model_cfg["mlflow"]["champion_alias"], str(new_version)
        )

        # Training score distribution baseline for the drift detector (0-100 scale)
        scores = (train_proba * 100).tolist()
        with open(SCORE_DIST_PATH, "w") as f:
            json.dump({"scores": scores}, f)

    print("Training complete. Model registered as champion.")


if __name__ == "__main__":
    main()
