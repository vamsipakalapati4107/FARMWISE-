import pandas as pd

from advisory_rules import (
    FUNGAL_RISK_ADVISORY,
    HEAT_STRESS_ADVISORY,
    HEAVY_RAIN_ADVISORY,
    NORMAL_ADVISORY,
    generate_advisory,
)


def test_heavy_rain_triggers():
    row = {"rainfall_mm": 25, "temp_max_c": 30, "rh_max_pct": 60}
    assert generate_advisory(row) == HEAVY_RAIN_ADVISORY


def test_heat_stress_triggers():
    row = {"rainfall_mm": 0, "temp_max_c": 40, "rh_max_pct": 50}
    assert generate_advisory(row) == HEAT_STRESS_ADVISORY


def test_humidity_and_rain_triggers():
    row = {"rainfall_mm": 10, "temp_max_c": 30, "rh_max_pct": 90}
    assert generate_advisory(row) == FUNGAL_RISK_ADVISORY


def test_normal_operations():
    row = {"rainfall_mm": 2, "temp_max_c": 28, "rh_max_pct": 50}
    assert generate_advisory(row) == NORMAL_ADVISORY


def test_heavy_rain_takes_priority_over_other_rules():
    # Would also satisfy the humidity+rain rule, but heavy rain should win.
    row = {"rainfall_mm": 25, "temp_max_c": 30, "rh_max_pct": 90}
    assert generate_advisory(row) == HEAVY_RAIN_ADVISORY


def test_thresholds_are_strictly_greater_than():
    row = {"rainfall_mm": 20, "temp_max_c": 38, "rh_max_pct": 85}
    assert generate_advisory(row) == NORMAL_ADVISORY


def test_missing_values_handled_gracefully():
    row = {"rainfall_mm": None, "temp_max_c": None, "rh_max_pct": None}
    assert generate_advisory(row) == NORMAL_ADVISORY


def test_works_with_pandas_series():
    row = pd.Series({"rainfall_mm": 30, "temp_max_c": 32, "rh_max_pct": 70})
    assert generate_advisory(row) == HEAVY_RAIN_ADVISORY
