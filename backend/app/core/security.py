import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

# Argon2id: a slow, memory-hard hash, so stolen hashes are expensive to brute-force.
password_hasher = PasswordHash.recommended()

# Used when a login email does not exist, so the response takes as long as a real
# password check and attackers cannot discover which emails are registered.
DUMMY_PASSWORD_HASH = password_hasher.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hasher.verify(password, hashed_password)


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Return the user id if the token is valid, unexpired and an access token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],  # never let the token choose its own algorithm
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.InvalidTokenError:
        return None

    if payload["type"] != "access":
        return None
    try:
        return int(payload["sub"])
    except ValueError:
        return None


def generate_refresh_token() -> str:
    # Refresh tokens are random strings, not JWTs: the database decides if they are valid.
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    # Only the SHA-256 of a refresh token is stored, so a database leak does not leak sessions.
    return hashlib.sha256(token.encode()).hexdigest()
