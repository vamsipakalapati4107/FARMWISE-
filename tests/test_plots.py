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


def _make_farm(client, token: str, gp: str = "Bethupalli") -> dict:
    return client.post(
        "/farms", json={"name": "Farm", "gram_panchayat": gp}, headers=_auth_headers(token)
    ).json()


def test_create_plot_without_coordinates(client):
    token = _register_and_token(client, "plot1@example.com")
    farm = _make_farm(client, token)

    resp = client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token))
    assert resp.status_code == 201
    plot = resp.json()
    assert plot["latitude"] is None
    assert plot["longitude"] is None


def test_create_plot_with_coordinates(client):
    token = _register_and_token(client, "plot2@example.com")
    farm = _make_farm(client, token)

    resp = client.post(
        f"/farms/{farm['id']}/plots",
        json={"name": "Plot A", "latitude": 17.1974145, "longitude": 80.8873668},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201
    assert resp.json()["latitude"] == 17.1974145


def test_list_plots_for_farm(client):
    token = _register_and_token(client, "plot3@example.com")
    farm = _make_farm(client, token)
    client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token))
    client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot B"}, headers=_auth_headers(token))

    resp = client.get(f"/farms/{farm['id']}/plots", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_plot_ownership_isolation(client):
    token_a = _register_and_token(client, "plotown.a@example.com")
    token_b = _register_and_token(client, "plotown.b@example.com")
    farm = _make_farm(client, token_a)
    plot = client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token_a)).json()

    resp = client.get(f"/plots/{plot['id']}", headers=_auth_headers(token_b))
    assert resp.status_code == 404
    resp = client.get(f"/farms/{farm['id']}/plots", headers=_auth_headers(token_b))
    assert resp.status_code == 404


def test_update_and_delete_plot(client):
    token = _register_and_token(client, "plotcrud@example.com")
    farm = _make_farm(client, token)
    plot = client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token)).json()

    resp = client.patch(f"/plots/{plot['id']}", json={"latitude": 17.2, "longitude": 80.85}, headers=_auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["latitude"] == 17.2

    resp = client.delete(f"/plots/{plot['id']}", headers=_auth_headers(token))
    assert resp.status_code == 204
    resp = client.get(f"/plots/{plot['id']}", headers=_auth_headers(token))
    assert resp.status_code == 404


def test_plot_weather_gp_level_without_coordinates(client):
    token = _register_and_token(client, "plotweather1@example.com")
    farm = _make_farm(client, token)
    plot = client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token)).json()

    resp = client.get(f"/plots/{plot['id']}/weather", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["rainfall_mm"]["source"] == "gp_level"
    assert body["temp_max_c"]["source"] == "pass_through"


def test_plot_weather_estimated_with_coordinates(client):
    token = _register_and_token(client, "plotweather2@example.com")
    farm = _make_farm(client, token)
    plot = client.post(
        f"/farms/{farm['id']}/plots",
        json={"name": "Plot A", "latitude": 17.20, "longitude": 80.86},
        headers=_auth_headers(token),
    ).json()

    resp = client.get(f"/plots/{plot['id']}/weather", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["rainfall_mm"]["source"] == "estimated_downscaled"
    assert body["rainfall_mm"]["provenance"] is not None
    assert len(body["rainfall_mm"]["provenance"]) > 0


def test_plot_ml_predictions_classification(client):
    token = _register_and_token(client, "plotml@example.com")
    farm = _make_farm(client, token)
    plot = client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token)).json()

    resp = client.get(f"/plots/{plot['id']}/ml-predictions", headers=_auth_headers(token))
    assert resp.status_code == 200
    predictions = {p["variable"]: p for p in resp.json()["predictions"]}
    assert predictions["rainfall_mm"]["classification"] == "REAL_ML_PREDICTION"
    assert predictions["temp_max_c"]["classification"] == "PASS_THROUGH_VALUE"
    assert predictions["temp_min_c"]["classification"] == "PASS_THROUGH_VALUE"
    assert predictions["rh_max_pct"]["classification"] == "PASS_THROUGH_VALUE"
    assert predictions["wind_max_kmh"]["classification"] == "PASS_THROUGH_VALUE"


def test_plot_risk_endpoint(client):
    token = _register_and_token(client, "plotrisk@example.com")
    farm = _make_farm(client, token)
    plot = client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token)).json()

    resp = client.get(f"/plots/{plot['id']}/risk", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["rainfall_source"] == "gp_level"


def test_plot_health_is_honest_stub(client):
    token = _register_and_token(client, "plothealth@example.com")
    farm = _make_farm(client, token)
    plot = client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token)).json()

    resp = client.get(f"/plots/{plot['id']}/health", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["classification"] == "NOT_AVAILABLE"


def test_plot_advisory_without_linked_crop(client):
    token = _register_and_token(client, "plotadvisory1@example.com")
    farm = _make_farm(client, token)
    plot = client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token)).json()

    resp = client.get(f"/plots/{plot['id']}/advisory", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["crop_name"] is None


def test_plot_advisory_with_linked_crop(client):
    token = _register_and_token(client, "plotadvisory2@example.com")
    farm = _make_farm(client, token)
    plot = client.post(f"/farms/{farm['id']}/plots", json={"name": "Plot A"}, headers=_auth_headers(token)).json()
    client.post(
        "/crops",
        json={"farm_id": farm["id"], "plot_id": plot["id"], "crop_name": "Cotton", "stage": "Flowering"},
        headers=_auth_headers(token),
    )

    resp = client.get(f"/plots/{plot['id']}/advisory", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["crop_name"] == "Cotton"


def test_ml_audit_endpoint_lists_components(client):
    resp = client.get("/ml/models")
    assert resp.status_code == 200
    components = {c["component"] for c in resp.json()}
    assert "rainfall_downscaling_model" in components
    assert "temp_rh_wind_forecast" in components

    for c in resp.json():
        assert c["classification"] in (
            "REAL_ML_PREDICTION",
            "RULE_BASED_LOGIC",
            "RAW_DATA_API_VALUE",
            "PASS_THROUGH_VALUE",
        )


def test_ml_audit_single_component(client):
    resp = client.get("/ml/models/rainfall_downscaling_model")
    assert resp.status_code == 200
    assert resp.json()["classification"] == "REAL_ML_PREDICTION"

    resp = client.get("/ml/models/nonexistent")
    assert resp.status_code == 404
