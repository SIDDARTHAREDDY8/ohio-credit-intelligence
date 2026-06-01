"""API authentication and rate limiting.

Two production safeguards for a scoring endpoint that triggers paid Claude API
calls and database writes:

1. API-key auth via the ``X-API-Key`` header. Keys are read from the ``API_KEY``
   environment variable (comma-separated for key rotation). If no key is
   configured the dependency is a no-op so local development and the demo keep
   working without friction; production sets ``API_KEY`` to enforce.
2. Per-client rate limiting (slowapi) keyed on remote address, applied to the
   expensive ``/score`` route.
"""

import logging
import os

from fastapi import Header, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger("api.security")

# Limit applied to /score. Configurable; defaults to a sane interactive rate.
SCORE_RATE_LIMIT = os.getenv("SCORE_RATE_LIMIT", "30/minute")

limiter = Limiter(key_func=get_remote_address)


def _configured_keys() -> set[str]:
    raw = os.getenv("API_KEY", "")
    return {k.strip() for k in raw.split(",") if k.strip()}


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """FastAPI dependency enforcing the ``X-API-Key`` header when keys are set."""
    keys = _configured_keys()
    if not keys:
        # Auth disabled (no key configured) — dev/demo convenience.
        return
    if x_api_key not in keys:
        logger.warning("Rejected request with missing/invalid API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
