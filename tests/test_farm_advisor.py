from farm_advisor import (
    CATEGORIES,
    build_action_plan,
    build_crop_condition,
    build_disease_risk,
    build_recommendations,
    build_weather_risk,
)


def test_normal_weather_all_categories_normal():
    recs = build_recommendations(rainfall_mm=2, temp_max_c=28, rh_max_pct=50, crop_name=None, stage=None)
    assert {r["category"] for r in recs} == set(CATEGORIES)
    assert all(r["status"] == "normal" for r in recs)


def test_heavy_rain_triggers_delay_and_avoid_statuses():
    recs = build_recommendations(rainfall_mm=25, temp_max_c=30, rh_max_pct=60, crop_name=None, stage=None)
    by_cat = {r["category"]: r for r in recs}
    assert by_cat["irrigation"]["status"] == "delay"
    assert by_cat["fertilizer"]["status"] == "avoid"
    assert by_cat["field_inspection"]["status"] == "avoid"
    assert by_cat["weather_precautions"]["status"] == "recommended"
    assert by_cat["general_operations"]["status"] == "avoid"


def test_heat_stress_triggers_irrigation_recommended():
    recs = build_recommendations(rainfall_mm=0, temp_max_c=40, rh_max_pct=50, crop_name=None, stage=None)
    by_cat = {r["category"]: r for r in recs}
    assert by_cat["irrigation"]["status"] == "recommended"
    assert by_cat["fertilizer"]["status"] == "delay"
    assert by_cat["field_inspection"]["status"] == "delay"


def test_fungal_risk_triggers_disease_monitoring_recommended():
    recs = build_recommendations(rainfall_mm=10, temp_max_c=30, rh_max_pct=90, crop_name=None, stage=None)
    by_cat = {r["category"]: r for r in recs}
    assert by_cat["disease_monitoring"]["status"] == "recommended"
    assert by_cat["field_inspection"]["status"] == "recommended"
    assert by_cat["weather_precautions"]["status"] == "monitor"


def test_missing_values_do_not_crash_and_default_to_normal():
    recs = build_recommendations(rainfall_mm=None, temp_max_c=None, rh_max_pct=None, crop_name=None, stage=None)
    assert all(r["status"] == "normal" for r in recs)


def test_crop_stage_override_folded_into_reason():
    recs = build_recommendations(rainfall_mm=25, temp_max_c=30, rh_max_pct=60, crop_name="Cotton", stage="Flowering")
    irrigation = next(r for r in recs if r["category"] == "irrigation")
    assert "boll rot" in irrigation["why"]
    assert "crop_stage_rule" in irrigation["data_sources"]


def test_crop_stage_override_absent_for_unrelated_stage():
    recs = build_recommendations(rainfall_mm=25, temp_max_c=30, rh_max_pct=60, crop_name="Cotton", stage="Vegetative")
    irrigation = next(r for r in recs if r["category"] == "irrigation")
    assert "boll rot" not in irrigation["why"]


def test_action_plan_excludes_normal_and_orders_by_severity():
    recs = build_recommendations(rainfall_mm=25, temp_max_c=30, rh_max_pct=60, crop_name=None, stage=None)
    plan = build_action_plan(recs)
    assert all(item["status"] != "normal" for item in plan)
    statuses = [item["status"] for item in plan]
    # avoid/delay must appear before recommended/monitor
    assert statuses.index("avoid") < statuses.index("recommended") if "recommended" in statuses else True
    assert [item["priority"] for item in plan] == list(range(1, len(plan) + 1))


def test_action_plan_empty_when_all_normal():
    recs = build_recommendations(rainfall_mm=2, temp_max_c=28, rh_max_pct=50, crop_name=None, stage=None)
    assert build_action_plan(recs) == []


def test_disease_risk_medium_on_fungal_conditions():
    result = build_disease_risk(rh_max_pct=90, rainfall_mm=10)
    assert result["level"] == "MEDIUM"
    assert result["classification"] == "RULE_BASED_LOGIC"


def test_disease_risk_low_on_normal_conditions():
    result = build_disease_risk(rh_max_pct=50, rainfall_mm=2)
    assert result["level"] == "LOW"


def test_disease_risk_never_reports_high_or_probability():
    for rh, rain in [(95, 30), (100, 100), (99, 50)]:
        result = build_disease_risk(rh_max_pct=rh, rainfall_mm=rain)
        assert result["level"] in ("LOW", "MEDIUM")
        assert "probability" not in result


def test_disease_risk_unavailable_on_missing_data():
    result = build_disease_risk(rh_max_pct=None, rainfall_mm=10)
    assert result["available"] is False
    assert result["level"] is None


def test_weather_risk_high_on_heavy_rain():
    result = build_weather_risk(temp_max_c=30, rainfall_mm=25)
    assert result["level"] == "HIGH"


def test_weather_risk_low_on_normal_conditions():
    result = build_weather_risk(temp_max_c=28, rainfall_mm=2)
    assert result["level"] == "LOW"


def test_weather_risk_unavailable_on_missing_data():
    result = build_weather_risk(temp_max_c=None, rainfall_mm=None)
    assert result["available"] is False


def test_crop_condition_no_crop_linked():
    result = build_crop_condition(crop_name=None, stage=None)
    assert result["available"] is False
    assert "No crop" in result["reason"]


def test_crop_condition_with_crop_still_marked_unavailable():
    # Growth stage is real, but a health SCORE must never be fabricated.
    result = build_crop_condition(crop_name="Cotton", stage="Flowering")
    assert result["available"] is False
    assert result["crop_name"] == "Cotton"
    assert result["stage"] == "Flowering"
