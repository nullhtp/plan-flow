from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jose import jwt

from app.core.config import settings
from app.core.security import (
    JWTError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_roundtrip() -> None:
    """Hashed password should verify against the original."""
    raw = "my-secret-password"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed)


def test_verify_password_wrong() -> None:
    """Wrong password should not verify."""
    hashed = hash_password("correct-password")
    assert not verify_password("wrong-password", hashed)


def test_create_access_token() -> None:
    """Access token should contain sub, type, and exp."""
    token = create_access_token("user-123")
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_create_refresh_token() -> None:
    """Refresh token should contain sub, type, and exp."""
    token = create_refresh_token("user-456")
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    assert payload["sub"] == "user-456"
    assert payload["type"] == "refresh"
    assert "exp" in payload


def test_decode_token_valid() -> None:
    """Valid token should decode correctly."""
    token = create_access_token("user-789")
    payload = decode_token(token)
    assert payload["sub"] == "user-789"


def test_decode_token_expired() -> None:
    """Expired token should raise JWTError."""
    expire = datetime.now(UTC) - timedelta(hours=1)
    payload = {"sub": "user-expired", "exp": expire, "type": "access"}
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")

    try:
        decode_token(token)
        raise AssertionError("Expected JWTError")
    except JWTError:
        pass


def test_decode_token_invalid_signature() -> None:
    """Token with wrong key should raise JWTError."""
    payload = {"sub": "user-bad", "type": "access"}
    token = jwt.encode(payload, "wrong-secret-key", algorithm="HS256")

    try:
        decode_token(token)
        raise AssertionError("Expected JWTError")
    except JWTError:
        pass
