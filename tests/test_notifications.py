import pytest
from fastapi.testclient import TestClient

from api import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _register_and_token(client, email: str) -> str:
    client.post("/auth/register", json={"name": "Test User", "email": email, "password": "farmer123"})
    resp = client.post("/auth/login", json={"identifier": email, "password": "farmer123"})
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_notifications_generated_from_farm_alerts(client):
    token = _register_and_token(client, "notif@example.com")
    client.post(
        "/farms",
        json={"name": "Farm", "gram_panchayat": "Bethupalli"},
        headers=_auth_headers(token),
    )

    resp = client.get("/notifications", headers=_auth_headers(token))
    assert resp.status_code == 200
    notifications = resp.json()
    assert len(notifications) > 0
    assert all(n["read"] is False for n in notifications)


def test_notifications_are_deduped_on_repeated_calls(client):
    token = _register_and_token(client, "notifdedupe@example.com")
    client.post(
        "/farms",
        json={"name": "Farm", "gram_panchayat": "Bethupalli"},
        headers=_auth_headers(token),
    )

    first = client.get("/notifications", headers=_auth_headers(token)).json()
    second = client.get("/notifications", headers=_auth_headers(token)).json()
    assert len(first) == len(second)


def test_notifications_isolated_per_user(client):
    token_a = _register_and_token(client, "notif.a@example.com")
    token_b = _register_and_token(client, "notif.b@example.com")
    client.post(
        "/farms",
        json={"name": "Farm", "gram_panchayat": "Bethupalli"},
        headers=_auth_headers(token_a),
    )

    resp_a = client.get("/notifications", headers=_auth_headers(token_a)).json()
    resp_b = client.get("/notifications", headers=_auth_headers(token_b)).json()
    assert len(resp_a) > 0
    assert len(resp_b) == 0


def test_mark_notification_read(client):
    token = _register_and_token(client, "notifread@example.com")
    client.post(
        "/farms",
        json={"name": "Farm", "gram_panchayat": "Bethupalli"},
        headers=_auth_headers(token),
    )
    notifications = client.get("/notifications", headers=_auth_headers(token)).json()
    notification_id = notifications[0]["id"]

    resp = client.post(f"/notifications/{notification_id}/read", headers=_auth_headers(token))
    assert resp.status_code == 200

    refreshed = client.get("/notifications", headers=_auth_headers(token)).json()
    updated = next(n for n in refreshed if n["id"] == notification_id)
    assert updated["read"] is True


def test_mark_notification_read_requires_ownership(client):
    token_a = _register_and_token(client, "notifown.a@example.com")
    token_b = _register_and_token(client, "notifown.b@example.com")
    client.post(
        "/farms",
        json={"name": "Farm", "gram_panchayat": "Bethupalli"},
        headers=_auth_headers(token_a),
    )
    notifications = client.get("/notifications", headers=_auth_headers(token_a)).json()
    notification_id = notifications[0]["id"]

    resp = client.post(f"/notifications/{notification_id}/read", headers=_auth_headers(token_b))
    assert resp.status_code == 404


def test_mark_all_read(client):
    token = _register_and_token(client, "notifreadall@example.com")
    client.post(
        "/farms",
        json={"name": "Farm", "gram_panchayat": "Bethupalli"},
        headers=_auth_headers(token),
    )
    client.get("/notifications", headers=_auth_headers(token))

    resp = client.post("/notifications/read-all", headers=_auth_headers(token))
    assert resp.status_code == 200

    refreshed = client.get("/notifications", headers=_auth_headers(token)).json()
    assert all(n["read"] is True for n in refreshed)


def test_no_farms_means_no_notifications(client):
    token = _register_and_token(client, "nofarms@example.com")
    resp = client.get("/notifications", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert resp.json() == []
