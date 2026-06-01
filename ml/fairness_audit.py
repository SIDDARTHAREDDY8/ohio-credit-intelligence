"""Audit model fairness against the CFPB 4/5ths rule.

Reads mart_bias_audit (HMDA approval rates by demographic group), computes
each group's disparate impact ratio relative to the majority group
(White + Male), logs the ratios to MLflow, and raises a Slack alert for any
group below the 0.80 threshold.
"""

import mlflow
from dotenv import load_dotenv

from ml.common import (
    get_engine,
    load_model_config,
    mlflow_tracking_uri,
)
from monitoring.alert_rules import alert_fairness_violation

load_dotenv()


def load_bias_audit(engine):
    import pandas as pd

    query = "SELECT race_label, sex_label, total_applications, approvals, approval_rate_pct FROM public.mart_bias_audit"
    return pd.read_sql(query, engine)


def main():
    model_cfg = load_model_config()
    fairness = model_cfg["fairness"]
    majority_group = fairness["majority_group"]
    majority_sex = fairness["majority_sex"]
    min_ratio = fairness["min_disparate_impact_ratio"]
    min_group_size = fairness["min_group_size"]

    mlflow.set_tracking_uri(mlflow_tracking_uri())
    mlflow.set_experiment(model_cfg["mlflow"]["experiment_name"])

    engine = get_engine()
    df = load_bias_audit(engine)
    df = df[df["total_applications"] >= min_group_size].copy()
    print(f"Auditing {len(df)} demographic groups (>= {min_group_size} applications)")

    majority = df[(df["race_label"] == majority_group) & (df["sex_label"] == majority_sex)]
    if majority.empty:
        raise SystemExit(
            f"Majority group '{majority_group} + {majority_sex}' not found in mart_bias_audit"
        )
    majority_rate = float(majority["approval_rate_pct"].iloc[0])
    print(f"Majority group ({majority_group} + {majority_sex}) approval rate: {majority_rate:.2f}%")

    violations = []
    with mlflow.start_run(run_name="fairness_audit"):
        mlflow.log_metric("majority_approval_rate_pct", majority_rate)
        mlflow.log_param("majority_group", f"{majority_group}+{majority_sex}")
        mlflow.log_param("min_disparate_impact_ratio", min_ratio)

        for _, row in df.iterrows():
            group = f"{row['race_label']}+{row['sex_label']}"
            rate = float(row["approval_rate_pct"])
            ratio = rate / majority_rate if majority_rate > 0 else 0.0
            metric_key = f"dir__{group}".replace(" ", "_").replace("+", "__")
            mlflow.log_metric(metric_key, ratio)
            status = "OK" if ratio >= min_ratio else "VIOLATION"
            print(f"  {group:40s} rate={rate:6.2f}%  DIR={ratio:.3f}  [{status}]")
            if ratio < min_ratio:
                violations.append((group, ratio))

        mlflow.log_metric("n_violations", len(violations))

    for group, ratio in violations:
        alert_fairness_violation(group, ratio)

    if violations:
        print(f"\n{len(violations)} fairness violation(s) detected (DIR < {min_ratio}).")
    else:
        print(f"\nNo fairness violations. All groups meet the {min_ratio} threshold.")


if __name__ == "__main__":
    main()
