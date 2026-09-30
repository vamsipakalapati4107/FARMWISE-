"""Phase 5: Smart Alerts & Early Warning System -- the alert-generation
engine. Pure functions, no DB access (the router owns persistence/dedup).

Reuses, rather than re-derives:
  - analytics.compute_forecast_risk_for_row  (Phase 4's forward-looking
    forecast risk classification, used here for the "early warning" look-
    ahead across all real forecast days, not just today)
  - farm_advisor.build_recommendations       (Phase 1 -- irrigation/
    general-operations statuses feed Irrigation Concern / Farm Operation
    alerts directly; no second recommendation engine)
  - crop_health.build_disease_risk           (Phase 2)

Two alert types in the spec (Strong Wind, Crop Stress) are deliberately
NEVER generated: no wind-risk threshold and no crop-stress model exist
anywhere in this project (see docs/FOUNDATION.md / src/analytics.py).
Generating them would mean inventing a threshold or a model that isn't
there. They stay defined in ALERT_TYPES for the frontend's filter list,
simply never populated.
"""
from __future__ import annotations

from analytics import compute_forecast_risk_for_row

ALERT_TYPES = [
    "heavy_rainfall",
    "heat_risk",
    "strong_wind",  # never generated -- no threshold exists
    "excess_moisture",
    "disease_risk",
    "crop_stress",  # never generated -- no model exists
    "crop_health_decline",
    "irrigation_concern",
    "farm_operation",
]

SEVERITY_ORDER = {"critical": 3, "warning": 2, "attention": 1, "info": 0}
HEALTH_ORDER = {"POOR": 0, "FAIR": 1, "GOOD": 2}


def _rec_by_category(recommendations: list[dict], category: str) -> dict | None:
    return next((r for r in recommendations if r["category"] == category), None)


def generate_candidate_alerts(
    *,
    farm_id: str,
    plot_id: str | None,
    today_date: str,
    forecast_rows: list[dict],
    disease_risk: dict,
    recommendations: list[dict],
    previous_health_status: str | None,
    current_health_status: str | None,
) -> list[dict]:
    """Returns candidate alert dicts (no id/status/created_at -- the router
    assigns those on insert). Each carries a `dedupe_key` the router checks
    against existing rows before inserting."""
    alerts: list[dict] = []
    key_prefix = f"{farm_id}:{plot_id or 'none'}"

    # -- Forward-looking forecast risks (heavy rain, heat) across every real
    # forecast day, today included. This is the "early warning" lookahead:
    # a future day crossing the threshold becomes a `warning`-severity
    # alert now, before it happens; the SAME day, once it becomes "today",
    # naturally escalates to `critical` on that day's alert instead
    # (different dedupe_key per date, so both can legitimately coexist).
    for row in forecast_rows:
        risk = compute_forecast_risk_for_row(row)
        is_today = row["date"] == today_date

        if risk["heavy_rain_risk"]["level"] == "HIGH":
            alerts.append(
                {
                    "alert_type": "heavy_rainfall",
                    "severity": "critical" if is_today else "warning",
                    "title": "Heavy Rainfall Today" if is_today else f"Heavy Rainfall Expected ({row['date']})",
                    "condition": f"{row['rainfall_mm']:.1f}mm rainfall" if row.get("rainfall_mm") is not None else "Heavy rainfall",
                    "reason": "Weather forecast indicates rainfall above the heavy-rain threshold.",
                    "recommended_action": "Delay irrigation and secure vulnerable farm operations."
                    if is_today
                    else "Consider delaying irrigation and reassess after the rainfall event.",
                    "source": "weather_forecast",
                    "valid_until": row["date"],
                    "dedupe_key": f"{key_prefix}:heavy_rainfall:weather_forecast:{row['date']}",
                }
            )

        if risk["heat_risk"]["level"] == "HIGH":
            alerts.append(
                {
                    "alert_type": "heat_risk",
                    "severity": "critical" if is_today else "warning",
                    "title": "Heat Risk Today" if is_today else f"Heat Risk Expected ({row['date']})",
                    "condition": f"{row['temp_max_c']:.1f}°C forecast" if row.get("temp_max_c") is not None else "High temperature",
                    "reason": "Weather forecast indicates temperature above the heat-stress threshold.",
                    "recommended_action": "Irrigate early morning or evening; avoid fieldwork during peak heat.",
                    "source": "weather_forecast",
                    "valid_until": row["date"],
                    "dedupe_key": f"{key_prefix}:heat_risk:weather_forecast:{row['date']}",
                }
            )

        # Excess moisture -- a real, derived combination of two existing
        # real signals (rainfall + humidity), not a soil-moisture sensor
        # reading (no such data source exists in this project).
        if risk["heavy_rain_risk"]["level"] in ("MEDIUM", "HIGH") and risk["humidity_risk"]["level"] == "HIGH":
            alerts.append(
                {
                    "alert_type": "excess_moisture",
                    "severity": "warning",
                    "title": "Excess Moisture Risk" if is_today else f"Excess Moisture Risk Expected ({row['date']})",
                    "condition": f"{row.get('rainfall_mm')}mm rainfall with {row.get('rh_max_pct')}% humidity",
                    "reason": "Combined rainfall and humidity levels favor waterlogging/excess moisture conditions.",
                    "recommended_action": "Check field drainage; avoid additional irrigation.",
                    "source": "derived_assessment",
                    "valid_until": row["date"],
                    "dedupe_key": f"{key_prefix}:excess_moisture:derived_assessment:{row['date']}",
                }
            )

    # -- Disease risk (Phase 2, reused not re-derived) --
    if disease_risk["available"] and disease_risk["level"] == "MEDIUM":
        alerts.append(
            {
                "alert_type": "disease_risk",
                "severity": "warning",
                "title": "Disease Risk Elevated",
                "condition": disease_risk["level"],
                "reason": disease_risk["why"],
                "recommended_action": "Inspect the crop for early disease symptoms; consider a preventive fungicide.",
                "source": "derived_assessment",
                "valid_until": today_date,
                "dedupe_key": f"{key_prefix}:disease_risk:derived_assessment:{today_date}",
            }
        )

    # -- Irrigation Concern / Farm Operation: reuse Phase 1's recommendations
    # verbatim (same engine, no duplicated logic) --
    irrigation = _rec_by_category(recommendations, "irrigation")
    if irrigation and irrigation["status"] != "normal":
        alerts.append(
            {
                "alert_type": "irrigation_concern",
                "severity": "attention" if irrigation["status"] == "recommended" else "warning",
                "title": f"Irrigation: {irrigation['status'].capitalize()}",
                "condition": irrigation["status"],
                "reason": irrigation["why"],
                "recommended_action": irrigation["what"],
                "source": "advisory_engine",
                "valid_until": today_date,
                "dedupe_key": f"{key_prefix}:irrigation_concern:advisory_engine:{today_date}",
            }
        )

    general_ops = _rec_by_category(recommendations, "general_operations")
    if general_ops and general_ops["status"] == "avoid":
        alerts.append(
            {
                "alert_type": "farm_operation",
                "severity": "warning",
                "title": "Important Farm Operation Notice",
                "condition": general_ops["status"],
                "reason": general_ops["why"],
                "recommended_action": general_ops["what"],
                "source": "advisory_engine",
                "valid_until": today_date,
                "dedupe_key": f"{key_prefix}:farm_operation:advisory_engine:{today_date}",
            }
        )

    # -- Crop Health Decline: only when 2 genuine, real logged observations
    # exist (see HealthSnapshot) -- never a fabricated "previous" value. --
    if (
        previous_health_status
        and current_health_status
        and previous_health_status in HEALTH_ORDER
        and current_health_status in HEALTH_ORDER
        and HEALTH_ORDER[current_health_status] < HEALTH_ORDER[previous_health_status]
    ):
        alerts.append(
            {
                "alert_type": "crop_health_decline",
                "severity": "warning",
                "title": "Crop Health Declining",
                "condition": f"{previous_health_status} → {current_health_status}",
                "reason": "Crop health assessment has worsened compared to the last recorded observation.",
                "recommended_action": "Inspect the field and review disease/weather conditions.",
                "source": "derived_assessment",
                "valid_until": today_date,
                "dedupe_key": f"{key_prefix}:crop_health_decline:derived_assessment:{today_date}",
            }
        )

    return alerts
