import datetime as dt
import json

import pytest
from fastapi.testclient import TestClient

import api as api_module
from api import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _register_and_token(client, email: str, mobile: str | None = None) -> str:
    payload = {"name": "Test Farmer", "email": email, "password": "farmer123"}
    if mobile:
        payload["mobile"] = mobile
    client.post("/auth/register", json=payload)
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
    df = api_module.state["forecast"]
    mask = (df["gram_panchayat"] == gram_panchayat) & (df["date"] == _today())
    assert mask.any()
    df.loc[mask, "rainfall_mm"] = rainfall_mm
    df.loc[mask, "temp_max_c"] = temp_max_c
    df.loc[mask, "rh_max_pct"] = rh_max_pct


def test_sms_sent_for_critical_alert_when_eligible(client):
    token = _register_and_token(client, "sms1@example.com", mobile="9000000001")
    _set_todays_weather("Kakarlapalli", rainfall_mm=30, temp_max_c=28, rh_max_pct=50)
    _make_plot(client, token, "Kakarlapalli")

    alerts = client.get("/alert-center", headers=_auth_headers(token)).json()
    rain_alert = next(a for a in alerts if a["alert_type"] == "heavy_rainfall" and a["severity"] == "critical")
    assert rain_alert["sms"]["status"] == "SENT"
    assert rain_alert["sms"]["simulated"] is True


def test_sms_disabled_without_mobile_number(client):
    token = _register_and_token(client, "sms2@example.com", mobile=None)
    _set_todays_weather("Thumburu", rainfall_mm=30, temp_max_c=28, rh_max_pct=50)
    _make_plot(client, token, "Thumburu")

    alerts = client.get("/alert-center", headers=_auth_headers(token)).json()
    rain_alert = next(a for a in alerts if a["alert_type"] == "heavy_rainfall")
    assert rain_alert["sms"]["status"] == "DISABLED"


def test_sms_disabled_when_user_opts_out(client):
    token = _register_and_token(client, "sms3@example.com", mobile="9000000003")
    client.patch("/auth/me", json={"sms_notifications_enabled": False}, headers=_auth_headers(token))
    _set_todays_weather("Rejerla", rainfall_mm=30, temp_max_c=28, rh_max_pct=50)
    _make_plot(client, token, "Rejerla")

    alerts = client.get("/alert-center", headers=_auth_headers(token)).json()
    rain_alert = next(a for a in alerts if a["alert_type"] == "heavy_rainfall")
    assert rain_alert["sms"]["status"] == "DISABLED"


def test_sms_disabled_when_category_opted_out(client):
    token = _register_and_token(client, "sms4@example.com", mobile="9000000004")
    client.patch("/auth/me", json={"sms_alert_categories": ["disease_risk", "crop_stress", "farm_actions"]}, headers=_auth_headers(token))
    _set_todays_weather("Siddaram", rainfall_mm=30, temp_max_c=28, rh_max_pct=50)
    _make_plot(client, token, "Siddaram")

    alerts = client.get("/alert-center", headers=_auth_headers(token)).json()
    rain_alert = next(a for a in alerts if a["alert_type"] == "heavy_rainfall")
    assert rain_alert["sms"]["status"] == "DISABLED"


def test_sms_not_applicable_for_low_severity_alert(client):
    token = _register_and_token(client, "sms5@example.com", mobile="9000000005")
    # High temp alone (no heavy rain) triggers irrigation "recommended" ->
    # alert_engine.py maps that to severity "attention", not SMS-eligible.
    _set_todays_weather("Gangaram", rainfall_mm=0, temp_max_c=40, rh_max_pct=50)
    _make_plot(client, token, "Gangaram")

    alerts = client.get("/alert-center", headers=_auth_headers(token)).json()
    irrigation_alert = next((a for a in alerts if a["alert_type"] == "irrigation_concern"), None)
    assert irrigation_alert is not None
    assert irrigation_alert["severity"] == "attention"
    assert irrigation_alert["sms"]["status"] == "NOT_APPLICABLE"


def test_sms_cooldown_limits_bursts_to_one_message(client):
    token = _register_and_token(client, "sms6@example.com", mobile="9000000006")
    # Heavy rain + heat stress together on the same day -> two independently
    # SMS-eligible (critical) alerts created in the same sync.
    _set_todays_weather("Ramagovindapuram", rainfall_mm=30, temp_max_c=40, rh_max_pct=50)
    _make_plot(client, token, "Ramagovindapuram")

    alerts = client.get("/alert-center", headers=_auth_headers(token)).json()
    critical_today = [a for a in alerts if a["severity"] == "critical"]
    assert len(critical_today) >= 2
    sent_count = sum(1 for a in critical_today if a["sms"]["status"] == "SENT")
    assert sent_count == 1, "the per-user cooldown should limit a same-sync burst to a single SMS"


def test_no_new_sms_on_resync_of_same_alert(client):
    token = _register_and_token(client, "sms7@example.com", mobile="9000000007")
    _set_todays_weather("Pakalagudem", rainfall_mm=30, temp_max_c=28, rh_max_pct=50)
    _make_plot(client, token, "Pakalagudem")

    first = client.get("/alert-center", headers=_auth_headers(token)).json()
    second = client.get("/alert-center", headers=_auth_headers(token)).json()
    assert len(first) == len(second)
    rain_alert_1 = next(a for a in first if a["alert_type"] == "heavy_rainfall")
    rain_alert_2 = next(a for a in second if a["alert_type"] == "heavy_rainfall")
    assert rain_alert_1["id"] == rain_alert_2["id"]
    assert rain_alert_2["sms"]["status"] == "SENT"


def test_sms_alert_categories_round_trip_through_profile(client):
    token = _register_and_token(client, "sms8@example.com", mobile="9000000008")
    resp = client.patch(
        "/auth/me",
        json={"sms_alert_categories": ["severe_weather", "disease_risk"]},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["sms_alert_categories"] == ["severe_weather", "disease_risk"]

    me = client.get("/auth/me", headers=_auth_headers(token)).json()
    assert me["sms_alert_categories"] == ["severe_weather", "disease_risk"]
    assert me["sms_notifications_enabled"] is True
