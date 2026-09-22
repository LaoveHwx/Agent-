"""Shared-account authentication for the HTTP API."""

import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


_bearer = HTTPBearer(auto_error=False)
_token_lifetime_seconds = 12 * 60 * 60


def _credentials() -> tuple[str, str, str]:
    username = os.getenv("APP_USERNAME", "")
    password = os.getenv("APP_PASSWORD", "")
    secret = os.getenv("SECRET_KEY", "")
    if not username or not password or len(secret) < 32:
        raise RuntimeError("Set APP_USERNAME, APP_PASSWORD and a SECRET_KEY of at least 32 characters")
    return username, password, secret


def authenticate(username: str, password: str) -> str | None:
    expected_username, expected_password, secret = _credentials()
    username_ok = hmac.compare_digest(username.encode(), expected_username.encode())
    password_ok = hmac.compare_digest(password.encode(), expected_password.encode())
    if not (username_ok and password_ok):
        return None

    payload = json.dumps(
        {"sub": expected_username, "exp": int(time.time()) + _token_lifetime_seconds},
        separators=(",", ":"),
    ).encode()
    encoded = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
    signature = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def require_auth(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="请先登录")
    try:
        username, _, secret = _credentials()
        encoded, signature = credentials.credentials.split(".", 1)
        expected = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("bad signature")
        raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        payload = json.loads(raw)
        if payload.get("sub") != username or int(payload.get("exp", 0)) <= time.time():
            raise ValueError("expired or invalid token")
        return username
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, RuntimeError):
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录") from None

