"""Phase 11: current-weather + estimated-hourly endpoints, wrapping the
real gp_forecast_with_advisory.csv (no new data sources -- see api.py's
existing lifespan-loaded `state["forecast"]`).
"""
from __future__ import annotations

import datetime as dt
import math

import pandas as pd
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/weather", tags=["weather"])


def _forecast_for_gp(state: dict, gp_name: str) -> pd.DataFrame:
    df = state["forecast"]
    rows = df[df["gram_panchayat"] == gp_name].sort_values("date")
    if rows.empty:
        available = sorted(df["gram_panchayat"].unique().tolist())
        raise HTTPException(status_code=404, detail=f"Unknown Gram Panchayat '{gp_name}'. Available: {available}")
    return rows


def _pick_current_row(rows: pd.DataFrame) -> pd.Series:
    """The forecast file covers a fixed 5-day window. "Current" is today's
    row if today falls in that window; otherwise the nearest available day
    (future if the window hasn't started yet, else the most recent past
    day) -- never an invented value."""
    today = dt.date.today().isoformat()
    dates = rows["date"].tolist()

    if today in dates:
        return rows[rows["date"] == today].iloc[0]

    future = [d for d in dates if d > today]
    if future:
        return rows[rows["date"] == min(future)].iloc[0]

    return rows[rows["date"] == max(dates)].iloc[0]


def _record(row: pd.Series) -> dict:
    return row.astype(object).where(pd.notna(row), None).to_dict()


def register(router_state: dict) -> APIRouter:
    """The router needs access to api.py's `state` dict (populated at
    lifespan startup), so it's built via a factory instead of importing a
    module-level global -- avoids import-order coupling to api.py."""

    @router.get("/current/{gp_name}")
    def get_current_weather(gp_name: str):
        rows = _forecast_for_gp(router_state, gp_name)
        return _record(_pick_current_row(rows))

    @router.get("/hourly-estimated/{gp_name}")
    def get_hourly_estimated(gp_name: str, date: str | None = None):
        rows = _forecast_for_gp(router_state, gp_name)
        if date is not None:
            matching = rows[rows["date"] == date]
            if matching.empty:
                available = sorted(rows["date"].tolist())
                raise HTTPException(status_code=404, detail=f"No forecast row for '{gp_name}' on {date}. Available: {available}")
            current = matching.iloc[0]
        else:
            current = _pick_current_row(rows)
        temp_min, temp_max = current.get("temp_min_c"), current.get("temp_max_c")
        if pd.isna(temp_min) or pd.isna(temp_max):
            raise HTTPException(status_code=422, detail=f"No temperature range available for '{gp_name}'")

        mid = (temp_min + temp_max) / 2
        amplitude = (temp_max - temp_min) / 2
        points = []
        for hour in range(24):
            # Peak at 15:00, trough at 03:00 -- same diurnal model as the
            # frontend's previous client-side estimate (lib/weather.ts),
            # now server-side as the single source of truth.
            angle = ((hour - 15) / 24) * 2 * math.pi
            temp_c = round((mid + amplitude * math.cos(angle)) * 10) / 10
            points.append({"hour": hour, "temp_c": temp_c, "estimated": True})

        return {
            "gram_panchayat": gp_name,
            "date": current["date"],
            "points": points,
        }

    return router
