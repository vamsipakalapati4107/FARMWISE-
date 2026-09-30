"""Phase 5: REST API serving GP-level forecasts + advisories to the
dashboard (frontend/index.html) or any other client.

Run from the project root:
    uvicorn src.api:app --reload
"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from db import init_db
from routers import alert_center as alert_center_router
from routers import alerts as alerts_router
from routers import auth as auth_router
from routers import crop_advisory as crop_advisory_router
from routers import crops as crops_router
from routers import farm_management as farm_management_router
from routers import farms as farms_router
from routers import locations as locations_router
from routers import ml as ml_router
from routers import notifications as notifications_router
from routers import plots as plots_router
from routers import weather as weather_router

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
FORECAST_FILE = PROCESSED_DIR / "gp_forecast_with_advisory.csv"
CENTROIDS_FILE = PROCESSED_DIR / "gp_centroids.csv"

state: dict[str, pd.DataFrame] = {}


def _records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> list of JSON-safe dicts (NaN becomes null, not the
    invalid `NaN` token that pandas/stdlib json would otherwise emit)."""
    return df.astype(object).where(pd.notna(df), None).to_dict(orient="records")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not FORECAST_FILE.exists():
        raise RuntimeError(f"Missing {FORECAST_FILE}. Run Phases 1-4 first.")
    if not CENTROIDS_FILE.exists():
        raise RuntimeError(f"Missing {CENTROIDS_FILE}. Run src/fetch_ground_truth.py first.")

    state["forecast"] = pd.read_csv(FORECAST_FILE)
    state["centroids"] = pd.read_csv(CENTROIDS_FILE)
    print(
        f"Loaded {len(state['forecast'])} forecast rows and "
        f"{len(state['centroids'])} GP centroids."
    )
    init_db()
    yield
    state.clear()


app = FastAPI(title="Panchayat Downscaling API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(locations_router.router)
app.include_router(farms_router.router)
app.include_router(crops_router.router)
app.include_router(farm_management_router.router)
app.include_router(weather_router.register(state))
app.include_router(alerts_router.register(state))
app.include_router(crop_advisory_router.register(state))
app.include_router(notifications_router.register(state))
# plots_router.router already carries the CRUD routes (decorated at module
# import time); register(state) adds the weather/ml/risk/health/advisory
# routes onto that same router object and returns it -- include once.
app.include_router(plots_router.register(state))
app.include_router(ml_router.router)
app.include_router(alert_center_router.register(state))


@app.get("/gps")
def get_gps():
    df = state["centroids"][["gram_panchayat", "latitude", "longitude"]]
    return _records(df)


@app.get("/forecast")
def get_forecast():
    return _records(state["forecast"])


@app.get("/forecast/{gp_name}")
def get_forecast_for_gp(gp_name: str):
    df = state["forecast"]
    rows = df[df["gram_panchayat"] == gp_name]
    if rows.empty:
        available = sorted(df["gram_panchayat"].unique().tolist())
        raise HTTPException(
            status_code=404,
            detail=f"Unknown Gram Panchayat '{gp_name}'. Available: {available}",
        )
    return _records(rows)
