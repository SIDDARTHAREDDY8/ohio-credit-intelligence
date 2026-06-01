"""Unit tests for API-key authentication. No app/DB/model needed."""

import pytest
from fastapi import HTTPException

from api.security import require_api_key


def test_auth_disabled_when_no_key(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    # No key configured -> dependency is a no-op (dev/demo).
    assert require_api_key(None) is None
    assert require_api_key("anything") is None


def test_auth_rejects_missing_or_wrong_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "s3cret")
    with pytest.raises(HTTPException) as exc:
        require_api_key(None)
    assert exc.value.status_code == 401
    with pytest.raises(HTTPException):
        require_api_key("wrong")


def test_auth_accepts_valid_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "s3cret")
    assert require_api_key("s3cret") is None


def test_auth_supports_multiple_rotating_keys(monkeypatch):
    monkeypatch.setenv("API_KEY", "old-key, new-key")
    assert require_api_key("old-key") is None
    assert require_api_key("new-key") is None
    with pytest.raises(HTTPException):
        require_api_key("retired-key")
