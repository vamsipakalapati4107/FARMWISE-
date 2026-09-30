"""Phase 2: Crop Health & Stress Intelligence.

No trained crop-health or crop-stress model exists in this project (see
docs/FOUNDATION.md / src/ml_audit.py -- the only trained model is the
rainfall downscaler). This module NEVER invents one. It reuses Phase 1's
disease/weather risk functions (no duplicated advisory logic) and combines
them into a transparently rule-based "Crop Condition Assessment" -- always
labeled as such, never presented as an ML score or probability.

Every output carries a `source_type`, one of:
    ml_prediction | weather_data | soil_data | spatial_estimation
    | derived_assessment | unavailable
"""
from __future__ import annotations

from advisory_rules import HEAT_STRESS_THRESHOLD_C, HEAVY_RAIN_THRESHOLD_MM, HUMID_RAIN_THRESHOLD_MM, HUMID_RH_THRESHOLD_PCT
from farm_advisor import _is_na, build_disease_risk, build_weather_risk, now_iso

SOURCE_TYPES = [
    "ml_prediction",
    "weather_data",
    "soil_data",
    "spatial_estimation",
    "derived_assessment",
    "unavailable",
]


def build_crop_health(disease_risk: dict, weather_risk: dict) -> dict:
    """No trained health model exists -- this is a transparent, rule-based
    combination of the two existing risk signals (both already rule-based,
    reused from farm_advisor.py, not recomputed here). Status only
    (GOOD/FAIR/POOR), never a fabricated numeric score."""
    if not disease_risk["available"] or not weather_risk["available"]:
        return {
            "available": False,
            "status": None,
            "label": None,
            "source_type": "unavailable",
            "reason": "Insufficient weather data to assess crop condition for this plot today.",
        }

    elevated = int(disease_risk["level"] == "MEDIUM") + int(weather_risk["level"] == "HIGH")
    status = "GOOD" if elevated == 0 else "FAIR" if elevated == 1 else "POOR"

    return {
        "available": True,
        "status": status,
        "label": "Data-Based Assessment",
        "source_type": "derived_assessment",
        "reason": (
            f"Based on {disease_risk['level'].lower()} disease risk and "
            f"{weather_risk['level'].lower()} weather risk -- not an ML prediction."
        ),
    }


def build_crop_stress() -> dict:
    """Always unavailable -- no trained crop-stress model exists. Predicting
    stress would need physiological indicators (soil moisture, canopy
    temperature, NDVI) that this project does not collect. Deliberately has
    no rule-based fallback, per the stricter requirement for stress vs.
    health."""
    return {
        "available": False,
        "status": None,
        "source_type": "unavailable",
        "reason": (
            "No trained crop-stress model exists. Predicting stress would require "
            "physiological indicators such as soil moisture, canopy temperature, or "
            "satellite (NDVI) data, none of which this project currently collects."
        ),
    }


def build_factors(
    rainfall_mm: float | None,
    rainfall_source: str,
    temp_max_c: float | None,
    rh_max_pct: float | None,
    disease_risk: dict,
    weather_risk: dict,
    crop_stage: str | None,
) -> list[dict]:
    """One entry per factor, each carrying `available` + `source_type`.
    Frontend "WHY?" list should filter to available=True; the compact
    factor-card grid shows all of them (including unavailable ones, e.g.
    soil moisture, exactly as the fixed card layout expects)."""
    factors: list[dict] = []

    if _is_na(temp_max_c):
        factors.append({"key": "temperature", "label": "Temperature", "value": None, "status": "Unknown", "available": False, "source_type": "unavailable"})
    else:
        factors.append(
            {
                "key": "temperature",
                "label": "Temperature",
                "value": f"{temp_max_c:.1f}°C",
                "status": "Suitable" if temp_max_c <= HEAT_STRESS_THRESHOLD_C else "High",
                "available": True,
                "source_type": "weather_data",
            }
        )

    if _is_na(rh_max_pct):
        factors.append({"key": "humidity", "label": "Humidity", "value": None, "status": "Unknown", "available": False, "source_type": "unavailable"})
    else:
        factors.append(
            {
                "key": "humidity",
                "label": "Humidity",
                "value": f"{rh_max_pct:.0f}%",
                "status": "High" if rh_max_pct > HUMID_RH_THRESHOLD_PCT else "Normal",
                "available": True,
                "source_type": "weather_data",
            }
        )

    if _is_na(rainfall_mm):
        factors.append({"key": "rainfall", "label": "Rainfall", "value": None, "status": "Unknown", "available": False, "source_type": "unavailable"})
    else:
        if rainfall_mm > HEAVY_RAIN_THRESHOLD_MM:
            rain_status = "Above Normal"
        elif rainfall_mm > HUMID_RAIN_THRESHOLD_MM:
            rain_status = "Elevated"
        else:
            rain_status = "Normal"
        # rainfall's source_type reflects how *this specific value* was
        # derived: the real RF model's GP-level output, or the rule-based
        # IDW spatial estimate on top of it (see src/spatial.py).
        factors.append(
            {
                "key": "rainfall",
                "label": "Rainfall",
                "value": f"{rainfall_mm:.1f}mm",
                "status": rain_status,
                "available": True,
                "source_type": "spatial_estimation" if rainfall_source == "estimated_downscaled" else "ml_prediction",
            }
        )

    factors.append(
        {
            "key": "disease_risk",
            "label": "Disease Risk",
            "value": disease_risk["level"],
            "status": disease_risk["level"] or "Unknown",
            "available": disease_risk["available"],
            "source_type": "derived_assessment" if disease_risk["available"] else "unavailable",
        }
    )
    factors.append(
        {
            "key": "weather_risk",
            "label": "Weather Risk",
            "value": weather_risk["level"],
            "status": weather_risk["level"] or "Unknown",
            "available": weather_risk["available"],
            "source_type": "derived_assessment" if weather_risk["available"] else "unavailable",
        }
    )
    factors.append(
        {
            "key": "growth_stage",
            "label": "Growth Stage",
            "value": crop_stage,
            "status": crop_stage or "Unknown",
            "available": crop_stage is not None,
            # Recorded farm data, not weather/ML/spatial -- closest fit in
            # the fixed source_type set is derived_assessment (real,
            # user-recorded data, not a raw sensor/weather reading).
            "source_type": "derived_assessment" if crop_stage else "unavailable",
        }
    )
    # No soil-moisture sensor/data source exists anywhere in this project
    # (Farm.soil_type is a categorical descriptor like "Black soil", not a
    # moisture measurement) -- always unavailable, never invented.
    factors.append(
        {
            "key": "soil_moisture",
            "label": "Soil Moisture",
            "value": None,
            "status": "Unknown",
            "available": False,
            "source_type": "unavailable",
        }
    )

    return factors


def build_explanation() -> dict:
    """No trained model backs health/stress, so there is no real feature
    importance / SHAP / coefficient data to show. Never simulated."""
    return {
        "available": False,
        "reason": "Feature-level explanation is not available for this model.",
    }


def build_health_trend() -> dict:
    """Crop health is a new concept introduced this phase -- there is, by
    definition, no logged history of it yet. Never fabricated."""
    return {
        "available": False,
        "reason": "Historical crop-health data will appear after sufficient observations are collected.",
    }


__all__ = [
    "SOURCE_TYPES",
    "build_crop_health",
    "build_crop_stress",
    "build_factors",
    "build_explanation",
    "build_health_trend",
    "now_iso",
]
