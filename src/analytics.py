"""Phase 4: Historical + Forecast Analytics.

Reuses two REAL, previously-unused-by-the-API data sources instead of
inventing anything:
  - data/processed/panchayat_weather/<gp>.csv -- real 2025 daily ERA5-Land
    reanalysis per GP (365 days), used in Phase 3's training pipeline but
    never previously exposed via any API endpoint.
  - The existing 5-day block forecast (already served by /forecast, /weather).

The historical file's last real date is 2025-12-31, not "today" (the system
date is in 2026) -- so 7D/30D/90D windows are the most recent N days of
REAL recorded data available, not literally "the last N days before today".
Every response states its actual date range so this is never ambiguous.

No historical log of "disease risk" or "crop health" exists anywhere (both
are computed fresh per request in Phase 1/2, never persisted) -- so those
trends are always reported unavailable here. This module does not backtest
today's rules against 2025 weather to manufacture a pretend trend; that
would not be a genuine observed history, only a replay.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from advisory_rules import HEAT_STRESS_THRESHOLD_C, HEAVY_RAIN_THRESHOLD_MM, HUMID_RAIN_THRESHOLD_MM, HUMID_RH_THRESHOLD_PCT
from utils import safe_filename

WEATHER_DIR = Path(__file__).resolve().parent.parent / "data" / "processed" / "panchayat_weather"

SUPPORTED_RANGES = [7, 30, 90]


def _is_na(value) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value))


def load_full_history(gp_name: str) -> pd.DataFrame | None:
    path = WEATHER_DIR / f"{safe_filename(gp_name)}.csv"
    if not path.exists():
        return None
    return pd.read_csv(path)


def available_ranges(total_days: int) -> dict[int, bool]:
    return {r: total_days >= r for r in SUPPORTED_RANGES}


def load_historical_weather(gp_name: str, days: int) -> dict:
    """Real ERA5-Land observations only -- never fabricated. See module
    docstring for why the date range may not end "today"."""
    full = load_full_history(gp_name)
    if full is None:
        return {
            "available": False,
            "reason": f"No historical weather file exists for '{gp_name}'.",
            "source_type": "weather_observation",
        }
    if days > len(full):
        return {
            "available": False,
            "reason": f"Only {len(full)} days of historical data exist; {days} were requested.",
            "source_type": "weather_observation",
        }

    window = full.tail(days).reset_index(drop=True)
    return {
        "available": True,
        "range_days": days,
        "start_date": window["time"].iloc[0],
        "end_date": window["time"].iloc[-1],
        "temperature": [
            {"date": r["time"], "max_c": r["temperature_2m_max"], "min_c": r["temperature_2m_min"]}
            for _, r in window.iterrows()
        ],
        "rainfall": [{"date": r["time"], "mm": r["precipitation_sum"]} for _, r in window.iterrows()],
        "humidity": [{"date": r["time"], "max_pct": r["relative_humidity_2m_max"]} for _, r in window.iterrows()],
        "wind": [{"date": r["time"], "max_kmh": r["wind_speed_10m_max"]} for _, r in window.iterrows()],
        "source_type": "weather_observation",
        "note": "ERA5-Land reanalysis (used as proxy ground truth elsewhere in this project) -- "
        "the most recent available window of real historical data, not necessarily ending today.",
    }


def compute_rainfall_analytics(historical: dict, full_year_df: pd.DataFrame | None) -> dict:
    if not historical["available"]:
        return {"available": False, "reason": "No historical rainfall data available for this period."}

    values = [r["mm"] for r in historical["rainfall"]]
    total = sum(values)
    average = total / len(values) if values else 0.0
    rainy_days = sum(1 for v in values if v > 0)
    highest_day = max(historical["rainfall"], key=lambda r: r["mm"])

    result = {
        "available": True,
        "total_mm": round(total, 1),
        "average_mm_per_day": round(average, 2),
        "rainy_days": rainy_days,
        "highest_day": highest_day,
        "source_type": "weather_observation",
        "comparison": None,
    }

    if full_year_df is not None and len(full_year_df) > 0:
        reference_avg = float(full_year_df["precipitation_sum"].mean())
        result["comparison"] = {
            "available": True,
            "recent_average_mm_per_day": round(average, 2),
            "reference_average_mm_per_day": round(reference_avg, 2),
            "reference_period": f"Full observed year ({full_year_df['time'].iloc[0]} to {full_year_df['time'].iloc[-1]})",
            "source_type": "weather_observation",
        }

    return result


def _risk_level(value, thresholds: dict) -> str:
    """thresholds: {"low_max": x, "high_min": y} -- reused, not invented,
    thresholds where they exist (rain/heat/humidity); MEDIUM may be
    structurally unreachable for a given dimension, same precedent as
    Phase 1's disease_risk (never fabricated to force a 3rd tier)."""
    if _is_na(value):
        return "UNKNOWN"
    if value <= thresholds["low_max"]:
        return "LOW"
    if value > thresholds["high_min"]:
        return "HIGH"
    return "MEDIUM"


def compute_forecast_risk_for_row(row: dict) -> dict:
    rainfall_mm = row.get("rainfall_mm")
    temp_max_c = row.get("temp_max_c")
    rh_max_pct = row.get("rh_max_pct")
    wind_max_kmh = row.get("wind_max_kmh")

    heavy_rain = _risk_level(rainfall_mm, {"low_max": HUMID_RAIN_THRESHOLD_MM, "high_min": HEAVY_RAIN_THRESHOLD_MM})
    heat = _risk_level(temp_max_c, {"low_max": HEAT_STRESS_THRESHOLD_C, "high_min": HEAT_STRESS_THRESHOLD_C})
    humidity = _risk_level(rh_max_pct, {"low_max": HUMID_RH_THRESHOLD_PCT, "high_min": HUMID_RH_THRESHOLD_PCT})

    return {
        "heavy_rain_risk": {
            "level": heavy_rain,
            "source_type": "derived_assessment",
            "label": "Derived from forecast conditions",
            "value_mm": rainfall_mm,
        },
        "heat_risk": {
            "level": heat,
            "source_type": "derived_assessment",
            "label": "Derived from forecast conditions",
            "value_c": temp_max_c,
        },
        "humidity_risk": {
            "level": humidity,
            "source_type": "derived_assessment",
            "label": "Derived from forecast conditions",
            "value_pct": rh_max_pct,
        },
        # No wind-risk threshold has ever been established anywhere in this
        # project (unlike rain/heat/humidity, which all reuse Phase 1
        # constants) -- rather than invent an ungrounded cutoff, this stays
        # honestly unclassified. The real wind value is still shown.
        "wind_risk": {
            "level": "UNKNOWN",
            "source_type": "unavailable",
            "label": "No wind-risk threshold is established in this system yet",
            "value_kmh": wind_max_kmh,
        },
    }


def worst_case_risk(daily_risks: list[dict]) -> dict:
    order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNKNOWN": 0}
    result = {}
    for key in ["heavy_rain_risk", "heat_risk", "humidity_risk", "wind_risk"]:
        worst = max(daily_risks, key=lambda d: order[d[key]["level"]])[key]
        result[key] = worst
    return result


def condition_label(rainfall_mm) -> str:
    """A simple, honestly-derived label from the real rainfall figure --
    not a separate weather-condition model."""
    if _is_na(rainfall_mm):
        return "Unknown"
    return "Rain" if rainfall_mm > 0 else "Clear"


def generate_insights(
    historical: dict,
    forecast_rows: list[dict],
    current_rh_max_pct,
    disease_risk: dict,
) -> list[dict]:
    """Every insight is only emitted when computable from real data --
    no filler, no invented trend when the underlying comparison isn't
    materially significant."""
    insights: list[dict] = []

    if historical["available"] and len(historical["rainfall"]) >= 4:
        values = [r["mm"] for r in historical["rainfall"]]
        midpoint = len(values) // 2
        first_half_avg = sum(values[:midpoint]) / midpoint
        second_half_avg = sum(values[midpoint:]) / (len(values) - midpoint)
        if first_half_avg > 0.1 and second_half_avg > first_half_avg * 1.2:
            insights.append(
                {
                    "text": f"Rainfall has increased over the last {historical['range_days']} available observations.",
                    "source_type": "weather_history",
                }
            )
        elif first_half_avg > 0.1 and second_half_avg < first_half_avg * 0.8:
            insights.append(
                {
                    "text": f"Rainfall has decreased over the last {historical['range_days']} available observations.",
                    "source_type": "weather_history",
                }
            )

    if historical["available"] and not _is_na(current_rh_max_pct):
        avg_humidity = sum(r["max_pct"] for r in historical["humidity"]) / len(historical["humidity"])
        if current_rh_max_pct > avg_humidity * 1.1:
            insights.append(
                {
                    "text": "Humidity is currently above the recent historical average.",
                    "source_type": "weather_history",
                }
            )

    future_rain_day = next((r for r in forecast_rows if not _is_na(r.get("rainfall_mm")) and r["rainfall_mm"] > 0), None)
    if future_rain_day:
        insights.append(
            {
                "text": f"Rain is forecast on {future_rain_day['date']}, the next available forecast period with rain.",
                "source_type": "forecast",
            }
        )

    if disease_risk["available"] and disease_risk["level"] == "MEDIUM":
        insights.append(
            {
                "text": f"Current conditions indicate elevated disease risk: {disease_risk['why']}",
                "source_type": "derived_rule",
            }
        )

    return insights
