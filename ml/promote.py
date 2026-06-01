"""Promote a challenger model to champion if it beats the incumbent.

Compares the most recently registered model version's cross-validated AUC
against the current champion's AUC. If the challenger improves AUC by more
than MIN_IMPROVEMENT, it is promoted by moving the champion alias; otherwise
the incumbent is kept.
"""

import mlflow
from dotenv import load_dotenv
from mlflow.tracking import MlflowClient

from ml.common import load_model_config, mlflow_tracking_uri

load_dotenv()

MIN_IMPROVEMENT = 0.005


def run_auc(client: MlflowClient, run_id: str) -> float:
    run = client.get_run(run_id)
    metrics = run.data.metrics
    for key in ("mean_auc", "test_auc", "auc"):
        if key in metrics:
            return float(metrics[key])
    raise ValueError(f"No AUC metric found on run {run_id}")


def main():
    model_cfg = load_model_config()
    name = model_cfg["mlflow"]["model_name"]
    alias = model_cfg["mlflow"]["champion_alias"]

    mlflow.set_tracking_uri(mlflow_tracking_uri())
    client = MlflowClient()

    versions = client.search_model_versions(f"name='{name}'")
    if not versions:
        raise SystemExit(f"No registered versions found for model '{name}'")

    latest = max(versions, key=lambda v: int(v.version))
    challenger_auc = run_auc(client, latest.run_id)
    print(f"Challenger: version {latest.version}  AUC={challenger_auc:.4f}")

    try:
        champion = client.get_model_version_by_alias(name, alias)
    except Exception:
        champion = None

    if champion is None:
        client.set_registered_model_alias(name, alias, latest.version)
        print(f"No existing champion. Promoted version {latest.version} to '{alias}'.")
        return

    if str(champion.version) == str(latest.version):
        print(f"Latest version {latest.version} is already the champion. Nothing to do.")
        return

    champion_auc = run_auc(client, champion.run_id)
    print(f"Champion:   version {champion.version}  AUC={champion_auc:.4f}")

    improvement = challenger_auc - champion_auc
    print(f"Improvement: {improvement:+.4f} (threshold {MIN_IMPROVEMENT})")

    if improvement > MIN_IMPROVEMENT:
        client.set_registered_model_alias(name, alias, latest.version)
        print(f"Promoted version {latest.version} to '{alias}' (Δ AUC {improvement:+.4f}).")
    else:
        print(f"Kept champion version {champion.version}. Challenger did not clear threshold.")


if __name__ == "__main__":
    main()
