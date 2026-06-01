"""Unit tests for ml.common pure helpers (no DB/MLflow needed)."""

import numpy as np
import pandas as pd
import pytest

from ml.common import (
    apply_label_encoders,
    feature_lists,
    fit_label_encoders,
    gini_from_auc,
    ks_statistic,
    load_features_config,
)


def test_gini_from_auc():
    assert gini_from_auc(0.5) == 0.0
    assert gini_from_auc(1.0) == 1.0
    assert gini_from_auc(0.72) == pytest.approx(0.44)


def test_apply_label_encoders_unseen_maps_to_minus_one():
    df = pd.DataFrame({"grade": ["A", "B", "C"]})
    encoders = fit_label_encoders(df, ["grade"])
    new = pd.DataFrame({"grade": ["A", "Z"]})  # Z unseen at fit time
    out = apply_label_encoders(new, encoders)
    assert out.iloc[0]["grade"] == 0  # A is first class
    assert out.iloc[1]["grade"] == -1  # unseen


def test_apply_label_encoders_preserves_other_columns():
    df = pd.DataFrame({"grade": ["A", "B"], "amount": [100, 200]})
    encoders = fit_label_encoders(df, ["grade"])
    out = apply_label_encoders(df, encoders)
    assert list(out["amount"]) == [100, 200]


def test_ks_statistic_perfect_separation():
    y_true = np.array([0, 0, 1, 1])
    y_proba = np.array([0.1, 0.2, 0.8, 0.9])
    assert ks_statistic(y_true, y_proba) == 1.0


def test_feature_lists_structure():
    cfg = load_features_config()
    numeric, categorical, target = feature_lists(cfg)
    assert isinstance(numeric, list) and len(numeric) > 0
    assert isinstance(categorical, list) and len(categorical) > 0
    assert isinstance(target, str)
    # no overlap between numeric and categorical
    assert set(numeric).isdisjoint(set(categorical))
