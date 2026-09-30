from alert_engine import ALERT_TYPES, generate_candidate_alerts
from crop_health import build_disease_risk
from farm_advisor import build_recommendations


def _base_kwargs(**overrides):
    kwargs = dict(
        farm_id="farm1",
        plot_id="plot1",
        today_date="2026-09-27",
        forecast_rows=[{"date": "2026-09-27", "rainfall_mm": 2, "temp_max_c": 28, "rh_max_pct": 50, "wind_max_kmh": 10}],
        disease_risk=build_disease_risk(50, 2),
        recommendations=build_recommendations(2, 28, 50, None, None),
        previous_health_status=None,
        current_health_status=None,
    )
    kwargs.update(overrides)
    return kwargs


def test_no_alerts_on_normal_conditions():
    alerts = generate_candidate_alerts(**_base_kwargs())
    assert alerts == []


def test_heavy_rainfall_alert_today_is_critical():
    rows = [{"date": "2026-09-27", "rainfall_mm": 25, "temp_max_c": 28, "rh_max_pct": 50, "wind_max_kmh": 10}]
    alerts = generate_candidate_alerts(
        **_base_kwargs(
            forecast_rows=rows,
            recommendations=build_recommendations(25, 28, 50, None, None),
        )
    )
    rain_alert = next(a for a in alerts if a["alert_type"] == "heavy_rainfall")
    assert rain_alert["severity"] == "critical"
    assert rain_alert["source"] == "weather_forecast"
    assert rain_alert["valid_until"] == "2026-09-27"


def test_heavy_rainfall_alert_future_day_is_warning_early_warning():
    rows = [
        {"date": "2026-09-27", "rainfall_mm": 2, "temp_max_c": 28, "rh_max_pct": 50, "wind_max_kmh": 10},
        {"date": "2026-09-28", "rainfall_mm": 25, "temp_max_c": 28, "rh_max_pct": 50, "wind_max_kmh": 10},
    ]
    alerts = generate_candidate_alerts(**_base_kwargs(forecast_rows=rows))
    rain_alert = next(a for a in alerts if a["alert_type"] == "heavy_rainfall")
    assert rain_alert["severity"] == "warning"
    assert rain_alert["valid_until"] == "2026-09-28"
    assert "2026-09-28" in rain_alert["title"]


def test_heat_risk_alert():
    rows = [{"date": "2026-09-27", "rainfall_mm": 2, "temp_max_c": 40, "rh_max_pct": 50, "wind_max_kmh": 10}]
    alerts = generate_candidate_alerts(**_base_kwargs(forecast_rows=rows, recommendations=build_recommendations(2, 40, 50, None, None)))
    heat_alert = next(a for a in alerts if a["alert_type"] == "heat_risk")
    assert heat_alert["severity"] == "critical"
    assert heat_alert["source"] == "weather_forecast"


def test_excess_moisture_alert_requires_both_rain_and_humidity():
    rows = [{"date": "2026-09-27", "rainfall_mm": 10, "temp_max_c": 28, "rh_max_pct": 90, "wind_max_kmh": 10}]
    alerts = generate_candidate_alerts(**_base_kwargs(forecast_rows=rows, disease_risk=build_disease_risk(90, 10)))
    moisture_alert = next(a for a in alerts if a["alert_type"] == "excess_moisture")
    assert moisture_alert["source"] == "derived_assessment"


def test_disease_risk_alert_reuses_phase2_output():
    disease_risk = build_disease_risk(90, 10)
    alerts = generate_candidate_alerts(**_base_kwargs(disease_risk=disease_risk))
    disease_alert = next(a for a in alerts if a["alert_type"] == "disease_risk")
    assert disease_alert["reason"] == disease_risk["why"]
    assert disease_alert["source"] == "derived_assessment"
    assert disease_alert["severity"] == "warning"


def test_disease_risk_never_alerts_when_unavailable():
    disease_risk = build_disease_risk(None, None)
    alerts = generate_candidate_alerts(**_base_kwargs(disease_risk=disease_risk))
    assert not any(a["alert_type"] == "disease_risk" for a in alerts)


def test_irrigation_concern_reuses_phase1_recommendation():
    rows = [{"date": "2026-09-27", "rainfall_mm": 25, "temp_max_c": 28, "rh_max_pct": 50, "wind_max_kmh": 10}]
    recs = build_recommendations(25, 28, 50, None, None)
    alerts = generate_candidate_alerts(**_base_kwargs(forecast_rows=rows, recommendations=recs))
    irrigation_alert = next(a for a in alerts if a["alert_type"] == "irrigation_concern")
    irrigation_rec = next(r for r in recs if r["category"] == "irrigation")
    assert irrigation_alert["recommended_action"] == irrigation_rec["what"]
    assert irrigation_alert["source"] == "advisory_engine"
    assert irrigation_alert["severity"] == "warning"  # delay -> warning


def test_farm_operation_alert_on_avoid_status():
    rows = [{"date": "2026-09-27", "rainfall_mm": 25, "temp_max_c": 28, "rh_max_pct": 50, "wind_max_kmh": 10}]
    recs = build_recommendations(25, 28, 50, None, None)
    alerts = generate_candidate_alerts(**_base_kwargs(forecast_rows=rows, recommendations=recs))
    assert any(a["alert_type"] == "farm_operation" for a in alerts)


def test_crop_health_decline_requires_two_real_observations():
    alerts_no_prior = generate_candidate_alerts(**_base_kwargs(previous_health_status=None, current_health_status="FAIR"))
    assert not any(a["alert_type"] == "crop_health_decline" for a in alerts_no_prior)

    alerts_decline = generate_candidate_alerts(**_base_kwargs(previous_health_status="GOOD", current_health_status="FAIR"))
    decline_alert = next(a for a in alerts_decline if a["alert_type"] == "crop_health_decline")
    assert decline_alert["condition"] == "GOOD → FAIR"
    assert decline_alert["source"] == "derived_assessment"


def test_crop_health_no_alert_when_improving_or_stable():
    alerts_improve = generate_candidate_alerts(**_base_kwargs(previous_health_status="FAIR", current_health_status="GOOD"))
    assert not any(a["alert_type"] == "crop_health_decline" for a in alerts_improve)

    alerts_stable = generate_candidate_alerts(**_base_kwargs(previous_health_status="GOOD", current_health_status="GOOD"))
    assert not any(a["alert_type"] == "crop_health_decline" for a in alerts_stable)


def test_strong_wind_and_crop_stress_never_generated():
    rows = [{"date": "2026-09-27", "rainfall_mm": 25, "temp_max_c": 40, "rh_max_pct": 95, "wind_max_kmh": 100}]
    alerts = generate_candidate_alerts(
        **_base_kwargs(
            forecast_rows=rows,
            disease_risk=build_disease_risk(95, 25),
            recommendations=build_recommendations(25, 40, 95, None, None),
            previous_health_status="GOOD",
            current_health_status="POOR",
        )
    )
    assert not any(a["alert_type"] == "strong_wind" for a in alerts)
    assert not any(a["alert_type"] == "crop_stress" for a in alerts)
    assert "strong_wind" in ALERT_TYPES  # defined for the filter list, just never emitted
    assert "crop_stress" in ALERT_TYPES


def test_dedupe_key_is_stable_and_date_scoped():
    rows = [{"date": "2026-09-27", "rainfall_mm": 25, "temp_max_c": 28, "rh_max_pct": 50, "wind_max_kmh": 10}]
    alerts = generate_candidate_alerts(**_base_kwargs(forecast_rows=rows, recommendations=build_recommendations(25, 28, 50, None, None)))
    rain_alert = next(a for a in alerts if a["alert_type"] == "heavy_rainfall")
    assert rain_alert["dedupe_key"] == "farm1:plot1:heavy_rainfall:weather_forecast:2026-09-27"
