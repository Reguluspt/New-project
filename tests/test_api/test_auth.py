"""Tests for authentication endpoints."""

import datetime

import jwt
import pytest


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("status") == "ok"


def test_login_success(client):
    resp = client.post("/api/auth/login", json={"username": "truongpnt", "password": "Cen2026"})
    assert resp.status_code == 200
    data = resp.get_json()
    # Response wraps user info under "user" key
    assert "user" in data
    assert data["user"].get("username") == "truongpnt"
    # Cookie must be set
    cookie = resp.headers.get("Set-Cookie", "")
    assert "thamdinh_auth" in cookie


def test_secret_key_is_stable_across_app_restarts(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "stable-test-secret-key")

    from api import create_app

    first_app = create_app()
    second_app = create_app()

    token = jwt.encode(
        {
            "sub": "tester",
            "role": "admin",
            "exp": datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(minutes=5),
        },
        first_app.config["SECRET_KEY"],
        algorithm="HS256",
    )

    with second_app.test_client() as restarted_client:
        restarted_client.set_cookie("thamdinh_auth", token)
        response = restarted_client.get("/api/auth/me")

    assert response.status_code == 200


def test_missing_secret_key_prevents_api_startup(monkeypatch):
    import api

    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setattr(api, "load_dotenv", lambda *args, **kwargs: False)

    with pytest.raises(RuntimeError, match="SECRET_KEY must be configured"):
        api.create_app()


def test_login_wrong_password(client):
    resp = client.post("/api/auth/login", json={"username": "truongpnt", "password": "wrong"})
    assert resp.status_code == 401


def test_login_missing_fields(client):
    # Missing password → treated as wrong credentials
    resp = client.post("/api/auth/login", json={"username": "truongpnt"})
    assert resp.status_code in (400, 401)


def test_me_authenticated(auth_client):
    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "user" in data
    assert "username" in data["user"]


def test_me_unauthenticated(client):
    # Fresh client with no cookies → must get 401
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_logout(auth_client):
    resp = auth_client.post("/api/auth/logout")
    assert resp.status_code == 200
