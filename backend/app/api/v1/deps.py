from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import RateLimiter
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

# Reads "Authorization: Bearer <token>". tokenUrl powers the "Authorize" button in /docs.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_error

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


# Add `current_user: CurrentUser` to any route to require login.
CurrentUser = Annotated[User, Depends(get_current_user)]


def limit_by_ip(limiter: RateLimiter):
    """Dependency for anonymous endpoints (login, register): count requests per client IP."""

    def dependency(request: Request) -> None:
        limiter.check(f"ip:{request.client.host if request.client else 'unknown'}")

    return Depends(dependency)


def limit_by_user(limiter: RateLimiter):
    """Dependency for logged-in endpoints: count requests per user, wherever they connect from."""

    def dependency(current_user: CurrentUser) -> None:
        limiter.check(f"user:{current_user.id}")

    return Depends(dependency)
