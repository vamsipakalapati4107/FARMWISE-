import pytest
from fastapi.testclient import TestClient

from api import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_register_and_login(client):
    resp = client.post(
        "/auth/register",
        json={"name": "Ravi Kumar", "email": "ravi.test@example.com", "password": "farmer123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Ravi Kumar"
    assert body["email"] == "ravi.test@example.com"

    resp = client.post(
        "/auth/login",
        json={"identifier": "ravi.test@example.com", "password": "farmer123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert token

    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "ravi.test@example.com"


def test_new_user_has_no_saved_location(client):
    client.post("/auth/register", json={"name": "New User", "email": "newloc.test@example.com", "password": "farmer123"})
    token = client.post(
        "/auth/login", json={"identifier": "newloc.test@example.com", "password": "farmer123"}
    ).json()["access_token"]

    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    body = resp.json()
    assert body["selected_state"] is None
    assert body["selected_district"] is None
    assert body["selected_block"] is None


def test_save_and_persist_selected_location(client):
    client.post("/auth/register", json={"name": "Loc User", "email": "loc.test@example.com", "password": "farmer123"})
    token = client.post(
        "/auth/login", json={"identifier": "loc.test@example.com", "password": "farmer123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.patch(
        "/auth/me",
        json={"selected_state": "Telangana", "selected_district": "Khammam", "selected_block": "Sathupally"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["selected_block"] == "Sathupally"

    # Persists across a fresh /auth/me read (not just the PATCH response).
    resp2 = client.get("/auth/me", headers=headers)
    assert resp2.json()["selected_district"] == "Khammam"
    assert resp2.json()["selected_block"] == "Sathupally"


def test_duplicate_email_rejected(client):
    payload = {"name": "Dupe", "email": "dupe.test@example.com", "password": "farmer123"}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201
    second = client.post("/auth/register", json=payload)
    assert second.status_code == 400


def test_wrong_password_rejected(client):
    client.post(
        "/auth/register",
        json={"name": "Wrong Pw", "email": "wrongpw.test@example.com", "password": "farmer123"},
    )
    resp = client.post(
        "/auth/login",
        json={"identifier": "wrongpw.test@example.com", "password": "not-the-password"},
    )
    assert resp.status_code == 401


def test_password_too_short_rejected(client):
    resp = client.post(
        "/auth/register",
        json={"name": "Short Pw", "email": "shortpw.test@example.com", "password": "abc"},
    )
    assert resp.status_code == 422


def test_protected_route_requires_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_protected_route_rejects_garbage_token(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_forgot_password_flow(client, capsys):
    client.post(
        "/auth/register",
        json={"name": "Reset Me", "email": "resetme.test@example.com", "password": "farmer123"},
    )
    resp = client.post("/auth/forgot-password", json={"identifier": "resetme.test@example.com"})
    assert resp.status_code == 202

    printed = capsys.readouterr().out
    token = printed.split("token=")[1].strip()

    resp = client.post("/auth/reset-password", json={"token": token, "new_password": "newpassword1"})
    assert resp.status_code == 200

    resp = client.post(
        "/auth/login",
        json={"identifier": "resetme.test@example.com", "password": "newpassword1"},
    )
    assert resp.status_code == 200


def test_forgot_password_unknown_identifier_does_not_leak(client):
    resp = client.post("/auth/forgot-password", json={"identifier": "nobody.test@example.com"})
    assert resp.status_code == 202
