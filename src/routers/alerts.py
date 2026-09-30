"""Phase 11: structured weather alerts, restructuring the existing
threshold logic in src/advisory_rules.py (same thresholds, same rule
priority) into objects the frontend can render as alert cards instead of
a single sentence.
"""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException

from advisory_rules import (
    HEAT_STRESS_THRESHOLD_C,
    HEAVY_RAIN_THRESHOLD_MM,
    HUMID_RAIN_THRESHOLD_MM,
    HUMID_RH_THRESHOLD_PCT,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])


def build_alert(row: pd.Series) -> dict | None:
    """Returns None for rows with no significant risk -- "normal operations"
    isn't an alert. Priority order matches generate_advisory() exactly."""
    rainfall_mm = row.get("rainfall_mm")
    temp_max_c = row.get("temp_max_c")
    rh_max_pct = row.get("rh_max_pct")

    base = {
        "gram_panchayat": row["gram_panchayat"],
        "date": row["date"],
    }

    if pd.notna(rainfall_mm) and rainfall_mm > HEAVY_RAIN_THRESHOLD_MM:
        return {
            **base,
            "icon": "cloud-rain",
            "severity": "critical",
            "title": "Heavy rain",
            "description": f"{rainfall_mm:.1f}mm of rain expected, above the {HEAVY_RAIN_THRESHOLD_MM}mm threshold.",
            "action": "Delay spraying and harvest; ensure field drainage.",
        }

    if pd.notna(temp_max_c) and temp_max_c > HEAT_STRESS_THRESHOLD_C:
        return {
            **base,
            "icon": "sun",
            "severity": "critical",
            "title": "Extreme heat",
            "description": f"{temp_max_c:.1f}°C expected, above the {HEAT_STRESS_THRESHOLD_C}°C threshold.",
            "action": "Irrigate early morning or evening; avoid midday fieldwork.",
        }

    if (
        pd.notna(rh_max_pct)
        and pd.notna(rainfall_mm)
        and rh_max_pct > HUMID_RH_THRESHOLD_PCT
        and rainfall_mm > HUMID_RAIN_THRESHOLD_MM
    ):
        return {
            **base,
            "icon": "shield-alert",
            "severity": "warning",
            "title": "Fungal disease risk",
            "description": f"High humidity ({rh_max_pct:.0f}%) together with rain favors fungal spread.",
            "action": "Monitor crops closely; consider a preventive fungicide.",
        }

    return None


def register(router_state: dict) -> APIRouter:
    def _forecast_for_gp(gp_name: str) -> pd.DataFrame:
        df = router_state["forecast"]
        rows = df[df["gram_panchayat"] == gp_name]
        if rows.empty:
            available = sorted(df["gram_panchayat"].unique().tolist())
            raise HTTPException(
                status_code=404, detail=f"Unknown Gram Panchayat '{gp_name}'. Available: {available}"
            )
        return rows

    @router.get("/{gp_name}")
    def get_alerts_for_gp(gp_name: str):
        rows = _forecast_for_gp(gp_name)
        alerts = [build_alert(row) for _, row in rows.iterrows()]
        return [a for a in alerts if a is not None]

    @router.get("")
    def get_all_alerts():
        df = router_state["forecast"]
        alerts = [build_alert(row) for _, row in df.iterrows()]
        return [a for a in alerts if a is not None]

    return router
