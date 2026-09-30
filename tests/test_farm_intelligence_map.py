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


def _today() -> str:
    return dt.date.today().isoformat()


def _set_todays_weather(gram_panchayat: str, rainfall_mm, temp_max_c, rh_max_pct):
    df = api_module.state["forecast"]
    mask = (df["gram_panchayat"] == gram_panchayat) & (df["date"] == _today())
    assert mask.any()
    df.loc[mask, "rainfall_mm"] = rainfall_mm
    df.loc[mask, "temp_max_c"] = temp_max_c
    df.loc[mask, "rh_max_pct"] = rh_max_pct


def test_farm_with_valid_coordinates_does_not_affect_plot_resolution(client):
    token = _register_and_token(client, "map1@example.com")
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": "Bethupalli"}, headers=_auth_headers(token)).json()
    client.patch(f"/farms/{farm['id']}", json={"latitude": 17.19, "longitude": 80.88}, headers=_auth_headers(token))
    client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token))

    resp = client.get("/plots/intelligence", headers=_auth_headers(token))
    assert resp.status_code == 200
    entry = resp.json()[0]
    assert entry["location_configured"] is False  # plot itself has no coords
    assert entry["weather"]["rainfall_mm"]["source"] == "gp_level"


def test_plot_with_valid_coordinates_uses_spatial_estimate(client):
    token = _register_and_token(client, "map2@example.com")
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": "Bethupalli"}, headers=_auth_headers(token)).json()
    client.post(
        f"/farms/{farm['id']}/plots",
        json={"name": "Plot A", "latitude": 17.205, "longitude": 80.895},
        headers=_auth_headers(token),
    )

    resp = client.get("/plots/intelligence", headers=_auth_headers(token))
    entry = resp.json()[0]
    assert entry["location_configured"] is True
    assert entry["weather"]["rainfall_mm"]["source"] == "estimated_downscaled"
    assert entry["sources"]["spatial_estimation_used"] is True
    assert "Plot-level estimate" in entry["sources"]["resolution"]


def test_plot_without_coordinates_shows_gp_level_not_invented(client):
    token = _register_and_token(client, "map3@example.com")
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": "Bethupalli"}, headers=_auth_headers(token)).json()
    client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token))

    resp = client.get("/plots/intelligence", headers=_auth_headers(token))
    entry = resp.json()[0]
    assert entry["latitude"] is None
    assert entry["longitude"] is None
    assert entry["location_configured"] is False
    assert "Gram Panchayat-level" in entry["sources"]["resolution"]


def test_disease_risk_field_present_and_correctly_classified(client):
    token = _register_and_token(client, "map4@example.com")
    _set_todays_weather("Kothuru", rainfall_mm=10, temp_max_c=30, rh_max_pct=90)
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": "Kothuru"}, headers=_auth_headers(token)).json()
    client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token))

    resp = client.get("/plots/intelligence", headers=_auth_headers(token))
    entry = resp.json()[0]
    assert entry["disease_risk"]["level"] == "MEDIUM"
    assert entry["disease_risk"]["classification"] == "RULE_BASED_LOGIC"


def test_crop_health_field_present(client):
    token = _register_and_token(client, "map5@example.com")
    _set_todays_weather("Gowrigudem", rainfall_mm=2, temp_max_c=28, rh_max_pct=50)
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": "Gowrigudem"}, headers=_auth_headers(token)).json()
    client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token))

    resp = client.get("/plots/intelligence", headers=_auth_headers(token))
    entry = resp.json()[0]
    assert entry["health"]["status"] == "GOOD"
    assert entry["health"]["source_type"] == "derived_assessment"


def test_weather_layer_fields_present(client):
    token = _register_and_token(client, "map6@example.com")
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": "Bethupalli"}, headers=_auth_headers(token)).json()
    client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token))

    resp = client.get("/plots/intelligence", headers=_auth_headers(token))
    entry = resp.json()[0]
    assert set(entry["weather"].keys()) == {"temp_max_c", "rh_max_pct", "rainfall_mm"}
    assert entry["weather"]["temp_max_c"]["source"] == "pass_through"


def test_missing_rainfall_data_handled_gracefully(client):
    token = _register_and_token(client, "map7@example.com")
    _set_todays_weather("Rejerla", rainfall_mm=np.nan, temp_max_c=30, rh_max_pct=50)
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": "Rejerla"}, headers=_auth_headers(token)).json()
    client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token))

    resp = client.get("/plots/intelligence", headers=_auth_headers(token))
    assert resp.status_code == 200
    entry = resp.json()[0]
    assert entry["weather"]["rainfall_mm"]["value"] is None
    assert entry["disease_risk"]["available"] is False  # can't assess without rainfall


def test_missing_all_weather_data_handled_gracefully(client):
    token = _register_and_token(client, "map8@example.com")
    _set_todays_weather("Siddaram", rainfall_mm=np.nan, temp_max_c=np.nan, rh_max_pct=np.nan)
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": "Siddaram"}, headers=_auth_headers(token)).json()
    client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token))

    resp = client.get("/plots/intelligence", headers=_auth_headers(token))
    assert resp.status_code == 200
    entry = resp.json()[0]
    assert entry["health"]["available"] is False
    assert entry["weather_risk"]["available"] is False


def test_intelligence_endpoint_returns_all_users_plots_in_one_call(client):
    token = _register_and_token(client, "map9@example.com")
    farm_a = client.post("/farms", json={"name": "Farm A", "gram_panchayat": "Bethupalli"}, headers=_auth_headers(token)).json()
    farm_b = client.post("/farms", json={"name": "Farm B", "gram_panchayat": "Buggapadu"}, headers=_auth_headers(token)).json()
    client.post(f"/farms/{farm_a['id']}/plots", json={"name": "Plot A1"}, headers=_auth_headers(token))
    client.post(f"/farms/{farm_a['id']}/plots", json={"name": "Plot A2"}, headers=_auth_headers(token))
    client.post(f"/farms/{farm_b['id']}/plots", json={"name": "Plot B1"}, headers=_auth_headers(token))

    resp = client.get("/plots/intelligence", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_intelligence_isolated_per_user(client):
    token_a = _register_and_token(client, "map10.a@example.com")
    token_b = _register_and_token(client, "map10.b@example.com")
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": "Bethupalli"}, headers=_auth_headers(token_a)).json()
    client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token_a))

    resp_a = client.get("/plots/intelligence", headers=_auth_headers(token_a))
    resp_b = client.get("/plots/intelligence", headers=_auth_headers(token_b))
    assert len(resp_a.json()) == 1
    assert len(resp_b.json()) == 0


def test_route_ordering_plots_intelligence_not_shadowed_by_plot_id(client):
    token = _register_and_token(client, "map11@example.com")
    resp = client.get("/plots/intelligence", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_real_plot_id_route_still_works_after_reordering(client):
    token = _register_and_token(client, "map12@example.com")
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": "Bethupalli"}, headers=_auth_headers(token)).json()
    plot = client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token)).json()

    resp = client.get(f"/plots/{plot['id']}", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["name"] == "Plot A"


def test_phase1_advisor_still_works(client):
    token = _register_and_token(client, "map13@example.com")
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": "Bethupalli"}, headers=_auth_headers(token)).json()
    plot = client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token)).json()

    resp = client.get(f"/plots/{plot['id']}/farm-advisor", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert len(resp.json()["recommendations"]) == 6


def test_phase2_crop_health_still_works(client):
    token = _register_and_token(client, "map14@example.com")
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": "Bethupalli"}, headers=_auth_headers(token)).json()
    plot = client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token)).json()

    resp = client.get(f"/plots/{plot['id']}/crop-health", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["stress"]["available"] is False
