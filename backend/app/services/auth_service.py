import logging
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.config import settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models import RefreshToken, User
from app.schemas.auth import RegisterRequest

logger = logging.getLogger(__name__)

# Two browser tabs may refresh with the same token at the same moment. Within this window
# that is treated as a race, not as theft.
REUSE_GRACE_PERIOD = timedelta(seconds=10)


def create_user(db: Session, data: RegisterRequest) -> User:
    """Raises sqlalchemy IntegrityError if the email is already registered."""
    user = User(email=data.email, full_name=data.full_name, hashed_password=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)  # same timing as a real check
        return None
    if not verify_password(password, user.hashed_password) or not user.is_active:
        return None
    return user


def issue_refresh_token(db: Session, user_id: int) -> str:
    """Create a new session and return the raw token (only its hash is stored)."""
    raw_token = _add_refresh_token(db, user_id)
    db.commit()
    return raw_token


def rotate_refresh_token(db: Session, raw_token: str) -> tuple[User, str] | None:
    """Exchange a valid refresh token for a new one. Returns None if it is not valid.

    Each refresh token works once. If an already-used token comes back, someone may
    have stolen it, so every session of that user is revoked.
    """
    token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token)))
    if token is None:
        return None

    now = utcnow()
    if token.revoked_at is not None:
        if now - token.revoked_at > REUSE_GRACE_PERIOD:
            logger.warning("Refresh token reuse detected for user %s; revoking all sessions", token.user_id)
            revoke_all_refresh_tokens(db, token.user_id)
        return None

    if token.expires_at <= now or not token.user.is_active:
        return None

    token.revoked_at = now
    new_raw_token = _add_refresh_token(db, token.user_id)
    db.commit()
    return token.user, new_raw_token


def revoke_refresh_token(db: Session, raw_token: str) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == hash_token(raw_token), RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    db.commit()


def revoke_all_refresh_tokens(db: Session, user_id: int) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    db.commit()


def _add_refresh_token(db: Session, user_id: int) -> str:
    raw_token = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_token(raw_token),
            expires_at=utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    return raw_token
