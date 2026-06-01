"""Programmatic compliance guardrails for adverse-action notices.

ECOA/FCRA adverse-action notices have hard structural requirements. Rather than
trusting the LLM to follow the system prompt every time, we validate every
generated notice against these rules. The same validator powers the offline
evaluation harness (tests/eval) and the live resilient generation path
(claude_service), so what we test is exactly what we enforce in production.
"""

import re

# Markdown / formatting tokens the notice must never contain. ECOA notices are
# read by consumers and regulators as plain prose; markdown is non-compliant.
BANNED_TOKENS = ("**", "*", "#", "---", "___", "__", "•", "- ", "```")

# Human-readable labels for model feature names, used when citing reasons.
FEATURE_LABELS = {
    "loan_amount": "requested loan amount",
    "int_rate": "interest rate",
    "installment": "monthly installment",
    "annual_inc": "annual income",
    "dti": "debt-to-income ratio",
    "delinq_2yrs": "number of recent delinquencies",
    "fico_mid": "credit score",
    "open_acc": "number of open accounts",
    "pub_rec": "number of public records",
    "revol_bal": "revolving balance",
    "revol_util": "credit utilization",
    "total_acc": "total number of accounts",
    "loan_to_income_ratio": "loan-to-income ratio",
    "emp_length_years": "length of employment",
    "term": "loan term",
    "grade": "credit grade",
    "sub_grade": "credit sub-grade",
    "home_ownership": "home ownership status",
    "verification_status": "income verification status",
    "purpose": "stated loan purpose",
}


def humanize_feature(feature: str) -> str:
    """Map a raw model feature name to a consumer-friendly label."""
    return FEATURE_LABELS.get(feature, feature.replace("_", " "))


def expected_citation_numbers(shap_factors: list[dict]) -> list[str]:
    """Build the set of figures a compliant notice should be able to cite.

    Returns string tokens derived from the SHAP factor values so the validator
    can confirm the notice references at least one of the applicant's own
    numbers (an ECOA "specific reasons" requirement).
    """
    tokens: list[str] = []
    for f in shap_factors:
        value = f.get("feature_value")
        if isinstance(value, (int, float)):
            tokens.append(str(int(value)) if float(value).is_integer() else str(value))
            tokens.append(f"{float(value):.1f}")
            tokens.append(f"{float(value):,.0f}")  # e.g. 31,000
        elif value is not None:
            tokens.append(str(value))
    # De-duplicate while preserving order.
    seen: set[str] = set()
    return [t for t in tokens if not (t in seen or seen.add(t))]


def validate_adverse_action_notice(
    notice: str,
    expected_numbers: list[str] | None = None,
    max_words: int = 200,
) -> list[str]:
    """Return a list of compliance violations. Empty list means the notice passes.

    Checks: non-empty, no markdown tokens, within the word limit, written in the
    second person, contains numbered reasons, and (when ``expected_numbers`` is
    supplied) cites at least one of the applicant's own figures.
    """
    violations: list[str] = []

    if not notice or not notice.strip():
        return ["notice is empty"]

    for token in BANNED_TOKENS:
        if token in notice:
            violations.append(f"contains banned formatting token {token!r}")

    word_count = len(notice.split())
    if word_count > max_words:
        violations.append(f"too long: {word_count} words exceeds limit of {max_words}")

    if not re.search(r"\byou\b|\byour\b", notice, flags=re.IGNORECASE):
        violations.append("not written in the second person (no 'you'/'your')")

    if not re.search(r"(?m)^\s*\d+[.)]", notice) and not re.search(r"\b\d+\.\s", notice):
        violations.append("missing numbered reasons")

    if expected_numbers and not any(num in notice for num in expected_numbers):
        violations.append("does not cite any of the applicant's specific figures")

    return violations


def is_compliant(notice: str, expected_numbers: list[str] | None = None) -> bool:
    """Convenience boolean wrapper around :func:`validate_adverse_action_notice`."""
    return not validate_adverse_action_notice(notice, expected_numbers)
