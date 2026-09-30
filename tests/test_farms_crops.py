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


def test_locations_hierarchy(client):
    assert client.get("/locations/states").json() == ["Telangana"]
    assert client.get("/locations/districts", params={"state": "Telangana"}).json() == ["Khammam"]
    assert client.get("/locations/blocks", params={"state": "Telangana", "district": "Khammam"}).json() == [
        "Sathupally"
    ]

    panchayats = client.get(
        "/locations/panchayats", params={"state": "Telangana", "district": "Khammam", "block": "Sathupally"}
    ).json()
    assert len(panchayats) == 21
    assert "Bethupalli" in panchayats

    villages = client.get(
        "/locations/villages",
        params={"state": "Telangana", "district": "Khammam", "block": "Sathupally", "gram_panchayat": "Bethupalli"},
    ).json()
    assert "Bethupalle" in villages


def test_crop_catalog_exposed(client):
    crops = client.get("/locations/crops").json()
    names = [c["name"] for c in crops]
    assert "Cotton" in names


def test_farm_crud_and_ownership_isolation(client):
    token_a = _register_and_token(client, "farmer.a@example.com")
    token_b = _register_and_token(client, "farmer.b@example.com")

    resp = client.post(
        "/farms",
        json={"name": "A's Cotton Field", "gram_panchayat": "Bethupalli", "area_value": 3.5},
        headers=_auth_headers(token_a),
    )
    assert resp.status_code == 201
    farm = resp.json()
    farm_id = farm["id"]
    assert farm["owner_id"]

    # Owner can list/read/update it.
    listed = client.get("/farms", headers=_auth_headers(token_a)).json()
    assert len(listed) == 1

    resp = client.patch(
        f"/farms/{farm_id}", json={"area_value": 4.0}, headers=_auth_headers(token_a)
    )
    assert resp.status_code == 200
    assert resp.json()["area_value"] == 4.0

    # A different user cannot see or modify it.
    resp = client.get(f"/farms/{farm_id}", headers=_auth_headers(token_b))
    assert resp.status_code == 404
    resp = client.patch(f"/farms/{farm_id}", json={"area_value": 99}, headers=_auth_headers(token_b))
    assert resp.status_code == 404
    assert client.get("/farms", headers=_auth_headers(token_b)).json() == []

    # Delete works for the owner.
    resp = client.delete(f"/farms/{farm_id}", headers=_auth_headers(token_a))
    assert resp.status_code == 204
    assert client.get("/farms", headers=_auth_headers(token_a)).json() == []


def test_crop_crud_requires_owning_the_farm(client):
    token_a = _register_and_token(client, "cropowner.a@example.com")
    token_b = _register_and_token(client, "cropowner.b@example.com")

    farm = client.post(
        "/farms",
        json={"name": "A's Farm", "gram_panchayat": "Thumburu"},
        headers=_auth_headers(token_a),
    ).json()

    # Can't create a crop on someone else's farm.
    resp = client.post(
        "/crops",
        json={"farm_id": farm["id"], "crop_name": "Cotton", "stage": "Flowering"},
        headers=_auth_headers(token_b),
    )
    assert resp.status_code == 404

    resp = client.post(
        "/crops",
        json={"farm_id": farm["id"], "crop_name": "Cotton", "stage": "Flowering"},
        headers=_auth_headers(token_a),
    )
    assert resp.status_code == 201
    crop = resp.json()

    assert client.get("/crops", params={"farm_id": farm["id"]}, headers=_auth_headers(token_a)).json()
    assert client.get("/crops", headers=_auth_headers(token_b)).json() == []

    resp = client.patch(f"/crops/{crop['id']}", json={"stage": "Boll Formation"}, headers=_auth_headers(token_a))
    assert resp.status_code == 200
    assert resp.json()["stage"] == "Boll Formation"

    resp = client.delete(f"/crops/{crop['id']}", headers=_auth_headers(token_b))
    assert resp.status_code == 404

    resp = client.delete(f"/crops/{crop['id']}", headers=_auth_headers(token_a))
    assert resp.status_code == 204


def test_unknown_crop_name_rejected(client):
    token = _register_and_token(client, "badcrop@example.com")
    farm = client.post(
        "/farms", json={"name": "Farm", "gram_panchayat": "Rejerla"}, headers=_auth_headers(token)
    ).json()
    resp = client.post(
        "/crops",
        json={"farm_id": farm["id"], "crop_name": "Dragonfruit"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 422
