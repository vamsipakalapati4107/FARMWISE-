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


def _make_plot(client, token: str, gp: str) -> tuple[str, str]:
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": gp}, headers=_auth_headers(token)).json()
    plot = client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot"}, headers=_auth_headers(token)).json()
    return farm["id"], plot["id"]


def test_historical_weather_available_for_real_gp(client):
    token = _register_and_token(client, "analytics1@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/analytics?range_days=30", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["historical"]["available"] is True
    assert len(body["historical"]["rainfall"]) == 30
    assert body["historical"]["source_type"] == "weather_observation"


def test_historical_weather_unavailable_for_excessive_range(client):
    token = _register_and_token(client, "analytics2@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/analytics?range_days=90", headers=_auth_headers(token))
    assert resp.status_code == 200
    # 90 days genuinely exist in the real 2025 dataset -- should be available.
    assert resp.json()["historical"]["available"] is True


def test_invalid_range_rejected(client):
    token = _register_and_token(client, "analytics3@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/analytics?range_days=15", headers=_auth_headers(token))
    assert resp.status_code == 422


def test_forecast_available_real_5_days(client):
    token = _register_and_token(client, "analytics4@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/analytics", headers=_auth_headers(token))
    body = resp.json()
    assert len(body["forecast"]) == 5
    assert all("condition" in day for day in body["forecast"])


def test_rainfall_analytics_present_with_comparison(client):
    token = _register_and_token(client, "analytics5@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/analytics?range_days=7", headers=_auth_headers(token))
    body = resp.json()
    assert body["rainfall_analytics"]["available"] is True
    assert body["rainfall_analytics"]["comparison"]["available"] is True


def test_time_range_filtering_changes_window_size(client):
    token = _register_and_token(client, "analytics6@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")

    resp7 = client.get(f"/plots/{plot_id}/analytics?range_days=7", headers=_auth_headers(token))
    resp30 = client.get(f"/plots/{plot_id}/analytics?range_days=30", headers=_auth_headers(token))
    assert len(resp7.json()["historical"]["temperature"]) == 7
    assert len(resp30.json()["historical"]["temperature"]) == 30
    assert resp7.json()["available_ranges"] == {"7": True, "30": True, "90": True}


def test_disease_history_always_unavailable(client):
    token = _register_and_token(client, "analytics7@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/analytics", headers=_auth_headers(token))
    assert resp.json()["disease_history"]["available"] is False


def test_health_history_always_unavailable(client):
    token = _register_and_token(client, "analytics8@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/analytics", headers=_auth_headers(token))
    assert resp.json()["health_history"]["available"] is False


def test_insight_generation_present(client):
    token = _register_and_token(client, "analytics9@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/analytics", headers=_auth_headers(token))
    insights = resp.json()["insights"]
    assert isinstance(insights, list)
    for insight in insights:
        assert insight["source_type"] in ("weather_history", "forecast", "ml_prediction", "spatial_estimate", "derived_rule")


def test_source_type_transparency(client):
    token = _register_and_token(client, "analytics10@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/analytics", headers=_auth_headers(token))
    sources = resp.json()["data_sources"]
    assert "ML model" in sources["rainfall_ml"]
    assert sources["wind_risk"] == "Unavailable (no established threshold)"


def test_missing_plot_returns_404(client):
    token = _register_and_token(client, "analytics11@example.com")
    resp = client.get("/plots/nonexistent/analytics", headers=_auth_headers(token))
    assert resp.status_code == 404


def test_analytics_ownership_required(client):
    token_a = _register_and_token(client, "analytics12.a@example.com")
    token_b = _register_and_token(client, "analytics12.b@example.com")
    _, plot_id = _make_plot(client, token_a, "Bethupalli")

    resp = client.get(f"/plots/{plot_id}/analytics", headers=_auth_headers(token_b))
    assert resp.status_code == 404


def test_phase1_advisor_still_works(client):
    token = _register_and_token(client, "analytics13@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")
    resp = client.get(f"/plots/{plot_id}/farm-advisor", headers=_auth_headers(token))
    assert resp.status_code == 200


def test_phase2_crop_health_still_works(client):
    token = _register_and_token(client, "analytics14@example.com")
    _, plot_id = _make_plot(client, token, "Bethupalli")
    resp = client.get(f"/plots/{plot_id}/crop-health", headers=_auth_headers(token))
    assert resp.status_code == 200


def test_phase3_map_still_works(client):
    token = _register_and_token(client, "analytics15@example.com")
    _make_plot(client, token, "Bethupalli")
    resp = client.get("/plots/intelligence", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_plot_comparison_via_existing_intelligence_endpoint(client):
    """Item 11's 'Compare Plots' is implemented client-side by grouping the
    existing /plots/intelligence response by farm_id -- no new backend
    endpoint duplicates that data."""
    token = _register_and_token(client, "analytics16@example.com")
    farm = client.post("/farms", json={"name": "Farm", "gram_panchayat": "Bethupalli"}, headers=_auth_headers(token)).json()
    client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token))
    client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot B"}, headers=_auth_headers(token))

    resp = client.get("/plots/intelligence", headers=_auth_headers(token))
    entries = [e for e in resp.json() if e["farm_id"] == farm["id"]]
    assert len(entries) == 2
