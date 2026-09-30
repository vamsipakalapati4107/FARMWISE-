"""Phase 12: crop-stage-aware agro-advisory.

Extends the generic, weather-only rules in advisory_rules.py with a small,
explicit override table keyed on (condition, crop, stage) -- same
config-driven, no-black-box philosophy as VARIABLE_SPECS in
train_downscaling_model.py. A crop/stage combination with no override still
gets the generic advisory, so this only ever adds specificity, never removes
coverage.

Run standalone for a quick manual check:
    python src/crop_advisory_rules.py
"""
from __future__ import annotations

import pandas as pd

from advisory_rules import (
    HEAT_STRESS_THRESHOLD_C,
    HEAVY_RAIN_THRESHOLD_MM,
    HUMID_RAIN_THRESHOLD_MM,
    HUMID_RH_THRESHOLD_PCT,
)

# condition -> crop_name -> (stages that get this override) -> action text
CROP_STAGE_ADVISORY_OVERRIDES: dict[str, dict[str, dict[tuple[str, ...], str]]] = {
    "heavy_rain": {
        "Cotton": {
            ("Flowering", "Boll Formation"): (
                "Rain during flowering/boll formation risks flower drop and boll rot. "
                "Delay spraying; inspect bolls for rot once the rain clears."
            ),
        },
        "Paddy (Rice)": {
            ("Flowering", "Grain Filling"): (
                "Standing water is normal for paddy at this stage, but check that drainage "
                "channels are clear so fields don't over-flood."
            ),
        },
    },
    "heat_stress": {
        "Paddy (Rice)": {
            ("Flowering",): (
                "Heat during flowering increases spikelet sterility risk. "
                "Irrigate to cool the canopy in the early morning."
            ),
        },
        "Chilli": {
            ("Flowering", "Fruiting"): (
                "High heat during flowering/fruiting can cause flower and fruit drop. "
                "Increase irrigation frequency during this stage."
            ),
        },
    },
    "fungal_risk": {
        "Turmeric": {
            ("Rhizome Development",): (
                "High humidity with rain increases rhizome rot risk. "
                "Ensure field drainage and avoid waterlogging around the rhizome bed."
            ),
        },
        "Groundnut": {
            ("Pegging", "Pod Development"): (
                "Humid, wet conditions favor collar rot and leaf spot at this stage. "
                "Consider a preventive fungicide and avoid waterlogged soil."
            ),
        },
    },
}

GENERIC_ADVISORY = {
    "heavy_rain": {
        "what": "Heavy rain expected (over 20mm).",
        "why": "Waterlogged fields and washed-off spray reduce yield and waste input cost.",
        "action": "Delay spraying and harvest; check field drainage before the rain arrives.",
        "severity": "critical",
    },
    "heat_stress": {
        "what": "High daytime temperature expected (over 38°C).",
        "why": "Midday heat stresses crops and increases water loss.",
        "action": "Irrigate early morning or evening; avoid fieldwork during peak heat.",
        "severity": "critical",
    },
    "fungal_risk": {
        "what": "High humidity together with rain expected.",
        "why": "These conditions favor fungal disease spread on standing crops.",
        "action": "Monitor crops closely for symptoms; consider a preventive fungicide.",
        "severity": "warning",
    },
    "normal": {
        "what": "No significant weather risk.",
        "why": "Conditions are within normal range for the day.",
        "action": "Continue normal farm operations.",
        "severity": "safe",
    },
}


def classify_condition(row) -> str:
    """Same branch order as advisory_rules.generate_advisory() -- returns the
    condition key instead of the rendered sentence."""
    rainfall_mm = row.get("rainfall_mm")
    temp_max_c = row.get("temp_max_c")
    rh_max_pct = row.get("rh_max_pct")

    if pd.notna(rainfall_mm) and rainfall_mm > HEAVY_RAIN_THRESHOLD_MM:
        return "heavy_rain"
    if pd.notna(temp_max_c) and temp_max_c > HEAT_STRESS_THRESHOLD_C:
        return "heat_stress"
    if (
        pd.notna(rh_max_pct)
        and pd.notna(rainfall_mm)
        and rh_max_pct > HUMID_RH_THRESHOLD_PCT
        and rainfall_mm > HUMID_RAIN_THRESHOLD_MM
    ):
        return "fungal_risk"
    return "normal"


def generate_crop_advisory(row, crop_name: str, stage: str) -> dict:
    """row must support `.get(key)` (a dict or pandas Series). Returns
    {severity, condition, what, why, action, crop_name, stage}."""
    condition = classify_condition(row)
    generic = GENERIC_ADVISORY[condition]

    override_action = (
        CROP_STAGE_ADVISORY_OVERRIDES.get(condition, {})
        .get(crop_name, {})
    )
    action = generic["action"]
    for stages, override_text in override_action.items():
        if stage in stages:
            action = override_text
            break

    return {
        "severity": generic["severity"],
        "condition": condition,
        "what": generic["what"],
        "why": generic["why"],
        "action": action,
        "crop_name": crop_name,
        "stage": stage,
    }


if __name__ == "__main__":
    sample_row = {"rainfall_mm": 25, "temp_max_c": 30, "rh_max_pct": 60}
    print(generate_crop_advisory(sample_row, "Cotton", "Flowering"))
