"""Unit tests for the probability calibration helper. No model/DB needed."""

import numpy as np
from sklearn.isotonic import IsotonicRegression

from ml.common import apply_calibration


def _fitted_calibrator() -> IsotonicRegression:
    # Raw scores that systematically over-predict; isotonic learns the mapping.
    raw = np.array([0.1, 0.2, 0.4, 0.6, 0.8, 0.9])
    observed = np.array([0, 0, 0, 1, 1, 1])
    return IsotonicRegression(out_of_bounds="clip").fit(raw, observed)


def test_no_calibrator_returns_raw():
    assert apply_calibration(0.42, None) == 0.42


def test_calibrated_value_in_unit_interval():
    cal = _fitted_calibrator()
    for p in (0.0, 0.25, 0.5, 0.75, 1.0):
        out = apply_calibration(p, cal)
        assert 0.0 <= out <= 1.0


def test_calibration_is_monotonic():
    cal = _fitted_calibrator()
    lo = apply_calibration(0.2, cal)
    hi = apply_calibration(0.8, cal)
    assert hi >= lo


def test_out_of_range_inputs_are_clipped():
    cal = _fitted_calibrator()
    # out_of_bounds="clip" plus our own clamp keeps results within [0, 1].
    assert 0.0 <= apply_calibration(1.5, cal) <= 1.0
    assert 0.0 <= apply_calibration(-0.3, cal) <= 1.0
