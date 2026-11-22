from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError

from app.api.v1.cookies import REFRESH_COOKIE, clear_refresh_cookie, set_refresh_cookie
from app.api.v1.deps import DbSession, limit_by_ip
from app.core.config import settings
from app.core.rate_limit import login_limiter, register_limiter
from app.core.security import create_access_token
from app.models import User
from app.schemas.auth import RegisterRequest, TokenResponse
from app.schemas.user import UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[limit_by_ip(register_limiter)],
)
def register(payload: RegisterRequest, db: DbSession) -> User:
    try:
        return auth_service.create_user(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists") from None


@router.post("/login", response_model=TokenResponse, dependencies=[limit_by_ip(login_limiter)])
def login(
    response: Response,
    db: DbSession,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    """Log in with form fields `username` (your email) and `password`."""
    user = auth_service.authenticate(db, form.username, form.password)
    if user is None:
        # Same message whether the email or the password is wrong
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    set_refresh_cookie(response, auth_service.issue_refresh_token(db, user.id))
    return _token_response(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(response: Response, db: DbSession, refresh_token: RefreshCookie = None):
    """Swap the refresh-token cookie for a new access token (and a new cookie)."""
    result = auth_service.rotate_refresh_token(db, refresh_token) if refresh_token else None
    if result is None:
        error = JSONResponse({"detail": "Session expired. Please log in again."}, status_code=401)
        clear_refresh_cookie(error)
        return error

    user, new_refresh_token = result
    set_refresh_cookie(response, new_refresh_token)
    return _token_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, db: DbSession, refresh_token: RefreshCookie = None) -> None:
    if refresh_token:
        auth_service.revoke_refresh_token(db, refresh_token)
    clear_refresh_cookie(response)
