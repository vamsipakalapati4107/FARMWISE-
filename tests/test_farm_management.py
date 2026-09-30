import pytest
from fastapi.testclient import TestClient

from api import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _register_and_token(client, email: str) -> str:
    client.post("/auth/register", json={"name": "Test Farmer", "email": email, "password": "farmer123"})
    resp = client.post("/auth/login", json={"identifier": email, "password": "farmer123"})
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_farm_plot_crop(client, token: str) -> tuple[str, str, str]:
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": "Bethupalli"}, headers=_auth_headers(token)).json()
    plot = client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot"}, headers=_auth_headers(token)).json()
    crop = client.post(
        "/crops",
        json={"farm_id": farm["id"], "plot_id": plot["id"], "crop_name": "Cotton", "stage": "Flowering"},
        headers=_auth_headers(token),
    ).json()
    return farm["id"], plot["id"], crop["id"]


# ---- Change crop (crops.py CropUpdate.crop_name) ----


def test_change_crop_name_via_patch(client):
    token = _register_and_token(client, "changecrop@example.com")
    _, _, crop_id = _make_farm_plot_crop(client, token)

    resp = client.patch(f"/crops/{crop_id}", json={"crop_name": "Paddy (Rice)", "stage": "Nursery"}, headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["crop_name"] == "Paddy (Rice)"
    assert body["stage"] == "Nursery"


def test_change_crop_rejects_unknown_crop(client):
    token = _register_and_token(client, "changecrop2@example.com")
    _, _, crop_id = _make_farm_plot_crop(client, token)

    resp = client.patch(f"/crops/{crop_id}", json={"crop_name": "Dragonfruit"}, headers=_auth_headers(token))
    assert resp.status_code == 422


# ---- Disease reports ----


def test_create_and_list_disease_report(client):
    token = _register_and_token(client, "disease1@example.com")
    farm_id, plot_id, crop_id = _make_farm_plot_crop(client, token)

    resp = client.post(
        "/disease-reports",
        json={
            "farm_id": farm_id,
            "plot_id": plot_id,
            "crop_id": crop_id,
            "observed_problem": "Yellowing leaves",
            "symptoms": "Yellow patches on lower leaves",
        },
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201
    report = resp.json()
    assert report["observed_problem"] == "Yellowing leaves"
    assert report["ai_guidance"] is None
    assert report["ai_source"] is None

    listed = client.get(f"/disease-reports?farm_id={farm_id}", headers=_auth_headers(token)).json()
    assert len(listed) == 1
    assert listed[0]["id"] == report["id"]


def test_analyze_disease_report_honestly_unavailable_without_gemini_key(client, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    token = _register_and_token(client, "disease2@example.com")
    farm_id, plot_id, crop_id = _make_farm_plot_crop(client, token)
    report = client.post(
        "/disease-reports",
        json={"farm_id": farm_id, "plot_id": plot_id, "crop_id": crop_id, "observed_problem": "Possible blast disease"},
        headers=_auth_headers(token),
    ).json()

    resp = client.post(f"/disease-reports/{report['id']}/analyze", headers=_auth_headers(token))
    assert resp.status_code == 503
    assert "not configured" in resp.json()["detail"]


def test_disease_report_requires_owned_farm(client):
    token_a = _register_and_token(client, "diseaseA@example.com")
    token_b = _register_and_token(client, "diseaseB@example.com")
    farm_id, _, _ = _make_farm_plot_crop(client, token_a)

    resp = client.post(
        "/disease-reports",
        json={"farm_id": farm_id, "observed_problem": "Wilting"},
        headers=_auth_headers(token_b),
    )
    assert resp.status_code == 404


# ---- Inspections ----


def test_create_and_list_inspection(client):
    token = _register_and_token(client, "inspect1@example.com")
    farm_id, plot_id, crop_id = _make_farm_plot_crop(client, token)

    resp = client.post(
        "/inspections",
        json={
            "farm_id": farm_id,
            "plot_id": plot_id,
            "crop_id": crop_id,
            "inspection_date": "2026-09-27",
            "observed_symptoms": "No visible symptoms",
            "crop_condition": "Healthy",
        },
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201
    assert resp.json()["crop_condition"] == "Healthy"

    listed = client.get(f"/inspections?farm_id={farm_id}", headers=_auth_headers(token)).json()
    assert len(listed) == 1


# ---- Farm activity log ----


def test_create_and_list_farm_activity(client):
    token = _register_and_token(client, "activity1@example.com")
    farm_id, plot_id, crop_id = _make_farm_plot_crop(client, token)

    resp = client.post(
        "/farm-activities",
        json={"farm_id": farm_id, "plot_id": plot_id, "crop_id": crop_id, "activity_type": "irrigation", "activity_date": "2026-09-27"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201

    listed = client.get(f"/farm-activities?farm_id={farm_id}", headers=_auth_headers(token)).json()
    assert len(listed) == 1
    assert listed[0]["activity_type"] == "irrigation"


def test_farm_activity_rejects_unknown_type(client):
    token = _register_and_token(client, "activity2@example.com")
    farm_id, _, _ = _make_farm_plot_crop(client, token)

    resp = client.post(
        "/farm-activities",
        json={"farm_id": farm_id, "activity_type": "dancing", "activity_date": "2026-09-27"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 422


def test_farm_activity_requires_owned_farm(client):
    token_a = _register_and_token(client, "activityA@example.com")
    token_b = _register_and_token(client, "activityB@example.com")
    farm_id, _, _ = _make_farm_plot_crop(client, token_a)

    resp = client.post(
        "/farm-activities",
        json={"farm_id": farm_id, "activity_type": "sowing", "activity_date": "2026-09-27"},
        headers=_auth_headers(token_b),
    )
    assert resp.status_code == 404
