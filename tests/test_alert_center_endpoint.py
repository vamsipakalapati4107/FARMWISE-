import datetime as dt
import os
import sqlite3

import numpy as np
import pytest
from fastapi.testclient import TestClient

import api as api_module
from api import app


def _test_db_path() -> str:
    """The real test DB is a tempfile (see tests/conftest.py's APP_DB_PATH)
    -- never touch data/app.db directly from a test."""
    return os.environ["APP_DB_PATH"]


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
    assert mask.any()
    df.loc[mask, "rainfall_mm"] = rainfall_mm
    df.loc[mask, "temp_max_c"] = temp_max_c
    df.loc[mask, "rh_max_pct"] = rh_max_pct


def test_heavy_rainfall_alert_generated(client):
    token = _register_and_token(client, "alert1@example.com")
    _set_todays_weather("Buggapadu", rainfall_mm=30, temp_max_c=28, rh_max_pct=50)
    _, plot_id = _make_plot(client, token, "Buggapadu")

    resp = client.get("/alert-center", headers=_auth_headers(token))
    assert resp.status_code == 200
    alerts = resp.json()
    rain_alert = next(a for a in alerts if a["alert_type"] == "heavy_rainfall")
    assert rain_alert["severity"] == "critical"
    assert rain_alert["source"] == "weather_forecast"
    assert rain_alert["status"] == "new"


def test_disease_risk_alert_generated(client):
    token = _register_and_token(client, "alert2@example.com")
    _set_todays_weather("Gowrigudem", rainfall_mm=10, temp_max_c=28, rh_max_pct=92)
    _, plot_id = _make_plot(client, token, "Gowrigudem")

    resp = client.get("/alert-center", headers=_auth_headers(token))
    alerts = resp.json()
    disease_alert = next(a for a in alerts if a["alert_type"] == "disease_risk")
    assert disease_alert["source"] == "derived_assessment"
    assert disease_alert["severity"] == "warning"


def test_crop_health_decline_alert_after_two_real_observations(client):
    token = _register_and_token(client, "alert3@example.com")
    _set_todays_weather("Kakarlapalli", rainfall_mm=2, temp_max_c=28, rh_max_pct=50)
    _, plot_id = _make_plot(client, token, "Kakarlapalli")

    # First sync: logs a GOOD health snapshot for today, no prior to compare.
    resp1 = client.get("/alert-center", headers=_auth_headers(token))
    assert not any(a["alert_type"] == "crop_health_decline" for a in resp1.json())

    # Manually move today's snapshot to "yesterday" so a second sync (still
    # "today") creates a genuinely new second real observation to compare.
    conn = sqlite3.connect(_test_db_path())
    cur = conn.cursor()
    cur.execute("UPDATE health_snapshots SET date = '2000-01-01' WHERE plot_id = ?", (plot_id,))
    conn.commit()
    conn.close()

    _set_todays_weather("Kakarlapalli", rainfall_mm=10, temp_max_c=30, rh_max_pct=92)  # now FAIR (medium disease risk)
    resp2 = client.get("/alert-center", headers=_auth_headers(token))
    decline_alerts = [a for a in resp2.json() if a["alert_type"] == "crop_health_decline"]
    assert len(decline_alerts) == 1
    assert decline_alerts[0]["source"] == "derived_assessment"


def test_missing_weather_data_no_crash_no_fake_alerts(client):
    token = _register_and_token(client, "alert4@example.com")
    _set_todays_weather("Rejerla", rainfall_mm=np.nan, temp_max_c=np.nan, rh_max_pct=np.nan)
    _, plot_id = _make_plot(client, token, "Rejerla")

    resp = client.get("/alert-center", headers=_auth_headers(token))
    assert resp.status_code == 200
    # No disease/rainfall/heat alerts fabricated from missing data.
    assert not any(a["alert_type"] in ("disease_risk", "heavy_rainfall", "heat_risk") for a in resp.json())


def test_alert_deduplication_on_repeated_sync(client):
    token = _register_and_token(client, "alert5@example.com")
    _set_todays_weather("Sadasivunipalem", rainfall_mm=30, temp_max_c=28, rh_max_pct=50)
    _make_plot(client, token, "Sadasivunipalem")

    first = client.get("/alert-center", headers=_auth_headers(token)).json()
    second = client.get("/alert-center", headers=_auth_headers(token)).json()
    third = client.get("/alert-center", headers=_auth_headers(token)).json()
    assert len(first) == len(second) == len(third)
    assert len(first) > 0


def test_alert_lifecycle_read_and_resolve(client):
    token = _register_and_token(client, "alert6@example.com")
    _set_todays_weather("Siddaram", rainfall_mm=30, temp_max_c=28, rh_max_pct=50)
    _make_plot(client, token, "Siddaram")

    alerts = client.get("/alert-center", headers=_auth_headers(token)).json()
    alert_id = alerts[0]["id"]
    assert alerts[0]["status"] == "new"

    resp = client.patch(f"/alerts/{alert_id}/read", headers=_auth_headers(token))
    assert resp.json()["status"] == "read"

    resp = client.patch(f"/alerts/{alert_id}/resolve", headers=_auth_headers(token))
    assert resp.json()["status"] == "resolved"

    # Resolved alerts stay resolved across another sync (not reset to new).
    alerts_after = client.get("/alert-center", headers=_auth_headers(token)).json()
    assert next(a for a in alerts_after if a["id"] == alert_id)["status"] == "resolved"


def test_severity_classification_today_critical_future_warning(client):
    token = _register_and_token(client, "alert7@example.com")
    _set_todays_weather("Thallamada", rainfall_mm=30, temp_max_c=28, rh_max_pct=50)
    _make_plot(client, token, "Thallamada")

    alerts = client.get("/alert-center", headers=_auth_headers(token)).json()
    today_rain = next(a for a in alerts if a["alert_type"] == "heavy_rainfall" and a["valid_until"] == _today())
    assert today_rain["severity"] == "critical"


def test_plot_specific_alerts_endpoint(client):
    token = _register_and_token(client, "alert8@example.com")
    _set_todays_weather("Kothuru", rainfall_mm=30, temp_max_c=28, rh_max_pct=50)
    farm_id, plot_id = _make_plot(client, token, "Kothuru")

    resp = client.get(f"/plots/{plot_id}/alerts", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert all(a["plot_id"] == plot_id for a in resp.json())
    assert len(resp.json()) > 0


def test_farm_specific_alerts_endpoint(client):
    token = _register_and_token(client, "alert9@example.com")
    _set_todays_weather("Regallapadu", rainfall_mm=30, temp_max_c=28, rh_max_pct=50)
    farm_id, plot_id = _make_plot(client, token, "Regallapadu")

    resp = client.get(f"/farms/{farm_id}/alerts", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert all(a["farm_id"] == farm_id for a in resp.json())


def test_mark_alert_read_requires_ownership(client):
    token_a = _register_and_token(client, "alert10.a@example.com")
    token_b = _register_and_token(client, "alert10.b@example.com")
    _set_todays_weather("Ramanagaram", rainfall_mm=30, temp_max_c=28, rh_max_pct=50)
    _make_plot(client, token_a, "Ramanagaram")

    alerts = client.get("/alert-center", headers=_auth_headers(token_a)).json()
    alert_id = alerts[0]["id"]
    resp = client.patch(f"/alerts/{alert_id}/read", headers=_auth_headers(token_b))
    assert resp.status_code == 404


def test_resolve_alert_requires_ownership(client):
    token_a = _register_and_token(client, "alert11.a@example.com")
    token_b = _register_and_token(client, "alert11.b@example.com")
    _set_todays_weather("Yatalakunta", rainfall_mm=30, temp_max_c=28, rh_max_pct=50)
    _make_plot(client, token_a, "Yatalakunta")

    alerts = client.get("/alert-center", headers=_auth_headers(token_a)).json()
    alert_id = alerts[0]["id"]
    resp = client.patch(f"/alerts/{alert_id}/resolve", headers=_auth_headers(token_b))
    assert resp.status_code == 404


def test_expired_alert_auto_expires_when_valid_until_passes(client):
    token = _register_and_token(client, "alert12@example.com")
    _set_todays_weather("Narayanapuram", rainfall_mm=30, temp_max_c=28, rh_max_pct=50)
    _make_plot(client, token, "Narayanapuram")
    alerts = client.get("/alert-center", headers=_auth_headers(token)).json()
    alert_id = next(a["id"] for a in alerts if a["alert_type"] == "heavy_rainfall")

    conn = sqlite3.connect(_test_db_path())
    cur = conn.cursor()
    cur.execute("UPDATE alerts SET valid_until = '2000-01-01' WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()

    alerts_after = client.get("/alert-center", headers=_auth_headers(token)).json()
    assert next(a for a in alerts_after if a["id"] == alert_id)["status"] == "expired"


def test_dashboard_alert_count_via_alert_center(client):
    token = _register_and_token(client, "alert13@example.com")
    _set_todays_weather("Ramagovindapuram", rainfall_mm=30, temp_max_c=28, rh_max_pct=50)
    _make_plot(client, token, "Ramagovindapuram")

    alerts = client.get("/alert-center", headers=_auth_headers(token)).json()
    critical_count = sum(1 for a in alerts if a["severity"] == "critical")
    assert critical_count >= 1


def test_map_alert_integration_via_plots_intelligence(client):
    token = _register_and_token(client, "alert14@example.com")
    _set_todays_weather("Cherukupalli", rainfall_mm=30, temp_max_c=28, rh_max_pct=50)
    _make_plot(client, token, "Cherukupalli")

    resp = client.get("/plots/intelligence", headers=_auth_headers(token))
    assert resp.status_code == 200
    entry = resp.json()[0]
    assert "active_alerts" in entry
    assert entry["active_alerts"]["counts"]["critical"] >= 1
    assert entry["active_alerts"]["top_severity"] == "critical"


def test_no_alerts_when_conditions_normal(client):
    token = _register_and_token(client, "alert15@example.com")
    # Override every forecast day (not just today) to normal -- the alert
    # engine's early-warning lookahead scans all 5 real forecast days, so
    # leaving any of them at their real (possibly risky) values could
    # legitimately produce a future-day alert.
    df = api_module.state["forecast"]
    mask = df["gram_panchayat"] == "Kistaram"
    df.loc[mask, "rainfall_mm"] = 2
    df.loc[mask, "temp_max_c"] = 28
    df.loc[mask, "rh_max_pct"] = 50
    _make_plot(client, token, "Kistaram")

    resp = client.get("/alert-center", headers=_auth_headers(token))
    assert resp.json() == []


def test_phase1_advisor_still_works(client):
    token = _register_and_token(client, "alert16@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")
    resp = client.get(f"/plots/{plot_id}/farm-advisor", headers=_auth_headers(token))
    assert resp.status_code == 200


def test_phase2_crop_health_still_works(client):
    token = _register_and_token(client, "alert17@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")
    resp = client.get(f"/plots/{plot_id}/crop-health", headers=_auth_headers(token))
    assert resp.status_code == 200


def test_phase3_map_still_works(client):
    token = _register_and_token(client, "alert18@example.com")
    _make_plot(client, token, "Bethupalli")
    resp = client.get("/plots/intelligence", headers=_auth_headers(token))
    assert resp.status_code == 200


def test_phase4_analytics_still_works(client):
    token = _register_and_token(client, "alert19@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")
    resp = client.get(f"/plots/{plot_id}/analytics", headers=_auth_headers(token))
    assert resp.status_code == 200


def test_phase11_gp_level_alerts_unaffected(client):
    """The pre-existing public /alerts (GP-scoped, Phase 11) must still
    work unchanged -- it is a completely different endpoint from
    /alert-center (see routers/alert_center.py docstring)."""
    resp = client.get("/alerts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
