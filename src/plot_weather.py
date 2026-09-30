"""Shared plot-weather resolution, used by src/routers/plots.py and (from
Phase 5) src/routers/alert_center.py. Extracted out of plots.py's
register() closure so the SAME resolution logic is reused rather than
duplicated by the alert engine -- these were previously closures capturing
`router_state`; now `router_state` is an explicit parameter so any router
can call them.

No behavior change from the original closures -- see Phase 0.5/1's
docstrings, preserved below.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
from fastapi import HTTPException

from db_models import Farm, Plot
from spatial import idw_estimate


def pick_current_row(router_state: dict, gp_name: str) -> dict:
    df = router_state["forecast"]
    rows = df[df["gram_panchayat"] == gp_name]
    if rows.empty:
        raise HTTPException(status_code=422, detail=f"No forecast data for Gram Panchayat '{gp_name}'")
    today = dt.date.today().isoformat()
    dates = rows["date"].tolist()
    if today in dates:
        row = rows[rows["date"] == today].iloc[0]
    else:
        future = [d for d in dates if d > today]
        row = rows[rows["date"] == (min(future) if future else max(dates))].iloc[0]
    # `.to_dict()` (not just `.astype(object)`) is what actually unboxes
    # numpy scalars (int64/float64) into native Python int/float -- a row
    # sliced from a mixed-dtype DataFrame is already `object`-dtype, so
    # `.astype(object)` alone is a no-op and leaves numpy scalars behind,
    # which FastAPI's JSON encoder then can't serialize.
    return row.astype(object).where(pd.notna(row), None).to_dict()


def rainfall_gp_values(router_state: dict, date: str) -> dict[str, tuple[float, float, float]]:
    """{gp_name: (lat, lon, rainfall_mm)} for every GP on the given date --
    the real ML model's raw GP-level output, used as IDW input."""
    forecast_df = router_state["forecast"]
    centroids_df = router_state["centroids"]
    day_rows = forecast_df[forecast_df["date"] == date]
    centroid_lookup = {
        row["gram_panchayat"]: (row["latitude"], row["longitude"]) for _, row in centroids_df.iterrows()
    }

    result = {}
    for _, row in day_rows.iterrows():
        gp = row["gram_panchayat"]
        if gp in centroid_lookup and pd.notna(row.get("rainfall_mm")):
            lat, lon = centroid_lookup[gp]
            result[gp] = (lat, lon, float(row["rainfall_mm"]))
    return result


def resolve_plot_weather(router_state: dict, plot: Plot, farm: Farm) -> dict:
    """Single source of truth for every plot-scoped endpoint that needs
    today's weather: resolves the GP-level row for the farm's Gram
    Panchayat, plus (if the plot has coordinates) an IDW-estimated rainfall
    value. Never applies IDW to temp/RH/wind -- those are identical
    block-level pass-through values across every GP, so "interpolating"
    them would misleadingly imply spatial variation that doesn't exist.
    """
    current_row = pick_current_row(router_state, farm.gram_panchayat)
    date = current_row["date"]

    rainfall_gp_level = current_row.get("rainfall_mm")
    rainfall_estimate = None
    if plot.latitude is not None and plot.longitude is not None:
        gp_values = rainfall_gp_values(router_state, date)
        rainfall_estimate = idw_estimate(plot.latitude, plot.longitude, gp_values)

    return {
        "date": date,
        "current_row": current_row,
        "rainfall_gp_level": rainfall_gp_level,
        "rainfall_estimate": rainfall_estimate,
    }


def all_forecast_rows(router_state: dict, gp_name: str) -> list[dict]:
    df = router_state["forecast"]
    rows = df[df["gram_panchayat"] == gp_name].sort_values("date")
    return [r.astype(object).where(pd.notna(r), None).to_dict() for _, r in rows.iterrows()]
