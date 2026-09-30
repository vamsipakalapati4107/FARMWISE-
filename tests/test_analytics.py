import pandas as pd

from analytics import (
    available_ranges,
    compute_forecast_risk_for_row,
    compute_rainfall_analytics,
    condition_label,
    generate_insights,
    load_historical_weather,
    worst_case_risk,
)


def test_load_historical_weather_available_for_real_gp():
    result = load_historical_weather("Bethupalli", 7)
    assert result["available"] is True
    assert result["range_days"] == 7
    assert len(result["rainfall"]) == 7
    assert result["source_type"] == "weather_observation"


def test_load_historical_weather_unavailable_for_unknown_gp():
    result = load_historical_weather("NotARealPlace", 7)
    assert result["available"] is False
    assert "reason" in result


def test_load_historical_weather_unavailable_when_range_exceeds_data():
    result = load_historical_weather("Bethupalli", 9999)
    assert result["available"] is False
    assert "9999" in result["reason"]


def test_available_ranges_reflects_real_data_length():
    ranges = available_ranges(365)
    assert ranges == {7: True, 30: True, 90: True}
    ranges_short = available_ranges(10)
    assert ranges_short == {7: True, 30: False, 90: False}


def test_rainfall_analytics_computes_real_metrics():
    historical = load_historical_weather("Bethupalli", 30)
    result = compute_rainfall_analytics(historical, None)
    assert result["available"] is True
    assert result["total_mm"] >= 0
    assert result["rainy_days"] <= 30
    assert "date" in result["highest_day"]


def test_rainfall_analytics_unavailable_when_historical_unavailable():
    historical = {"available": False, "reason": "none"}
    result = compute_rainfall_analytics(historical, None)
    assert result["available"] is False


def test_rainfall_analytics_comparison_uses_real_reference():
    historical = load_historical_weather("Bethupalli", 7)
    full_year = load_historical_weather("Bethupalli", 365)
    full_df = pd.DataFrame({"time": [r["date"] for r in full_year["rainfall"]], "precipitation_sum": [r["mm"] for r in full_year["rainfall"]]})
    result = compute_rainfall_analytics(historical, full_df)
    assert result["comparison"]["available"] is True
    assert result["comparison"]["reference_average_mm_per_day"] >= 0


def test_forecast_risk_heavy_rain_high():
    risk = compute_forecast_risk_for_row({"rainfall_mm": 25, "temp_max_c": 30, "rh_max_pct": 60, "wind_max_kmh": 10})
    assert risk["heavy_rain_risk"]["level"] == "HIGH"


def test_forecast_risk_heavy_rain_medium():
    risk = compute_forecast_risk_for_row({"rainfall_mm": 10, "temp_max_c": 30, "rh_max_pct": 60, "wind_max_kmh": 10})
    assert risk["heavy_rain_risk"]["level"] == "MEDIUM"


def test_forecast_risk_heavy_rain_low():
    risk = compute_forecast_risk_for_row({"rainfall_mm": 1, "temp_max_c": 30, "rh_max_pct": 60, "wind_max_kmh": 10})
    assert risk["heavy_rain_risk"]["level"] == "LOW"


def test_forecast_risk_labels_derived_not_ml():
    risk = compute_forecast_risk_for_row({"rainfall_mm": 25, "temp_max_c": 40, "rh_max_pct": 90, "wind_max_kmh": 30})
    for key in ["heavy_rain_risk", "heat_risk", "humidity_risk"]:
        assert risk[key]["source_type"] == "derived_assessment"
        assert risk[key]["label"] == "Derived from forecast conditions"


def test_forecast_risk_wind_always_unknown_no_threshold_exists():
    risk = compute_forecast_risk_for_row({"rainfall_mm": 0, "temp_max_c": 30, "rh_max_pct": 50, "wind_max_kmh": 50})
    assert risk["wind_risk"]["level"] == "UNKNOWN"
    assert risk["wind_risk"]["source_type"] == "unavailable"


def test_forecast_risk_missing_data_returns_unknown():
    risk = compute_forecast_risk_for_row({"rainfall_mm": None, "temp_max_c": None, "rh_max_pct": None, "wind_max_kmh": None})
    assert risk["heavy_rain_risk"]["level"] == "UNKNOWN"
    assert risk["heat_risk"]["level"] == "UNKNOWN"
    assert risk["humidity_risk"]["level"] == "UNKNOWN"


def test_worst_case_risk_picks_highest_across_days():
    daily = [
        compute_forecast_risk_for_row({"rainfall_mm": 1, "temp_max_c": 30, "rh_max_pct": 50, "wind_max_kmh": 10}),
        compute_forecast_risk_for_row({"rainfall_mm": 25, "temp_max_c": 30, "rh_max_pct": 50, "wind_max_kmh": 10}),
    ]
    worst = worst_case_risk(daily)
    assert worst["heavy_rain_risk"]["level"] == "HIGH"


def test_condition_label_from_real_rainfall():
    assert condition_label(5) == "Rain"
    assert condition_label(0) == "Clear"
    assert condition_label(None) == "Unknown"


def test_insights_rainfall_trend_only_when_significant():
    historical = {"available": True, "range_days": 8, "rainfall": [{"date": f"d{i}", "mm": v} for i, v in enumerate([1, 1, 1, 1, 5, 5, 5, 5])], "humidity": []}
    insights = generate_insights(historical, [], None, {"available": False})
    texts = [i["text"] for i in insights]
    assert any("increased" in t for t in texts)
    assert all(i["source_type"] == "weather_history" for i in insights)


def test_insights_no_trend_when_flat():
    historical = {"available": True, "range_days": 8, "rainfall": [{"date": f"d{i}", "mm": 2} for i in range(8)], "humidity": []}
    insights = generate_insights(historical, [], None, {"available": False})
    assert insights == []


def test_insights_forecast_rain(monkeypatch=None):
    historical = {"available": False}
    forecast_rows = [{"date": "2026-09-28", "rainfall_mm": 0}, {"date": "2026-09-29", "rainfall_mm": 12}]
    insights = generate_insights(historical, forecast_rows, None, {"available": False})
    assert any(i["source_type"] == "forecast" for i in insights)
    assert any("2026-09-29" in i["text"] for i in insights)


def test_insights_disease_risk_when_medium():
    historical = {"available": False}
    disease_risk = {"available": True, "level": "MEDIUM", "why": "high humidity"}
    insights = generate_insights(historical, [], None, disease_risk)
    assert any(i["source_type"] == "derived_rule" for i in insights)


def test_insights_empty_when_no_real_data_at_all():
    historical = {"available": False}
    insights = generate_insights(historical, [], None, {"available": False})
    assert insights == []
