import json
import os
from datetime import date

import numpy as np

from api.db.connection import engine
from sqlalchemy import text

BASELINE_PATH = "ml/encoders/training_score_distribution.json"
N_BINS = 10


def compute_psi(expected: np.ndarray, actual: np.ndarray, n_bins: int = N_BINS) -> float:
    """Compute the Population Stability Index between two score distributions."""
    breakpoints = np.linspace(0, 100, n_bins + 1)
    breakpoints[0] = -np.inf
    breakpoints[-1] = np.inf

    expected_counts, _ = np.histogram(expected, bins=breakpoints)
    actual_counts, _ = np.histogram(actual, bins=breakpoints)

    expected_pct = expected_counts / max(len(expected), 1)
    actual_pct = actual_counts / max(len(actual), 1)

    # Avoid division by zero / log(0)
    epsilon = 1e-6
    expected_pct = np.clip(expected_pct, epsilon, None)
    actual_pct = np.clip(actual_pct, epsilon, None)

    psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
    return float(psi)


def run_drift_detection() -> dict:
    """Compare recent live scores to the training baseline and log PSI."""
    if not os.path.exists(BASELINE_PATH):
        raise FileNotFoundError(f"Baseline not found at {BASELINE_PATH}")

    with open(BASELINE_PATH) as f:
        baseline = json.load(f)
    expected = np.array(baseline["scores"])

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT risk_score FROM public.decisions")).fetchall()
    actual = np.array([float(r[0]) for r in rows])

    if len(actual) == 0:
        return {"status": "no_data", "psi": None}

    psi = compute_psi(expected, actual)

    if psi >= 0.2:
        status = "critical"
    elif psi >= 0.1:
        status = "warning"
    else:
        status = "ok"

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO public.drift_log (psi_score, status, week_start) "
                "VALUES (:psi, :status, :week_start)"
            ),
            {
                "psi": psi,
                "status": status,
                "week_start": date.today(),
            },
        )

    return {"status": status, "psi": psi, "n_samples": len(actual)}


if __name__ == "__main__":
    print(run_drift_detection())
