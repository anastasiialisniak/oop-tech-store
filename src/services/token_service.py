from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError

from src.config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

VALID_ROLES = {"Customer", "Admin"}


def create_access_token(
    user_id: int,
    role: str = "Customer",
    expires_delta: timedelta | None = None,
) -> str:
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("User ID must be a positive integer.")

    if not isinstance(role, str) or role not in VALID_ROLES:
        raise ValueError(f"Unsupported user role: '{role}'.")

    now = datetime.now(timezone.utc)
    delta = (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + delta,
    }

    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    return token


def verify_access_token(token: str) -> dict | None:
    if not isinstance(token, str) or not token.strip():
        return None

    try:
        payload = jwt.decode(
            token.strip(),
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]},
        )

        sub = payload.get("sub")
        if not isinstance(sub, str) or not sub.strip():
            return None

        user_id = int(sub)
        if user_id <= 0:
            return None

        role = payload.get("role")
        if role is not None and role not in VALID_ROLES:
            return None

        return payload

    except (InvalidTokenError, ValueError, TypeError):
        return None
