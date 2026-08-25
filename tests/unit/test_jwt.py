import time

import jwt as pyjwt
import pytest

from cka.infrastructure.security.jwt import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
)

SECRET = "test-secret-key"


def test_create_and_decode_round_trips_claims() -> None:
    token = create_access_token("user-123", "employee", SECRET, expire_minutes=30)

    payload = decode_access_token(token, SECRET)

    assert payload.user_id == "user-123"
    assert payload.role == "employee"


def test_decode_rejects_wrong_secret() -> None:
    token = create_access_token("user-123", "employee", SECRET, expire_minutes=30)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, "a-different-secret")


def test_decode_rejects_expired_token() -> None:
    token = create_access_token("user-123", "employee", SECRET, expire_minutes=0)
    time.sleep(1.1)  # ensure exp (whole-second resolution) is in the past

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, SECRET)


def test_decode_rejects_malformed_token() -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token("not-a-real-token", SECRET)


def test_decode_rejects_token_missing_role_claim() -> None:
    # A token an attacker forged without going through create_access_token
    # (e.g. missing a required claim) must be rejected, not crash the app.
    token = pyjwt.encode({"sub": "user-123"}, SECRET, algorithm="HS256")

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, SECRET)
