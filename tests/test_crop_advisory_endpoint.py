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


def test_crop_advisory_for_farm_with_crops(client):
    token = _register_and_token(client, "cropadvisory@example.com")
    farm = client.post(
        "/farms",
        json={"name": "Farm", "gram_panchayat": "Bethupalli"},
        headers=_auth_headers(token),
    ).json()
    client.post(
        "/crops",
        json={"farm_id": farm["id"], "crop_name": "Cotton", "stage": "Flowering"},
        headers=_auth_headers(token),
    )

    resp = client.get(f"/farms/{farm['id']}/crop-advisory", headers=_auth_headers(token))
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["crop_name"] == "Cotton"
    assert results[0]["stage"] == "Flowering"
    assert results[0]["severity"] in ("critical", "warning", "safe")


def test_crop_advisory_requires_ownership(client):
    token_a = _register_and_token(client, "advisory.a@example.com")
    token_b = _register_and_token(client, "advisory.b@example.com")
    farm = client.post(
        "/farms",
        json={"name": "Farm", "gram_panchayat": "Bethupalli"},
        headers=_auth_headers(token_a),
    ).json()

    resp = client.get(f"/farms/{farm['id']}/crop-advisory", headers=_auth_headers(token_b))
    assert resp.status_code == 404


def test_crop_advisory_empty_when_no_crops(client):
    token = _register_and_token(client, "nocrops@example.com")
    farm = client.post(
        "/farms",
        json={"name": "Farm", "gram_panchayat": "Bethupalli"},
        headers=_auth_headers(token),
    ).json()

    resp = client.get(f"/farms/{farm['id']}/crop-advisory", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert resp.json() == []
