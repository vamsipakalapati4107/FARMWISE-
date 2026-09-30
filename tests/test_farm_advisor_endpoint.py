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


def _make_plot(client, token: str, gp: str) -> str:
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": gp}, headers=_auth_headers(token)).json()
    plot = client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot"}, headers=_auth_headers(token)).json()
    return plot["id"]


def _today() -> str:
    return dt.date.today().isoformat()


def _set_todays_weather(gram_panchayat: str, rainfall_mm, temp_max_c, rh_max_pct):
    """Overwrite today's forecast row for one GP in the live in-memory
    state, so we can exercise scenarios (heavy rain, missing data) that
    may not occur in the real fixed 5-day forecast for every GP."""
    df = api_module.state["forecast"]
    mask = (df["gram_panchayat"] == gram_panchayat) & (df["date"] == _today())
    assert mask.any(), f"no row for {gram_panchayat} on {_today()} -- fixture assumption broken"
    df.loc[mask, "rainfall_mm"] = rainfall_mm
    df.loc[mask, "temp_max_c"] = temp_max_c
    df.loc[mask, "rh_max_pct"] = rh_max_pct


def test_advisor_normal_weather(client):
    token = _register_and_token(client, "advisornormal@example.com")
    _set_todays_weather("Buggapadu", rainfall_mm=2, temp_max_c=28, rh_max_pct=50)
    plot_id = _make_plot(client, token, "Buggapadu")

    resp = client.get(f"/plots/{plot_id}/farm-advisor", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert all(r["status"] == "normal" for r in body["recommendations"])
    assert body["action_plan"] == []
    assert body["disease_risk"]["level"] == "LOW"
    assert body["weather_risk"]["level"] == "LOW"


def test_advisor_high_rainfall(client):
    token = _register_and_token(client, "advisorrain@example.com")
    _set_todays_weather("Gowrigudem", rainfall_mm=30, temp_max_c=30, rh_max_pct=60)
    plot_id = _make_plot(client, token, "Gowrigudem")

    resp = client.get(f"/plots/{plot_id}/farm-advisor", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    by_cat = {r["category"]: r for r in body["recommendations"]}
    assert by_cat["irrigation"]["status"] == "delay"
    assert by_cat["field_inspection"]["status"] == "avoid"
    assert body["weather_risk"]["level"] == "HIGH"
    assert len(body["action_plan"]) > 0
    assert "heavy_rain_threshold_exceeded" in " ".join(body["technical_details"]["rules_triggered"])


def test_advisor_high_disease_risk(client):
    token = _register_and_token(client, "advisordisease@example.com")
    _set_todays_weather("Kakarlapalli", rainfall_mm=10, temp_max_c=30, rh_max_pct=92)
    plot_id = _make_plot(client, token, "Kakarlapalli")

    resp = client.get(f"/plots/{plot_id}/farm-advisor", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["disease_risk"]["level"] == "MEDIUM"
    assert body["disease_risk"]["classification"] == "RULE_BASED_LOGIC"
    by_cat = {r["category"]: r for r in body["recommendations"]}
    assert by_cat["disease_monitoring"]["status"] == "recommended"


def test_advisor_distinguishes_ml_from_rule_based(client):
    token = _register_and_token(client, "advisorml@example.com")
    plot_id = _make_plot(client, token, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/farm-advisor", headers=_auth_headers(token))
    body = resp.json()
    tech = body["technical_details"]
    assert tech["ml_prediction_used"]["classification"] == "REAL_ML_PREDICTION"
    assert tech["ml_prediction_used"]["variable"] == "rainfall_mm"
    assert body["disease_risk"]["classification"] == "RULE_BASED_LOGIC"
    assert body["weather_risk"]["classification"] == "RULE_BASED_LOGIC"
    # No recommendation may claim to be an ML output.
    for rec in body["recommendations"]:
        assert "ml_based" not in rec or rec.get("ml_based") is not True


def test_advisor_with_missing_crop(client):
    token = _register_and_token(client, "advisornocrop@example.com")
    plot_id = _make_plot(client, token, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/farm-advisor", headers=_auth_headers(token))
    body = resp.json()
    assert body["crop"] is None
    assert body["crop_condition"]["available"] is False


def test_advisor_with_linked_crop(client):
    token = _register_and_token(client, "advisorcrop@example.com")
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": "Bethupalli"}, headers=_auth_headers(token)).json()
    plot = client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot"}, headers=_auth_headers(token)).json()
    client.post(
        "/crops",
        json={"farm_id": farm["id"], "plot_id": plot["id"], "crop_name": "Cotton", "stage": "Flowering"},
        headers=_auth_headers(token),
    )

    resp = client.get(f"/plots/{plot['id']}/farm-advisor", headers=_auth_headers(token))
    body = resp.json()
    assert body["crop"]["crop_name"] == "Cotton"
    assert body["crop"]["stage"] == "Flowering"
    assert body["crop_condition"]["available"] is False  # honest -- no health model


def test_advisor_missing_weather_data_handled_gracefully(client):
    token = _register_and_token(client, "advisormissing@example.com")
    _set_todays_weather("Rejerla", rainfall_mm=np.nan, temp_max_c=np.nan, rh_max_pct=np.nan)
    plot_id = _make_plot(client, token, "Rejerla")

    resp = client.get(f"/plots/{plot_id}/farm-advisor", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["disease_risk"]["available"] is False
    assert body["weather_risk"]["available"] is False
    assert all(r["status"] == "normal" for r in body["recommendations"])  # never fabricated as risky


def test_advisor_missing_plot_returns_404(client):
    token = _register_and_token(client, "advisornoplot@example.com")
    resp = client.get("/plots/nonexistent-id/farm-advisor", headers=_auth_headers(token))
    assert resp.status_code == 404


def test_advisor_requires_ownership(client):
    token_a = _register_and_token(client, "advisorowner.a@example.com")
    token_b = _register_and_token(client, "advisorowner.b@example.com")
    plot_id = _make_plot(client, token_a, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/farm-advisor", headers=_auth_headers(token_b))
    assert resp.status_code == 404
