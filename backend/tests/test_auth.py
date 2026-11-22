from datetime import timedelta

from sqlalchemy import update

from app.core.clock import utcnow
from app.core.security import hash_token
from app.models import RefreshToken
from app.services import auth_service
from tests.conftest import TEST_PASSWORD

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"


def register(client, email="asha@example.com", password=TEST_PASSWORD, full_name="Asha Rao"):
    return client.post(REGISTER_URL, json={"email": email, "full_name": full_name, "password": password})


def login(client, email="asha@example.com", password=TEST_PASSWORD):
    return client.post(LOGIN_URL, data={"username": email, "password": password})


def bearer(response):
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_register_creates_user_without_exposing_password(client):
    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "asha@example.com"
    assert body["preferred_language"] == "en"
    assert "password" not in body and "hashed_password" not in body
    assert body["created_at"].endswith("Z")


def test_register_normalizes_email_and_rejects_duplicates(client):
    assert register(client, email="  Asha@Example.COM ").status_code == 201

    response = register(client, email="asha@example.com")

    assert response.status_code == 409


def test_register_rejects_weak_passwords_and_bad_emails(client):
    assert register(client, password="short1").status_code == 422
    assert register(client, password="onlyletters").status_code == 422
    assert register(client, email="not-an-email").status_code == 422


def test_login_returns_access_token_and_httponly_refresh_cookie(client):
    register(client)

    response = login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "asha@example.com"
    set_cookie = response.headers["set-cookie"]
    assert "refresh_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Path=/api/v1/auth" in set_cookie


def test_login_fails_with_same_message_for_wrong_password_and_unknown_email(client):
    register(client)

    wrong_password = login(client, password="Wrong1234")
    unknown_email = login(client, email="nobody@example.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]


def test_protected_route_requires_valid_token(client):
    register(client)
    token_response = login(client)

    assert client.get("/api/v1/users/me").status_code == 401
    assert client.get("/api/v1/users/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    me = client.get("/api/v1/users/me", headers=bearer(token_response))
    assert me.status_code == 200
    assert me.json()["email"] == "asha@example.com"


def test_refresh_rotates_the_refresh_token(client):
    register(client)
    old_token = login(client).cookies["refresh_token"]

    response = client.post(REFRESH_URL)

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.cookies["refresh_token"] != old_token


def test_reusing_an_old_refresh_token_revokes_all_sessions(client, session_factory):
    register(client)
    old_token = login(client).cookies["refresh_token"]
    new_token = client.post(REFRESH_URL).cookies["refresh_token"]
    # Pretend the old token was rotated a minute ago, i.e. outside the grace period.
    with session_factory() as db:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == hash_token(old_token))
            .values(revoked_at=utcnow() - auth_service.REUSE_GRACE_PERIOD - timedelta(minutes=1))
        )
        db.commit()

    # An attacker replays the stolen, already-used token...
    client.cookies.clear()
    client.cookies.set("refresh_token", old_token)
    assert client.post(REFRESH_URL).status_code == 401

    # ...so the legitimate user's newest token is revoked too.
    client.cookies.clear()
    client.cookies.set("refresh_token", new_token)
    assert client.post(REFRESH_URL).status_code == 401


def test_concurrent_refresh_within_grace_period_does_not_log_user_out(client):
    register(client)
    old_token = login(client).cookies["refresh_token"]
    new_token = client.post(REFRESH_URL).cookies["refresh_token"]

    # A second browser tab immediately sends the old token: rejected, but not treated as theft.
    client.cookies.clear()
    client.cookies.set("refresh_token", old_token)
    assert client.post(REFRESH_URL).status_code == 401

    client.cookies.clear()
    client.cookies.set("refresh_token", new_token)
    assert client.post(REFRESH_URL).status_code == 200


def test_logout_revokes_the_session(client):
    register(client)
    login(client)

    assert client.post(LOGOUT_URL).status_code == 204
    assert client.post(REFRESH_URL).status_code == 401


def test_refresh_without_cookie_is_rejected(client):
    assert client.post(REFRESH_URL).status_code == 401


def test_update_profile(client):
    register(client)
    headers = bearer(login(client))

    response = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"full_name": "  Asha R  ", "preferred_language": "te"},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Asha R"
    assert response.json()["preferred_language"] == "te"
    bad_language = client.patch("/api/v1/users/me", headers=headers, json={"preferred_language": "fr"})
    assert bad_language.status_code == 422


def test_change_password(client):
    register(client)
    headers = bearer(login(client))
    url = "/api/v1/users/me/password"

    wrong = client.post(url, headers=headers, json={"current_password": "Wrong1234", "new_password": "NewPass123"})
    assert wrong.status_code == 400

    ok = client.post(url, headers=headers, json={"current_password": TEST_PASSWORD, "new_password": "NewPass123"})
    assert ok.status_code == 204
    assert login(client).status_code == 401
    assert login(client, password="NewPass123").status_code == 200
