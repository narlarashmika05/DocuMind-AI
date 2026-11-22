from fastapi import Response

from app.core.config import settings

REFRESH_COOKIE = "refresh_token"
# The browser sends the cookie only to /api/v1/auth/*, not with every API call.
REFRESH_COOKIE_PATH = f"{settings.API_V1_PREFIX}/auth"


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
        httponly=True,  # JavaScript cannot read it, so XSS cannot steal it
        secure=settings.is_production,  # HTTPS-only in production; local dev uses plain HTTP
        samesite="lax",  # not sent on cross-site POSTs, which blocks CSRF on /refresh
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )
