import os

import httpx

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


def send_slack_alert(message: str) -> None:
    """Post a message to the configured Slack webhook (no-op if unset)."""
    if not SLACK_WEBHOOK_URL:
        print(f"[ALERT] {message}")
        return
    try:
        httpx.post(SLACK_WEBHOOK_URL, json={"text": message}, timeout=10)
    except httpx.HTTPError as e:
        print(f"[ALERT] Failed to send Slack alert: {e}\n{message}")


def alert_drift_warning(psi: float, n_samples: int) -> None:
    send_slack_alert(
        f":warning: *Drift WARNING* — PSI={psi:.3f} over {n_samples} decisions "
        f"(threshold 0.10). Model scores are shifting from the training baseline."
    )


def alert_drift_critical(psi: float, n_samples: int) -> None:
    send_slack_alert(
        f":rotating_light: *Drift CRITICAL* — PSI={psi:.3f} over {n_samples} decisions "
        f"(threshold 0.20). Investigate and consider retraining the model."
    )


def alert_fairness_violation(group: str, disparate_impact_ratio: float) -> None:
    send_slack_alert(
        f":rotating_light: *Fairness violation* — group '{group}' has a disparate "
        f"impact ratio of {disparate_impact_ratio:.2f} (CFPB 4/5ths rule requires >= 0.80)."
    )
