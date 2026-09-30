import pytest
from fastapi.testclient import TestClient

from api import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_current_weather_for_known_gp(client):
    resp = client.get("/weather/current/Bethupalli")
    assert resp.status_code == 200
    body = resp.json()
    assert body["gram_panchayat"] == "Bethupalli"
    assert "temp_max_c" in body
    assert "date" in body


def test_current_weather_unknown_gp_404(client):
    resp = client.get("/weather/current/Nowhereville")
    assert resp.status_code == 404


def test_hourly_estimated_shape(client):
    resp = client.get("/weather/hourly-estimated/Bethupalli")
    assert resp.status_code == 200
    body = resp.json()
    assert body["gram_panchayat"] == "Bethupalli"
    assert len(body["points"]) == 24
    assert all(p["estimated"] is True for p in body["points"])
    assert {p["hour"] for p in body["points"]} == set(range(24))


def test_hourly_estimated_peak_near_afternoon(client):
    resp = client.get("/weather/hourly-estimated/Bethupalli")
    points = resp.json()["points"]
    temps = {p["hour"]: p["temp_c"] for p in points}
    # Peak (hour 15) should be warmer than trough (hour 3).
    assert temps[15] > temps[3]


def test_hourly_estimated_accepts_explicit_date(client):
    forecast_resp = client.get("/forecast/Bethupalli")
    dates = [row["date"] for row in forecast_resp.json()]
    assert len(dates) >= 2

    resp = client.get(f"/weather/hourly-estimated/Bethupalli?date={dates[-1]}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["date"] == dates[-1]
    assert len(body["points"]) == 24


def test_hourly_estimated_unknown_date_404(client):
    resp = client.get("/weather/hourly-estimated/Bethupalli?date=1999-01-01")
    assert resp.status_code == 404


def test_alerts_for_gp_have_expected_shape(client):
    resp = client.get("/alerts/Bethupalli")
    assert resp.status_code == 200
    alerts = resp.json()
    for alert in alerts:
        assert alert["severity"] in ("critical", "warning")
        assert alert["gram_panchayat"] == "Bethupalli"
        assert set(["icon", "title", "description", "action", "date"]).issubset(alert.keys())


def test_alerts_unknown_gp_404(client):
    resp = client.get("/alerts/Nowhereville")
    assert resp.status_code == 404


def test_all_alerts_endpoint(client):
    resp = client.get("/alerts")
    assert resp.status_code == 200
    alerts = resp.json()
    assert isinstance(alerts, list)
    # "Normal operations" rows must never appear as an alert.
    assert all(a["severity"] != "safe" for a in alerts)
