from crop_health import (
    build_crop_health,
    build_crop_stress,
    build_explanation,
    build_factors,
    build_health_trend,
)
from farm_advisor import build_disease_risk, build_weather_risk


def test_crop_health_good_when_both_risks_low():
    disease = build_disease_risk(rh_max_pct=50, rainfall_mm=2)
    weather = build_weather_risk(temp_max_c=28, rainfall_mm=2)
    result = build_crop_health(disease, weather)
    assert result["status"] == "GOOD"
    assert result["source_type"] == "derived_assessment"
    assert result["label"] == "Data-Based Assessment"


def test_crop_health_fair_when_one_risk_elevated():
    disease = build_disease_risk(rh_max_pct=90, rainfall_mm=10)  # MEDIUM
    weather = build_weather_risk(temp_max_c=28, rainfall_mm=2)  # LOW
    result = build_crop_health(disease, weather)
    assert result["status"] == "FAIR"


def test_crop_health_poor_when_both_risks_elevated():
    disease = build_disease_risk(rh_max_pct=90, rainfall_mm=10)  # MEDIUM
    weather = build_weather_risk(temp_max_c=30, rainfall_mm=25)  # HIGH
    result = build_crop_health(disease, weather)
    assert result["status"] == "POOR"


def test_crop_health_unavailable_when_weather_missing():
    disease = build_disease_risk(rh_max_pct=None, rainfall_mm=None)
    weather = build_weather_risk(temp_max_c=None, rainfall_mm=None)
    result = build_crop_health(disease, weather)
    assert result["available"] is False
    assert result["status"] is None
    assert result["source_type"] == "unavailable"


def test_crop_health_never_returns_numeric_score():
    disease = build_disease_risk(rh_max_pct=90, rainfall_mm=10)
    weather = build_weather_risk(temp_max_c=30, rainfall_mm=25)
    result = build_crop_health(disease, weather)
    assert "value" not in result
    assert "score" not in result


def test_crop_stress_always_unavailable_no_fake_prediction():
    result = build_crop_stress()
    assert result["available"] is False
    assert result["status"] is None
    assert result["source_type"] == "unavailable"
    assert "soil moisture" in result["reason"].lower()


def test_factors_includes_only_real_values_marked_available():
    disease = build_disease_risk(rh_max_pct=90, rainfall_mm=10)
    weather = build_weather_risk(temp_max_c=30, rainfall_mm=10)
    factors = build_factors(
        rainfall_mm=10, rainfall_source="gp_level", temp_max_c=30, rh_max_pct=90,
        disease_risk=disease, weather_risk=weather, crop_stage="Flowering",
    )
    by_key = {f["key"]: f for f in factors}
    assert by_key["temperature"]["available"] is True
    assert by_key["humidity"]["status"] == "High"
    assert by_key["rainfall"]["source_type"] == "ml_prediction"
    assert by_key["growth_stage"]["value"] == "Flowering"
    # Soil moisture never has real data in this project.
    assert by_key["soil_moisture"]["available"] is False
    assert by_key["soil_moisture"]["status"] == "Unknown"


def test_factors_rainfall_source_type_reflects_spatial_estimation():
    disease = build_disease_risk(rh_max_pct=50, rainfall_mm=2)
    weather = build_weather_risk(temp_max_c=28, rainfall_mm=2)
    factors = build_factors(
        rainfall_mm=13.0, rainfall_source="estimated_downscaled", temp_max_c=28, rh_max_pct=50,
        disease_risk=disease, weather_risk=weather, crop_stage=None,
    )
    rainfall_factor = next(f for f in factors if f["key"] == "rainfall")
    assert rainfall_factor["source_type"] == "spatial_estimation"


def test_factors_missing_weather_marks_unavailable_not_fabricated():
    disease = build_disease_risk(rh_max_pct=None, rainfall_mm=None)
    weather = build_weather_risk(temp_max_c=None, rainfall_mm=None)
    factors = build_factors(
        rainfall_mm=None, rainfall_source="gp_level", temp_max_c=None, rh_max_pct=None,
        disease_risk=disease, weather_risk=weather, crop_stage=None,
    )
    by_key = {f["key"]: f for f in factors}
    assert by_key["temperature"]["available"] is False
    assert by_key["temperature"]["value"] is None
    assert by_key["growth_stage"]["available"] is False


def test_explanation_always_honest_unavailable():
    result = build_explanation()
    assert result["available"] is False
    assert "not available" in result["reason"].lower()


def test_health_trend_always_honest_empty_state():
    result = build_health_trend()
    assert result["available"] is False
    assert "historical" in result["reason"].lower()
