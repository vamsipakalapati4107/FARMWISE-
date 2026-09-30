"""Phase 12: crop-stage-aware advisory endpoint, combining a user's Farm +
Crop records (Phase 8) with the real per-GP forecast and the crop-aware
rules in src/crop_advisory_rules.py.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth_utils import get_current_user
from crop_advisory_rules import generate_crop_advisory
from db import get_db
from db_models import Farm, User

router = APIRouter(tags=["crop-advisory"])


def _pick_current_row(rows: pd.DataFrame) -> pd.Series:
    """Mirrors src/routers/weather.py's _pick_current_row exactly."""
    today = dt.date.today().isoformat()
    dates = rows["date"].tolist()

    if today in dates:
        return rows[rows["date"] == today].iloc[0]

    future = [d for d in dates if d > today]
    if future:
        return rows[rows["date"] == min(future)].iloc[0]

    return rows[rows["date"] == max(dates)].iloc[0]


def register(router_state: dict) -> APIRouter:
    @router.get("/farms/{farm_id}/crop-advisory")
    def get_crop_advisory(farm_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        farm = db.get(Farm, farm_id)
        if farm is None or farm.owner_id != user.id:
            raise HTTPException(status_code=404, detail="Farm not found")

        forecast_df = router_state["forecast"]
        gp_rows = forecast_df[forecast_df["gram_panchayat"] == farm.gram_panchayat]
        if gp_rows.empty:
            raise HTTPException(
                status_code=422, detail=f"No forecast data for Gram Panchayat '{farm.gram_panchayat}'"
            )
        current_row = _pick_current_row(gp_rows)

        results = []
        for crop in farm.crops:
            advisory = generate_crop_advisory(current_row, crop.crop_name, crop.stage)
            results.append({"crop_id": crop.id, "date": current_row["date"], **advisory})
        return results

    return router
