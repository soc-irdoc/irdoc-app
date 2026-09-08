# backend/tests/unit/test_security_mfa.py
import time

import pytest
from fastapi import HTTPException

from app.core.security import (
    create_access_token,
    create_mfa_challenge_token,
    create_mfa_setup_token,
    decode_token,
)

USER_ID = "00000000-0000-0000-0000-000000000001"
ORG_ID = "00000000-0000-0000-0000-000000000002"


def test_mfa_challenge_token_has_correct_type():
    token = create_mfa_challenge_token(USER_ID, ORG_ID)
    payload = decode_token(token, expected_type="mfa_challenge")
    assert payload["type"] == "mfa_challenge"
    assert payload["sub"] == USER_ID


def test_mfa_setup_token_has_correct_type():
    token = create_mfa_setup_token(USER_ID, ORG_ID)
    payload = decode_token(token, expected_type="mfa_setup")
    assert payload["type"] == "mfa_setup"


def test_challenge_token_rejected_as_access():
    token = create_mfa_challenge_token(USER_ID, ORG_ID)
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token, expected_type="access")
    assert exc_info.value.status_code == 401


def test_access_token_rejected_as_mfa_challenge():
    token = create_access_token(USER_ID, ORG_ID)
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token, expected_type="mfa_challenge")
    assert exc_info.value.status_code == 401


def test_mfa_challenge_expires_in_5_minutes():
    token = create_mfa_challenge_token(USER_ID, ORG_ID)
    from jose import jwt as jose_jwt

    from app.core.config import get_settings
    settings = get_settings()
    payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    remaining = payload["exp"] - time.time()
    assert 250 <= remaining <= 310  # 5 minutes ±1 min tolerance


def test_mfa_setup_expires_in_10_minutes():
    token = create_mfa_setup_token(USER_ID, ORG_ID)
    from jose import jwt as jose_jwt

    from app.core.config import get_settings
    settings = get_settings()
    payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    remaining = payload["exp"] - time.time()
    assert 550 <= remaining <= 620  # 10 minutes ±1 min tolerance


def test_decode_token_defaults_to_access_type():
    """Existing callers that don't pass expected_type still work."""
    token = create_access_token(USER_ID, ORG_ID)
    payload = decode_token(token)  # no expected_type arg
    assert payload["sub"] == USER_ID
