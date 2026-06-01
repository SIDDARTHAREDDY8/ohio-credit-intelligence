"""Adverse-action notice generation via the Claude API, with guardrails.

Generation is resilient: the Anthropic client retries transient failures, every
notice is validated against the ECOA/FCRA guardrails, one corrective retry is
attempted if the first draft fails validation, and if Claude is unavailable or
keeps producing non-compliant output we fall back to a deterministic, fully
compliant template. The endpoint therefore never fails a credit decision just
because letter generation hiccupped.
"""

import logging
import os
from functools import lru_cache

from anthropic import Anthropic

from api.services.notice_guardrails import (
    expected_citation_numbers,
    humanize_feature,
    validate_adverse_action_notice,
)

logger = logging.getLogger("api.claude")

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
# Built-in SDK retries handle 429 / 5xx with exponential backoff.
CLAUDE_MAX_RETRIES = int(os.getenv("CLAUDE_MAX_RETRIES", "2"))


@lru_cache(maxsize=1)
def _client() -> Anthropic:
    """Construct the Anthropic client lazily so .env is loaded first."""
    return Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_retries=CLAUDE_MAX_RETRIES,
    )


SYSTEM_PROMPT = """You are a compliance officer at a regional bank in Ohio.
You generate adverse action notices that comply with ECOA (Equal Credit
Opportunity Act) and FCRA (Fair Credit Reporting Act) requirements.
Your notices are clear, specific, factual, and written for a consumer
with no financial background.

Rules:
- Never use markdown formatting of any kind
- No asterisks, no bold, no italics, no hashtags, no dashes as bullet points
- No --- dividers or horizontal rules
- Write plain prose paragraphs only
- Use numbered lines like "1." for reasons but on separate lines with no asterisks
- Never use ** or * around any word
- Always cite the specific number from the applicant profile
- Write in second person
- Keep the notice under 200 words
- End with one concrete actionable step

Output format must be plain text only. No symbols except periods, commas,
colons, and standard punctuation."""


def _factors_text(shap_factors: list[dict]) -> str:
    return "\n".join(
        f"- {f['feature']}: value={f['feature_value']}, "
        f"impact={f['direction']} (SHAP {f['shap_value']:+.3f})"
        for f in shap_factors
    )


def _call_claude(
    score: float, tier: int, shap_factors: list[dict], correction: str | None = None
) -> str:
    user_message = f"""A loan application was declined.

Model risk score: {score:.1f} / 100 (Tier {tier}, higher = higher default risk)

The top factors that drove this decision (from the model's SHAP explanation):
{_factors_text(shap_factors)}

Write the adverse action notice for this applicant.
Return plain text only. No markdown. No asterisks. No bold. No dashes as bullets."""

    if correction:
        user_message += (
            f"\n\nYour previous draft was rejected for these reasons: {correction}. "
            "Fix every issue and return only the corrected plain-text notice."
        )

    response = _client().messages.create(
        model=os.getenv("CLAUDE_MODEL", CLAUDE_MODEL),
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def build_fallback_notice(
    applicant: dict, score: float, tier: int, shap_factors: list[dict]
) -> str:
    """Deterministic, guardrail-compliant notice used when Claude is unavailable.

    Cites the top risk-increasing factors with the applicant's own values so the
    fallback still satisfies the ECOA "specific reasons" requirement.
    """
    risk_factors = [f for f in shap_factors if f.get("direction") == "increases_risk"][:4]
    if not risk_factors:  # extremely rare; cite the strongest factors regardless
        risk_factors = shap_factors[:4]

    intro = (
        "Thank you for your recent credit application. After a careful review of "
        "your application, we are unable to approve your request for credit at this "
        "time. This decision was based on the following factors from the information "
        "you provided:"
    )
    reasons = []
    for i, f in enumerate(risk_factors, start=1):
        label = humanize_feature(f["feature"])
        value = f["feature_value"]
        reasons.append(f"{i}. Your {label} of {value} weighed against approval.")

    closing = (
        "You have the right to obtain a free copy of any credit report used in this "
        "decision and to dispute any information you believe is inaccurate. To "
        "strengthen a future application, you can work to reduce your outstanding "
        "balances and maintain on-time payments before you reapply."
    )
    return f"{intro}\n\n" + "\n".join(reasons) + f"\n\n{closing}"


def generate_adverse_action_notice(
    applicant: dict, score: float, tier: int, shap_factors: list[dict]
) -> dict:
    """Generate a compliant adverse-action notice.

    Returns ``{"notice": str, "status": "generated" | "fallback"}``. The status
    lets callers distinguish an LLM-authored notice from the deterministic
    fallback used when the API is unavailable or repeatedly non-compliant.
    """
    expected = expected_citation_numbers(shap_factors)

    try:
        text = _call_claude(score, tier, shap_factors)
        violations = validate_adverse_action_notice(text, expected)

        if violations:
            logger.warning("Adverse-action draft failed guardrails: %s. Retrying.", violations)
            text = _call_claude(score, tier, shap_factors, correction="; ".join(violations))
            violations = validate_adverse_action_notice(text, expected)

        if not violations:
            return {"notice": text, "status": "generated"}

        logger.warning(
            "Adverse-action notice still non-compliant after retry (%s); using fallback.",
            violations,
        )
    except Exception as exc:  # never fail the credit decision on a notice error
        logger.warning("Claude notice generation failed (%s); using fallback.", exc)

    return {
        "notice": build_fallback_notice(applicant, score, tier, shap_factors),
        "status": "fallback",
    }
