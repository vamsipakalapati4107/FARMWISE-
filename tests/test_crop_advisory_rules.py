from crop_advisory_rules import classify_condition, generate_crop_advisory


def test_classify_heavy_rain():
    row = {"rainfall_mm": 25, "temp_max_c": 30, "rh_max_pct": 60}
    assert classify_condition(row) == "heavy_rain"


def test_classify_heat_stress():
    row = {"rainfall_mm": 0, "temp_max_c": 40, "rh_max_pct": 50}
    assert classify_condition(row) == "heat_stress"


def test_classify_fungal_risk():
    row = {"rainfall_mm": 10, "temp_max_c": 30, "rh_max_pct": 90}
    assert classify_condition(row) == "fungal_risk"


def test_classify_normal():
    row = {"rainfall_mm": 2, "temp_max_c": 28, "rh_max_pct": 50}
    assert classify_condition(row) == "normal"


def test_priority_heavy_rain_over_heat_stress():
    # Both heavy rain and heat-stress thresholds are exceeded -- heavy rain wins.
    row = {"rainfall_mm": 25, "temp_max_c": 40, "rh_max_pct": 50}
    assert classify_condition(row) == "heavy_rain"


def test_cotton_flowering_heavy_rain_gets_override():
    row = {"rainfall_mm": 25, "temp_max_c": 30, "rh_max_pct": 60}
    result = generate_crop_advisory(row, "Cotton", "Flowering")
    assert result["condition"] == "heavy_rain"
    assert result["severity"] == "critical"
    assert "boll rot" in result["action"]


def test_cotton_vegetative_heavy_rain_falls_back_to_generic():
    # Same weather, but Vegetative stage has no override -- generic action.
    row = {"rainfall_mm": 25, "temp_max_c": 30, "rh_max_pct": 60}
    result = generate_crop_advisory(row, "Cotton", "Vegetative")
    assert result["condition"] == "heavy_rain"
    assert result["action"] == "Delay spraying and harvest; check field drainage before the rain arrives."


def test_paddy_flowering_heat_stress_gets_override():
    row = {"rainfall_mm": 0, "temp_max_c": 40, "rh_max_pct": 50}
    result = generate_crop_advisory(row, "Paddy (Rice)", "Flowering")
    assert "sterility" in result["action"]


def test_turmeric_rhizome_development_fungal_risk_gets_override():
    row = {"rainfall_mm": 10, "temp_max_c": 30, "rh_max_pct": 90}
    result = generate_crop_advisory(row, "Turmeric", "Rhizome Development")
    assert "rhizome rot" in result["action"]


def test_unknown_crop_falls_back_to_generic():
    row = {"rainfall_mm": 25, "temp_max_c": 30, "rh_max_pct": 60}
    result = generate_crop_advisory(row, "Maize", "Tasseling")
    assert result["action"] == "Delay spraying and harvest; check field drainage before the rain arrives."


def test_normal_conditions_return_safe_severity_for_any_crop():
    row = {"rainfall_mm": 2, "temp_max_c": 28, "rh_max_pct": 50}
    result = generate_crop_advisory(row, "Cotton", "Flowering")
    assert result["severity"] == "safe"
    assert result["condition"] == "normal"


def test_boundary_exact_threshold_is_not_triggered():
    # Exactly at threshold (not "over") should not trigger heavy rain, matching
    # advisory_rules.generate_advisory()'s strict `>` comparison.
    row = {"rainfall_mm": 20, "temp_max_c": 30, "rh_max_pct": 60}
    assert classify_condition(row) == "normal"


def test_missing_values_do_not_crash():
    row = {"rainfall_mm": None, "temp_max_c": None, "rh_max_pct": None}
    result = generate_crop_advisory(row, "Cotton", "Flowering")
    assert result["condition"] == "normal"
