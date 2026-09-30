import datetime as dt

import numpy as np
import pytest
from fastapi.testclient import TestClient

import api as api_module
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


def _make_plot(client, token: str, gp: str) -> tuple[str, str]:
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": gp}, headers=_auth_headers(token)).json()
    plot = client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot"}, headers=_auth_headers(token)).json()
    return farm["id"], plot["id"]


def _today() -> str:
    return dt.date.today().isoformat()


def _set_todays_weather(gram_panchayat: str, rainfall_mm, temp_max_c, rh_max_pct):
    df = api_module.state["forecast"]
    mask = (df["gram_panchayat"] == gram_panchayat) & (df["date"] == _today())
    assert mask.any(), f"no row for {gram_panchayat} on {_today()}"
    df.loc[mask, "rainfall_mm"] = rainfall_mm
    df.loc[mask, "temp_max_c"] = temp_max_c
    df.loc[mask, "rh_max_pct"] = rh_max_pct


def test_health_available_with_real_weather(client):
    token = _register_and_token(client, "health1@example.com")
    _set_todays_weather("Buggapadu", rainfall_mm=2, temp_max_c=28, rh_max_pct=50)
    _, plot_id = _make_plot(client, token, "Buggapadu")

    resp = client.get(f"/plots/{plot_id}/crop-health", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["health"]["available"] is True
    assert body["health"]["status"] == "GOOD"
    assert body["health"]["source_type"] == "derived_assessment"
    assert "value" not in body["health"]  # never a fabricated numeric score


def test_health_never_labeled_as_ml_prediction(client):
    token = _register_and_token(client, "health2@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/crop-health", headers=_auth_headers(token))
    body = resp.json()
    assert body["health"]["source_type"] != "ml_prediction"
    assert body["stress"]["source_type"] == "unavailable"
    assert body["stress"]["available"] is False


def test_health_missing_weather_data(client):
    token = _register_and_token(client, "health3@example.com")
    _set_todays_weather("Rejerla", rainfall_mm=np.nan, temp_max_c=np.nan, rh_max_pct=np.nan)
    _, plot_id = _make_plot(client, token, "Rejerla")

    resp = client.get(f"/plots/{plot_id}/crop-health", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["health"]["available"] is False
    assert body["health"]["source_type"] == "unavailable"
    temp_factor = next(f for f in body["factors"] if f["key"] == "temperature")
    assert temp_factor["available"] is False
    assert temp_factor["value"] is None


def test_health_missing_soil_data_always_unavailable(client):
    token = _register_and_token(client, "health4@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/crop-health", headers=_auth_headers(token))
    body = resp.json()
    soil_factor = next(f for f in body["factors"] if f["key"] == "soil_moisture")
    assert soil_factor["available"] is False
    assert soil_factor["status"] == "Unknown"
    assert soil_factor["source_type"] == "unavailable"


def test_health_missing_plot_returns_404(client):
    token = _register_and_token(client, "health5@example.com")
    resp = client.get("/plots/nonexistent-id/crop-health", headers=_auth_headers(token))
    assert resp.status_code == 404


def test_health_missing_historical_data(client):
    token = _register_and_token(client, "health6@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/crop-health", headers=_auth_headers(token))
    body = resp.json()
    assert body["health_trend"]["available"] is False
    assert "historical" in body["health_trend"]["reason"].lower()


def test_source_type_classification_for_rainfall(client):
    token = _register_and_token(client, "health7@example.com")
    farm_id, plot_id = _make_plot(client, token, "Bethupalli")
    # No coordinates -> GP-level -> real ML model output.
    resp = client.get(f"/plots/{plot_id}/crop-health", headers=_auth_headers(token))
    rainfall_factor = next(f for f in resp.json()["factors"] if f["key"] == "rainfall")
    assert rainfall_factor["source_type"] == "ml_prediction"

    # Add coordinates -> spatial estimate applies.
    client.patch(f"/plots/{plot_id}", json={"latitude": 17.2, "longitude": 80.86}, headers=_auth_headers(token))
    resp2 = client.get(f"/plots/{plot_id}/crop-health", headers=_auth_headers(token))
    rainfall_factor2 = next(f for f in resp2.json()["factors"] if f["key"] == "rainfall")
    assert rainfall_factor2["source_type"] == "spatial_estimation"


def test_explanation_always_honest(client):
    token = _register_and_token(client, "health8@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/crop-health", headers=_auth_headers(token))
    body = resp.json()
    assert body["explanation"]["available"] is False


def test_phase1_farm_advisor_still_works_after_phase2(client):
    token = _register_and_token(client, "health9@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/farm-advisor", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert "recommendations" in body
    assert len(body["recommendations"]) == 6


def test_phase05_health_stub_still_untouched(client):
    token = _register_and_token(client, "health10@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/health", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["classification"] == "NOT_AVAILABLE"


def test_crop_health_with_linked_crop(client):
    token = _register_and_token(client, "health11@example.com")
    farm_id, plot_id = _make_plot(client, token, "Bethupalli")
    client.post(
        "/crops",
        json={"farm_id": farm_id, "plot_id": plot_id, "crop_name": "Cotton", "stage": "Flowering"},
        headers=_auth_headers(token),
    )

    resp = client.get(f"/plots/{plot_id}/crop-health", headers=_auth_headers(token))
    body = resp.json()
    assert body["crop"]["crop_name"] == "Cotton"
    growth_factor = next(f for f in body["factors"] if f["key"] == "growth_stage")
    assert growth_factor["value"] == "Flowering"
    assert growth_factor["available"] is True


def test_crop_health_requires_ownership(client):
    token_a = _register_and_token(client, "healthowner.a@example.com")
    token_b = _register_and_token(client, "healthowner.b@example.com")
    _, plot_id = _make_plot(client, token_a, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/crop-health", headers=_auth_headers(token_b))
    assert resp.status_code == 404
