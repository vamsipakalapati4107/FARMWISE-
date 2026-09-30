"""Phase 1: AI Farm Advisor.

A transparent RULE-BASED recommendation engine over farm/plot/crop context
plus existing weather data, the real rainfall ML model's output, and the
rule-based spatial (IDW) estimate from Phase 0.5. Nothing in this module is
itself a trained model -- it synthesizes existing REAL_ML_PREDICTION /
RAW_DATA_API_VALUE / PASS_THROUGH_VALUE / RULE_BASED_LOGIC values (see
src/ml_audit.py) into 6 category recommendations, and is careful never to
attribute a rule-based decision to "the ML model".

Thresholds are reused, not reinvented, from src/advisory_rules.py /
src/crop_advisory_rules.py (HEAVY_RAIN_THRESHOLD_MM, HEAT_STRESS_THRESHOLD_C,
HUMID_RH_THRESHOLD_PCT, HUMID_RAIN_THRESHOLD_MM).
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from advisory_rules import (
    HEAT_STRESS_THRESHOLD_C,
    HEAVY_RAIN_THRESHOLD_MM,
    HUMID_RAIN_THRESHOLD_MM,
    HUMID_RH_THRESHOLD_PCT,
)
from crop_advisory_rules import generate_crop_advisory

CATEGORIES = [
    "irrigation",
    "fertilizer",
    "disease_monitoring",
    "field_inspection",
    "weather_precautions",
    "general_operations",
]

STATUS_PRIORITY = {"avoid": 0, "delay": 1, "recommended": 2, "monitor": 3, "normal": 4}


def _is_na(value) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value))


def _fmt(value, suffix: str = "") -> str:
    return "an unknown amount" if _is_na(value) else f"{value:.1f}{suffix}"


def build_recommendations(
    rainfall_mm: float | None,
    temp_max_c: float | None,
    rh_max_pct: float | None,
    crop_name: str | None,
    stage: str | None,
) -> list[dict]:
    """Returns one entry per category in CATEGORIES, in that fixed order."""
    is_heavy_rain = not _is_na(rainfall_mm) and rainfall_mm > HEAVY_RAIN_THRESHOLD_MM
    is_heat_stress = not _is_na(temp_max_c) and temp_max_c > HEAT_STRESS_THRESHOLD_C
    is_fungal_risk = (
        not _is_na(rh_max_pct)
        and not _is_na(rainfall_mm)
        and rh_max_pct > HUMID_RH_THRESHOLD_PCT
        and rainfall_mm > HUMID_RAIN_THRESHOLD_MM
    )

    rain_s, temp_s, rh_s = _fmt(rainfall_mm, "mm"), _fmt(temp_max_c, "°C"), _fmt(rh_max_pct, "%")
    recs: list[dict] = []

    # -- Irrigation --
    if is_heavy_rain:
        recs.append(
            {
                "category": "irrigation",
                "status": "delay",
                "what": "Delay irrigation.",
                "why": f"Rainfall of {rain_s} is expected or estimated today, above the "
                f"{HEAVY_RAIN_THRESHOLD_MM}mm heavy-rain threshold.",
                "when": "Reassess after the next forecast update.",
                "data_sources": ["rainfall_forecast"],
            }
        )
    elif is_heat_stress:
        recs.append(
            {
                "category": "irrigation",
                "status": "recommended",
                "what": "Irrigate early morning or evening.",
                "why": f"Temperature of {temp_s} exceeds the {HEAT_STRESS_THRESHOLD_C}°C "
                "heat-stress threshold -- crops lose water faster in this heat.",
                "when": "Before midday heat sets in, or after sunset.",
                "data_sources": ["temperature_forecast"],
            }
        )
    else:
        recs.append(
            {
                "category": "irrigation",
                "status": "normal",
                "what": "Follow your regular irrigation schedule.",
                "why": "No significant rain or heat signal in today's forecast.",
                "when": "As per your usual schedule.",
                "data_sources": ["rainfall_forecast", "temperature_forecast"],
            }
        )

    # -- Fertilizer --
    if is_heavy_rain:
        recs.append(
            {
                "category": "fertilizer",
                "status": "avoid",
                "what": "Avoid applying fertilizer today.",
                "why": f"Rainfall of {rain_s} risks washing fertilizer away before the crop can absorb it.",
                "when": "Wait until after the rain clears and soil has drained.",
                "data_sources": ["rainfall_forecast"],
            }
        )
    elif is_heat_stress:
        recs.append(
            {
                "category": "fertilizer",
                "status": "delay",
                "what": "Delay fertilizer application.",
                "why": f"Temperature of {temp_s} may stress the crop further if fertilized now.",
                "when": "Apply during cooler conditions, early morning or evening.",
                "data_sources": ["temperature_forecast"],
            }
        )
    else:
        recs.append(
            {
                "category": "fertilizer",
                "status": "normal",
                "what": "No weather-related reason to delay fertilizer application.",
                "why": "Rain and temperature are both within normal range today.",
                "when": "Follow your planned schedule.",
                "data_sources": ["rainfall_forecast", "temperature_forecast"],
            }
        )

    # -- Disease monitoring --
    if is_fungal_risk:
        recs.append(
            {
                "category": "disease_monitoring",
                "status": "recommended",
                "what": "Inspect the crop for fungal disease symptoms.",
                "why": f"High humidity ({rh_s}) together with rainfall ({rain_s}) is associated "
                "with elevated fungal disease risk on standing crops.",
                "when": "Today, and again after the next rain.",
                "data_sources": ["humidity_forecast", "rainfall_forecast"],
            }
        )
    elif is_heavy_rain:
        recs.append(
            {
                "category": "disease_monitoring",
                "status": "monitor",
                "what": "Keep an eye out for disease symptoms after the rain clears.",
                "why": f"Heavy rain ({rain_s}) can create favorable conditions for fungal spread "
                "even without today's humidity crossing the disease-risk threshold.",
                "when": "In the 1-2 days after the rain.",
                "data_sources": ["rainfall_forecast"],
            }
        )
    else:
        recs.append(
            {
                "category": "disease_monitoring",
                "status": "normal",
                "what": "No elevated disease-risk signal today.",
                "why": "Humidity and rainfall are both below the disease-risk thresholds.",
                "when": "Continue routine monitoring.",
                "data_sources": ["humidity_forecast", "rainfall_forecast"],
            }
        )

    # -- Field inspection --
    if is_heavy_rain:
        recs.append(
            {
                "category": "field_inspection",
                "status": "avoid",
                "what": "Avoid walking the field today.",
                "why": f"Rainfall of {rain_s} likely means waterlogged, unsafe field conditions.",
                "when": "Wait until conditions dry out.",
                "data_sources": ["rainfall_forecast"],
            }
        )
    elif is_heat_stress:
        recs.append(
            {
                "category": "field_inspection",
                "status": "delay",
                "what": "Avoid inspection during peak heat.",
                "why": f"Temperature of {temp_s} makes midday fieldwork unsafe.",
                "when": "Inspect early morning or evening instead.",
                "data_sources": ["temperature_forecast"],
            }
        )
    elif is_fungal_risk:
        recs.append(
            {
                "category": "field_inspection",
                "status": "recommended",
                "what": "Walk the field to check crop condition closely.",
                "why": "Current humidity/rain conditions favor disease -- an in-person check "
                "catches early symptoms sooner.",
                "when": "Today.",
                "data_sources": ["humidity_forecast", "rainfall_forecast"],
            }
        )
    else:
        recs.append(
            {
                "category": "field_inspection",
                "status": "normal",
                "what": "Routine inspection schedule is sufficient.",
                "why": "No weather condition today requires an extra field visit.",
                "when": "As per your usual routine.",
                "data_sources": ["rainfall_forecast", "temperature_forecast"],
            }
        )

    # -- Weather precautions --
    if is_heavy_rain or is_heat_stress:
        hazard = f"heavy rain ({rain_s})" if is_heavy_rain else f"extreme heat ({temp_s})"
        recs.append(
            {
                "category": "weather_precautions",
                "status": "recommended",
                "what": "Take precautions for today's weather.",
                "why": f"Forecast conditions include {hazard}, which crosses a significant-risk threshold.",
                "when": "Today.",
                "data_sources": ["rainfall_forecast", "temperature_forecast"],
            }
        )
    elif is_fungal_risk:
        recs.append(
            {
                "category": "weather_precautions",
                "status": "monitor",
                "what": "Monitor conditions; no immediate precaution required.",
                "why": f"Humidity ({rh_s}) and rain ({rain_s}) are elevated but below the heavy-rain/heat thresholds.",
                "when": "Re-check tomorrow's forecast.",
                "data_sources": ["humidity_forecast", "rainfall_forecast"],
            }
        )
    else:
        recs.append(
            {
                "category": "weather_precautions",
                "status": "normal",
                "what": "No weather precautions needed today.",
                "why": "No significant-risk threshold was crossed in today's forecast.",
                "when": "N/A",
                "data_sources": ["rainfall_forecast", "temperature_forecast"],
            }
        )

    # -- General crop operations --
    if is_heavy_rain or is_heat_stress:
        recs.append(
            {
                "category": "general_operations",
                "status": "avoid",
                "what": "Avoid heavy fieldwork or machinery operation today.",
                "why": "Current weather conditions cross a significant-risk threshold for safe operations.",
                "when": "Resume once conditions normalize.",
                "data_sources": ["rainfall_forecast", "temperature_forecast"],
            }
        )
    elif is_fungal_risk:
        recs.append(
            {
                "category": "general_operations",
                "status": "monitor",
                "what": "Continue operations, but keep an eye on crop health.",
                "why": "Disease-favoring conditions are present, though not yet a hard stop for operations.",
                "when": "Ongoing.",
                "data_sources": ["humidity_forecast", "rainfall_forecast"],
            }
        )
    else:
        recs.append(
            {
                "category": "general_operations",
                "status": "normal",
                "what": "Normal farm operations can continue.",
                "why": "No significant weather risk in today's forecast.",
                "when": "N/A",
                "data_sources": ["rainfall_forecast", "temperature_forecast"],
            }
        )

    # -- Crop-stage specificity: if a crop+stage override exists (see
    # crop_advisory_rules.CROP_STAGE_ADVISORY_OVERRIDES), fold its more
    # specific text into whichever category it targets, without changing
    # the status already decided above (the override is a refinement of
    # the *reason*, not a different rule engine).
    if crop_name and stage:
        crop_specific = generate_crop_advisory(
            {"rainfall_mm": rainfall_mm, "temp_max_c": temp_max_c, "rh_max_pct": rh_max_pct}, crop_name, stage
        )
        generic_action_texts = {
            "heavy_rain": "Delay spraying and harvest; check field drainage before the rain arrives.",
            "heat_stress": "Irrigate early morning or evening; avoid fieldwork during peak heat.",
            "fungal_risk": "Monitor crops closely for symptoms; consider a preventive fungicide.",
            "normal": "Continue normal farm operations.",
        }
        if crop_specific["action"] != generic_action_texts.get(crop_specific["condition"]):
            target_category = {
                "heavy_rain": "irrigation",
                "heat_stress": "irrigation",
                "fungal_risk": "disease_monitoring",
            }.get(crop_specific["condition"])
            if target_category:
                for rec in recs:
                    if rec["category"] == target_category:
                        rec["why"] += f" For {crop_name} at {stage} stage specifically: {crop_specific['action']}"
                        rec["data_sources"].append("crop_stage_rule")

    return recs


def build_action_plan(recommendations: list[dict], max_items: int = 5) -> list[dict]:
    actionable = [r for r in recommendations if r["status"] != "normal"]
    actionable.sort(key=lambda r: STATUS_PRIORITY.get(r["status"], 99))
    return [
        {"priority": i + 1, "category": r["category"], "status": r["status"], "label": r["what"]}
        for i, r in enumerate(actionable[:max_items])
    ]


def build_disease_risk(rh_max_pct: float | None, rainfall_mm: float | None) -> dict:
    """LOW/MEDIUM only -- current rules never reach a HIGH disease tier, and
    there is no trained disease model, so no probability is reported.
    See docs/FOUNDATION.md / src/ml_audit.py."""
    if _is_na(rh_max_pct) or _is_na(rainfall_mm):
        return {
            "available": False,
            "level": None,
            "classification": "RULE_BASED_LOGIC",
            "why": "Insufficient humidity/rainfall data for this plot today.",
        }

    is_fungal_risk = rh_max_pct > HUMID_RH_THRESHOLD_PCT and rainfall_mm > HUMID_RAIN_THRESHOLD_MM
    return {
        "available": True,
        "level": "MEDIUM" if is_fungal_risk else "LOW",
        "classification": "RULE_BASED_LOGIC",
        "why": (
            f"High humidity ({rh_max_pct:.0f}%) together with rainfall ({rainfall_mm:.1f}mm) is "
            "associated with elevated predicted disease risk."
            if is_fungal_risk
            else f"Humidity ({rh_max_pct:.0f}%) and rainfall ({rainfall_mm:.1f}mm) are both below "
            "the disease-risk thresholds."
        ),
    }


def build_weather_risk(temp_max_c: float | None, rainfall_mm: float | None) -> dict:
    if _is_na(temp_max_c) or _is_na(rainfall_mm):
        return {"available": False, "level": None, "classification": "RULE_BASED_LOGIC", "why": "Insufficient weather data for this plot today."}

    is_heavy_rain = rainfall_mm > HEAVY_RAIN_THRESHOLD_MM
    is_heat_stress = temp_max_c > HEAT_STRESS_THRESHOLD_C
    if is_heavy_rain or is_heat_stress:
        hazard = f"heavy rain ({rainfall_mm:.1f}mm)" if is_heavy_rain else f"extreme heat ({temp_max_c:.1f}°C)"
        return {"available": True, "level": "HIGH", "classification": "RULE_BASED_LOGIC", "why": f"Forecast includes {hazard}."}
    return {
        "available": True,
        "level": "LOW",
        "classification": "RULE_BASED_LOGIC",
        "why": "Rainfall and temperature are both within normal range today.",
    }


def build_crop_condition(crop_name: str | None, stage: str | None) -> dict:
    """Honest stub -- no crop-health/NDVI model exists (see
    GET /plots/{id}/health). Growth stage is real data; a health SCORE is not."""
    if not crop_name:
        return {"available": False, "reason": "No crop is linked to this plot yet.", "crop_name": None, "stage": None}
    return {
        "available": False,
        "reason": "Crop health/vigor scoring is not implemented yet (no satellite/NDVI model). "
        "Showing the crop and growth stage you've recorded instead.",
        "crop_name": crop_name,
        "stage": stage,
    }


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()
