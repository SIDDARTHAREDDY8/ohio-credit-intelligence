import os
from functools import lru_cache

from anthropic import Anthropic

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")


@lru_cache(maxsize=1)
def _client() -> Anthropic:
    """Construct the Anthropic client lazily so .env is loaded first."""
    return Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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


def generate_adverse_action_notice(applicant: dict, score: float, tier: int, shap_factors: list) -> str:
    """Generate an ECOA-compliant adverse action notice via the Claude API."""
    factors_text = "\n".join(
        f"- {f['feature']}: value={f['feature_value']}, "
        f"impact={f['direction']} (SHAP {f['shap_value']:+.3f})"
        for f in shap_factors
    )

    user_message = f"""A loan application was declined.

Model risk score: {score:.1f} / 100 (Tier {tier}, higher = higher default risk)

The top factors that drove this decision (from the model's SHAP explanation):
{factors_text}

Write the adverse action notice for this applicant.
Return plain text only. No markdown. No asterisks. No bold. No dashes as bullets."""

    response = _client().messages.create(
        model=os.getenv("CLAUDE_MODEL", CLAUDE_MODEL),
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text
