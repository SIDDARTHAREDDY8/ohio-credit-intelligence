"""Shared helpers for the ML scripts: config loading, DB access, encoding."""

import os

import numpy as np
import pandas as pd
import yaml
from sqlalchemy import create_engine

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")
FEATURES_PATH = os.path.join(CONFIG_DIR, "features.yaml")
MODEL_CONFIG_PATH = os.path.join(CONFIG_DIR, "model_config.yaml")


def load_yaml(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_features_config() -> dict:
    return load_yaml(FEATURES_PATH)


def load_model_config() -> dict:
    return load_yaml(MODEL_CONFIG_PATH)


def get_engine():
    database_url = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/ohio_credit"
    )
    return create_engine(database_url)


def mlflow_tracking_uri() -> str:
    return os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")


def feature_lists(features_cfg: dict) -> tuple[list[str], list[str], str]:
    numeric = features_cfg["features"]["numeric"]
    categorical = features_cfg["features"]["categorical"]
    target = features_cfg["target"]
    return numeric, categorical, target


def load_training_frame(engine, is_train: bool, columns: list[str]) -> pd.DataFrame:
    cols = ", ".join(columns)
    flag = "TRUE" if is_train else "FALSE"
    query = f"SELECT {cols} FROM public.mart_training_set WHERE is_train IS {flag}"
    return pd.read_sql(query, engine)


def fit_label_encoders(df: pd.DataFrame, categorical: list[str]) -> dict:
    """Fit a LabelEncoder per categorical column, returning a dict."""
    from sklearn.preprocessing import LabelEncoder

    encoders = {}
    for col in categorical:
        le = LabelEncoder()
        le.fit(df[col].astype(str))
        encoders[col] = le
    return encoders


def apply_label_encoders(df: pd.DataFrame, encoders: dict) -> pd.DataFrame:
    """Apply encoders; labels unseen at fit time map to -1."""
    out = df.copy()
    for col, le in encoders.items():
        mapping = {label: idx for idx, label in enumerate(le.classes_)}
        out[col] = out[col].astype(str).map(mapping).fillna(-1).astype(int)
    return out


def ks_statistic(y_true: np.ndarray, y_proba: np.ndarray) -> float:
    from scipy.stats import ks_2samp

    return float(ks_2samp(y_proba[y_true == 1], y_proba[y_true == 0]).statistic)


def gini_from_auc(auc: float) -> float:
    return float(2 * auc - 1)
