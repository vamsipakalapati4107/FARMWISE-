"""Phase 0.5: Farm -> Plot -> Crop hierarchy, plus plot-scoped weather/ML/
risk/health/advisory endpoints. See docs/FOUNDATION.md for the full design
rationale (why IDW, why health is a stub, etc.).
"""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from advisory_rules import (
    HEAT_STRESS_THRESHOLD_C,
    HEAVY_RAIN_THRESHOLD_MM,
    HUMID_RAIN_THRESHOLD_MM,
    HUMID_RH_THRESHOLD_PCT,
)
from analytics import (
    SUPPORTED_RANGES,
    available_ranges,
    compute_forecast_risk_for_row,
    compute_rainfall_analytics,
    condition_label,
    generate_insights,
    load_full_history,
    load_historical_weather,
    worst_case_risk,
)
from auth_utils import get_current_user
from crop_advisory_rules import GENERIC_ADVISORY, classify_condition, generate_crop_advisory
from crop_health import (
    build_crop_health,
    build_crop_stress,
    build_explanation,
    build_factors,
    build_health_trend,
)
from db import get_db
from db_models import Alert, Crop, Farm, Plot, User
from farm_advisor import (
    build_action_plan,
    build_crop_condition,
    build_disease_risk,
    build_recommendations,
    build_weather_risk,
    now_iso,
)
from plot_weather import all_forecast_rows, resolve_plot_weather
from routers.alert_center import sync_all_alerts
from routers.alerts import build_alert

router = APIRouter(tags=["plots"])


def _plot_alert_summary(alerts: list[Alert], severity_rank: dict[str, int], severity_emoji: dict[str, str]) -> dict:
    """Phase 5 / Phase 3 map integration: a compact per-plot alert summary
    for map markers (item 12) -- counts by severity plus the single worst
    active alert's emoji, without the frontend needing a second request
    per plot (reuses the same /plots/intelligence single-call design)."""
    counts = {"critical": 0, "warning": 0, "attention": 0, "info": 0}
    for a in alerts:
        counts[a.severity] = counts.get(a.severity, 0) + 1
    worst = max(alerts, key=lambda a: severity_rank.get(a.severity, -1), default=None)
    return {
        "counts": counts,
        "total": len(alerts),
        "top_severity": worst.severity if worst else None,
        "top_emoji": severity_emoji.get(worst.severity) if worst else "\U0001F7E2",
    }


class PlotIn(BaseModel):
    name: str
    latitude: float | None = None
    longitude: float | None = None
    boundary_geojson: str | None = None
    area_value: float | None = None
    area_unit: str = "acre"


class PlotUpdate(BaseModel):
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    boundary_geojson: str | None = None
    area_value: float | None = None
    area_unit: str | None = None


class PlotOut(PlotIn):
    id: str
    farm_id: str

    model_config = ConfigDict(from_attributes=True)


def _get_owned_farm(db: Session, farm_id: str, user: User) -> Farm:
    farm = db.get(Farm, farm_id)
    if farm is None or farm.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    return farm


def _get_owned_plot(db: Session, plot_id: str, user: User) -> Plot:
    plot = db.get(Plot, plot_id)
    if plot is None or plot.farm.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plot not found")
    return plot


@router.get("/farms/{farm_id}/plots", response_model=list[PlotOut])
def list_plots(farm_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    farm = _get_owned_farm(db, farm_id, user)
    return farm.plots


@router.post("/farms/{farm_id}/plots", response_model=PlotOut, status_code=status.HTTP_201_CREATED)
def create_plot(farm_id: str, payload: PlotIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_owned_farm(db, farm_id, user)
    plot = Plot(farm_id=farm_id, **payload.model_dump())
    db.add(plot)
    db.commit()
    db.refresh(plot)
    return plot



# NOTE: GET/PATCH/DELETE /plots/{plot_id} are intentionally defined inside
# register() below, AFTER GET /plots/intelligence -- FastAPI/Starlette
# matches routes in registration order, and /plots/{plot_id} would
# otherwise shadow the literal /plots/intelligence path (matching it with
# plot_id="intelligence") if registered first.


def register(router_state: dict) -> APIRouter:
    def _resolve_plot_weather(plot: Plot, farm: Farm) -> dict:
        return resolve_plot_weather(router_state, plot, farm)

    @router.get("/plots/{plot_id}/weather")
    def get_plot_weather(plot_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        plot = _get_owned_plot(db, plot_id, user)
        farm = plot.farm
        resolved = _resolve_plot_weather(plot, farm)
        row = resolved["current_row"]

        if resolved["rainfall_estimate"] is not None:
            rainfall_field = {
                "value": resolved["rainfall_estimate"]["value"],
                "source": "estimated_downscaled",
                "method": resolved["rainfall_estimate"]["method"],
                "provenance": resolved["rainfall_estimate"]["sources"],
            }
        else:
            rainfall_field = {
                "value": resolved["rainfall_gp_level"],
                "source": "gp_level",
                "method": None,
                "provenance": None,
            }

        def _pass_through(value) -> dict:
            return {"value": value if pd.notna(value) else None, "source": "pass_through"}

        return {
            "plot_id": plot_id,
            "gram_panchayat": farm.gram_panchayat,
            "date": resolved["date"],
            "rainfall_mm": rainfall_field,
            "temp_max_c": _pass_through(row.get("temp_max_c")),
            "temp_min_c": _pass_through(row.get("temp_min_c")),
            "rh_max_pct": _pass_through(row.get("rh_max_pct")),
            "wind_max_kmh": _pass_through(row.get("wind_max_kmh")),
        }

    @router.get("/plots/{plot_id}/ml-predictions")
    def get_plot_ml_predictions(plot_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        plot = _get_owned_plot(db, plot_id, user)
        farm = plot.farm
        resolved = _resolve_plot_weather(plot, farm)
        row = resolved["current_row"]

        return {
            "plot_id": plot_id,
            "date": resolved["date"],
            "predictions": [
                {
                    "variable": "rainfall_mm",
                    "classification": "REAL_ML_PREDICTION",
                    "model": "rainfall_downscaling_model",
                    "gp_level_value": resolved["rainfall_gp_level"],
                    "plot_estimate": resolved["rainfall_estimate"],
                    "note": "GP-level value is the real trained model's output (Random Forest). "
                    "plot_estimate (if present) is a rule-based spatial interpolation over that "
                    "output, not a plot-trained model -- see docs/FOUNDATION.md.",
                },
                {
                    "variable": "temp_max_c",
                    "classification": "PASS_THROUGH_VALUE",
                    "model": None,
                    "gp_level_value": row.get("temp_max_c"),
                    "plot_estimate": None,
                    "note": "No trained model exists for temperature. This is the raw block "
                    "forecast value, identical across all GPs.",
                },
                {
                    "variable": "temp_min_c",
                    "classification": "PASS_THROUGH_VALUE",
                    "model": None,
                    "gp_level_value": row.get("temp_min_c"),
                    "plot_estimate": None,
                    "note": "No trained model exists for temperature. This is the raw block "
                    "forecast value, identical across all GPs.",
                },
                {
                    "variable": "rh_max_pct",
                    "classification": "PASS_THROUGH_VALUE",
                    "model": None,
                    "gp_level_value": row.get("rh_max_pct"),
                    "plot_estimate": None,
                    "note": "No trained model exists for humidity. This is the raw block "
                    "forecast value, identical across all GPs.",
                },
                {
                    "variable": "wind_max_kmh",
                    "classification": "PASS_THROUGH_VALUE",
                    "model": None,
                    "gp_level_value": row.get("wind_max_kmh"),
                    "plot_estimate": None,
                    "note": "No trained model exists for wind. This is the raw block "
                    "forecast value, identical across all GPs.",
                },
            ],
        }

    @router.get("/plots/{plot_id}/risk")
    def get_plot_risk(plot_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        plot = _get_owned_plot(db, plot_id, user)
        farm = plot.farm
        resolved = _resolve_plot_weather(plot, farm)
        row = resolved["current_row"].copy()

        rainfall_source = "gp_level"
        if resolved["rainfall_estimate"] is not None:
            row["rainfall_mm"] = resolved["rainfall_estimate"]["value"]
            rainfall_source = "estimated_downscaled"

        alert = build_alert(row)
        return {
            "plot_id": plot_id,
            "date": resolved["date"],
            "rainfall_source": rainfall_source,
            "alert": alert,  # None if no significant risk today
        }

    @router.get("/plots/{plot_id}/health")
    def get_plot_health(plot_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        _get_owned_plot(db, plot_id, user)
        # Honest stub: no satellite/NDVI/crop-health model exists yet.
        # Returning available=false rather than a fabricated score.
        return {
            "plot_id": plot_id,
            "available": False,
            "classification": "NOT_AVAILABLE",
            "reason": "No crop health / satellite imagery model is implemented yet.",
        }

    @router.get("/plots/{plot_id}/advisory")
    def get_plot_advisory(plot_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        plot = _get_owned_plot(db, plot_id, user)
        farm = plot.farm
        resolved = _resolve_plot_weather(plot, farm)
        row = resolved["current_row"].copy()

        rainfall_source = "gp_level"
        if resolved["rainfall_estimate"] is not None:
            row["rainfall_mm"] = resolved["rainfall_estimate"]["value"]
            rainfall_source = "estimated_downscaled"

        linked_crop = next((c for c in plot.crops), None)
        if linked_crop is not None:
            advisory = generate_crop_advisory(row, linked_crop.crop_name, linked_crop.stage)
        else:
            condition = classify_condition(row)
            advisory = {**GENERIC_ADVISORY[condition], "condition": condition, "crop_name": None, "stage": None}

        return {
            "plot_id": plot_id,
            "date": resolved["date"],
            "rainfall_source": rainfall_source,
            **advisory,
        }

    @router.get("/plots/{plot_id}/farm-advisor")
    def get_farm_advisor(plot_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        """Phase 1: AI Farm Advisor. Combines the plot's real weather data,
        the rainfall ML model's output (via _resolve_plot_weather, unchanged
        from Phase 0.5), and the rule-based recommendation engine in
        src/farm_advisor.py. Every value is traceable to its actual source
        -- see the `technical_details` block."""
        plot = _get_owned_plot(db, plot_id, user)
        farm = plot.farm
        resolved = _resolve_plot_weather(plot, farm)
        row = resolved["current_row"]

        rainfall_mm = resolved["rainfall_estimate"]["value"] if resolved["rainfall_estimate"] else resolved["rainfall_gp_level"]
        rainfall_source = "estimated_downscaled" if resolved["rainfall_estimate"] else "gp_level"
        temp_max_c = row.get("temp_max_c")
        temp_min_c = row.get("temp_min_c")
        rh_max_pct = row.get("rh_max_pct")
        wind_max_kmh = row.get("wind_max_kmh")

        linked_crop = next((c for c in plot.crops), None)
        crop_name = linked_crop.crop_name if linked_crop else None
        stage = linked_crop.stage if linked_crop else None

        recommendations = build_recommendations(rainfall_mm, temp_max_c, rh_max_pct, crop_name, stage)
        action_plan = build_action_plan(recommendations)
        disease_risk = build_disease_risk(rh_max_pct, rainfall_mm)
        weather_risk = build_weather_risk(temp_max_c, rainfall_mm)
        crop_condition = build_crop_condition(crop_name, stage)

        rules_triggered = []
        if not pd.isna(rainfall_mm) and rainfall_mm is not None and rainfall_mm > HEAVY_RAIN_THRESHOLD_MM:
            rules_triggered.append(f"heavy_rain_threshold_exceeded (>{HEAVY_RAIN_THRESHOLD_MM}mm)")
        if temp_max_c is not None and not pd.isna(temp_max_c) and temp_max_c > HEAT_STRESS_THRESHOLD_C:
            rules_triggered.append(f"heat_stress_threshold_exceeded (>{HEAT_STRESS_THRESHOLD_C}°C)")
        if (
            rh_max_pct is not None
            and not pd.isna(rh_max_pct)
            and rainfall_mm is not None
            and not pd.isna(rainfall_mm)
            and rh_max_pct > HUMID_RH_THRESHOLD_PCT
            and rainfall_mm > HUMID_RAIN_THRESHOLD_MM
        ):
            rules_triggered.append(
                f"fungal_risk_threshold_exceeded (rh>{HUMID_RH_THRESHOLD_PCT}% and rain>{HUMID_RAIN_THRESHOLD_MM}mm)"
            )
        for rec in recommendations:
            if "crop_stage_rule" in rec["data_sources"]:
                rules_triggered.append(f"crop_stage_override:{crop_name}:{stage}:{rec['category']}")

        return {
            "plot_id": plot_id,
            "date": resolved["date"],
            "crop": {"crop_name": crop_name, "variety": linked_crop.variety, "stage": stage} if linked_crop else None,
            "disease_risk": disease_risk,
            "weather_risk": weather_risk,
            "crop_condition": crop_condition,
            "recommendations": recommendations,
            "action_plan": action_plan,
            "technical_details": {
                "data_used": {
                    "rainfall_mm": {"value": rainfall_mm, "source": rainfall_source},
                    "temp_max_c": {"value": temp_max_c, "source": "pass_through"},
                    "temp_min_c": {"value": temp_min_c, "source": "pass_through"},
                    "rh_max_pct": {"value": rh_max_pct, "source": "pass_through"},
                    "wind_max_kmh": {"value": wind_max_kmh, "source": "pass_through"},
                },
                "ml_prediction_used": {
                    "variable": "rainfall_mm",
                    "model_name": "rainfall_downscaling_model (Random Forest)",
                    "classification": "REAL_ML_PREDICTION",
                    "gp_level_value": resolved["rainfall_gp_level"],
                },
                "spatial_estimation_used": resolved["rainfall_estimate"],
                "rules_triggered": rules_triggered,
                "timestamp": now_iso(),
            },
        }

    @router.get("/plots/intelligence")
    def get_plots_intelligence(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        """Phase 3: Farm Intelligence Map data, in one call (avoids N
        per-plot round-trips from the frontend). Loops over the user's
        plots and reuses the exact same Phase 1/2 functions each plot's own
        detail page uses -- no duplicated health/disease/advisory logic."""
        plots = db.query(Plot).join(Farm).filter(Farm.owner_id == user.id).all()

        # Phase 5: sync once (not per-plot -- it already loops every plot
        # itself), then attach each plot's active-alert summary below. Reuses
        # the same alert engine/sync as the Alert Center, not a second one.
        sync_all_alerts(router_state, db, user)
        active_alerts = db.query(Alert).filter(Alert.user_id == user.id, Alert.status.in_(["new", "read"])).all()
        alerts_by_plot: dict[str, list[Alert]] = {}
        for a in active_alerts:
            if a.plot_id:
                alerts_by_plot.setdefault(a.plot_id, []).append(a)
        severity_rank = {"critical": 3, "warning": 2, "attention": 1, "info": 0}
        severity_emoji = {"critical": "\U0001F534", "warning": "\U0001F7E0", "attention": "\U0001F7E1", "info": "\U0001F7E2"}

        results = []
        for plot in plots:
            farm = plot.farm
            resolved = _resolve_plot_weather(plot, farm)
            row = resolved["current_row"]

            rainfall_mm = resolved["rainfall_estimate"]["value"] if resolved["rainfall_estimate"] else resolved["rainfall_gp_level"]
            rainfall_source = "estimated_downscaled" if resolved["rainfall_estimate"] else "gp_level"
            temp_max_c = row.get("temp_max_c")
            rh_max_pct = row.get("rh_max_pct")

            linked_crop = next((c for c in plot.crops), None)
            crop_name = linked_crop.crop_name if linked_crop else None
            stage = linked_crop.stage if linked_crop else None

            disease_risk = build_disease_risk(rh_max_pct, rainfall_mm)
            weather_risk = build_weather_risk(temp_max_c, rainfall_mm)
            health = build_crop_health(disease_risk, weather_risk)
            factors = build_factors(rainfall_mm, rainfall_source, temp_max_c, rh_max_pct, disease_risk, weather_risk, stage)
            recommendations = build_recommendations(rainfall_mm, temp_max_c, rh_max_pct, crop_name, stage)
            action_plan = build_action_plan(recommendations)
            factor_by_key = {f["key"]: f for f in factors}

            results.append(
                {
                    "plot_id": plot.id,
                    "plot_name": plot.name,
                    "farm_id": farm.id,
                    "farm_name": farm.name,
                    "latitude": plot.latitude,
                    "longitude": plot.longitude,
                    "location_configured": plot.latitude is not None and plot.longitude is not None,
                    "area_value": plot.area_value,
                    "area_unit": plot.area_unit,
                    "crop": {"crop_name": crop_name, "variety": linked_crop.variety, "stage": stage}
                    if linked_crop
                    else None,
                    "date": resolved["date"],
                    "health": health,
                    "disease_risk": disease_risk,
                    "weather_risk": weather_risk,
                    "weather": {
                        "temp_max_c": {"value": temp_max_c, "status": factor_by_key["temperature"]["status"], "source": "pass_through"},
                        "rh_max_pct": {"value": rh_max_pct, "status": factor_by_key["humidity"]["status"], "source": "pass_through"},
                        "rainfall_mm": {"value": rainfall_mm, "status": factor_by_key["rainfall"]["status"], "source": rainfall_source},
                    },
                    "top_recommendation": action_plan[0]["label"] if action_plan else None,
                    "active_alerts": _plot_alert_summary(alerts_by_plot.get(plot.id, []), severity_rank, severity_emoji),
                    "sources": {
                        "weather": "pass_through (temp/humidity), ml_prediction or spatial_estimation (rainfall)",
                        "health": health["source_type"],
                        "disease_risk": "derived_assessment" if disease_risk["available"] else "unavailable",
                        "spatial_estimation_used": resolved["rainfall_estimate"] is not None,
                        "resolution": (
                            "Plot-level estimate derived from available spatial data (IDW over nearest GPs)."
                            if resolved["rainfall_estimate"] is not None
                            else "Gram Panchayat-level (21 fixed points) -- not measured at this plot's exact coordinates."
                        ),
                    },
                }
            )

        return results

    @router.get("/plots/{plot_id}", response_model=PlotOut)
    def get_plot(plot_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        return _get_owned_plot(db, plot_id, user)

    @router.patch("/plots/{plot_id}", response_model=PlotOut)
    def update_plot(
        plot_id: str, payload: PlotUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ):
        plot = _get_owned_plot(db, plot_id, user)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(plot, field, value)
        db.commit()
        db.refresh(plot)
        return plot

    @router.delete("/plots/{plot_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_plot(plot_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        plot = _get_owned_plot(db, plot_id, user)
        db.delete(plot)
        db.commit()

    @router.get("/plots/{plot_id}/crop-health")
    def get_crop_health(plot_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        """Phase 2: Crop Health & Stress Intelligence. No trained health/stress
        model exists (src/ml_audit.py) -- this reuses Phase 1's disease/weather
        risk functions (no duplicated advisory logic) and never fabricates a
        score, probability, or historical trend. See src/crop_health.py.

        Distinct from the Phase 0.5 GET /plots/{plot_id}/health stub, which is
        left untouched -- this is a new, additive endpoint."""
        plot = _get_owned_plot(db, plot_id, user)
        farm = plot.farm
        resolved = _resolve_plot_weather(plot, farm)
        row = resolved["current_row"]

        rainfall_mm = resolved["rainfall_estimate"]["value"] if resolved["rainfall_estimate"] else resolved["rainfall_gp_level"]
        rainfall_source = "estimated_downscaled" if resolved["rainfall_estimate"] else "gp_level"
        temp_max_c = row.get("temp_max_c")
        rh_max_pct = row.get("rh_max_pct")

        linked_crop = next((c for c in plot.crops), None)
        crop_name = linked_crop.crop_name if linked_crop else None
        stage = linked_crop.stage if linked_crop else None

        disease_risk = build_disease_risk(rh_max_pct, rainfall_mm)
        weather_risk = build_weather_risk(temp_max_c, rainfall_mm)
        health = build_crop_health(disease_risk, weather_risk)
        stress = build_crop_stress()
        factors = build_factors(rainfall_mm, rainfall_source, temp_max_c, rh_max_pct, disease_risk, weather_risk, stage)
        explanation = build_explanation()
        health_trend = build_health_trend()

        # Phase 1 integration: surface the advisor's disease risk + top
        # action without recomputing or duplicating its logic.
        recommendations = build_recommendations(rainfall_mm, temp_max_c, rh_max_pct, crop_name, stage)
        action_plan = build_action_plan(recommendations)

        return {
            "plot_id": plot_id,
            "date": resolved["date"],
            "crop": {"crop_name": crop_name, "stage": stage} if linked_crop else None,
            "health": health,
            "stress": stress,
            "factors": factors,
            "explanation": explanation,
            "health_trend": health_trend,
            "advisor_summary": {
                "disease_risk_level": disease_risk["level"],
                "top_recommendation": action_plan[0]["label"] if action_plan else None,
            },
            "technical_details": {
                "model": None,
                "source": health["source_type"],
                "features_used": [f["key"] for f in factors if f["available"]],
                "timestamp": now_iso(),
            },
        }

    def _all_forecast_rows(gp_name: str) -> list[dict]:
        return all_forecast_rows(router_state, gp_name)

    @router.get("/plots/{plot_id}/analytics")
    def get_plot_analytics(
        plot_id: str,
        range_days: int = 30,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        """Phase 4: Historical + Forecast Analytics. Reuses Phase 1/2/3
        functions (build_disease_risk, build_weather_risk, build_recommendations,
        build_action_plan) rather than re-deriving them -- see src/analytics.py
        for why historical data may not end "today", and why disease/health
        history is always reported unavailable (nothing is ever logged over
        time in this project)."""
        if range_days not in SUPPORTED_RANGES:
            raise HTTPException(status_code=422, detail=f"range must be one of {SUPPORTED_RANGES}")

        plot = _get_owned_plot(db, plot_id, user)
        farm = plot.farm
        resolved = _resolve_plot_weather(plot, farm)
        current_row = resolved["current_row"]

        linked_crop = next((c for c in plot.crops), None)
        crop_name = linked_crop.crop_name if linked_crop else None
        stage = linked_crop.stage if linked_crop else None

        # -- Historical (real ERA5-Land observations, see analytics.py) --
        full_history_df = load_full_history(farm.gram_panchayat)
        ranges = available_ranges(len(full_history_df) if full_history_df is not None else 0)
        historical = load_historical_weather(farm.gram_panchayat, range_days)
        rainfall_analytics = compute_rainfall_analytics(historical, full_history_df)

        # -- Forecast (real 5-day block forecast, unchanged from Phase 0.5) --
        forecast_rows = _all_forecast_rows(farm.gram_panchayat)
        forecast = [
            {
                "date": row["date"],
                "temp_max_c": row.get("temp_max_c"),
                "temp_min_c": row.get("temp_min_c"),
                "rh_max_pct": row.get("rh_max_pct"),
                "rainfall_mm": row.get("rainfall_mm"),
                "wind_max_kmh": row.get("wind_max_kmh"),
                "condition": condition_label(row.get("rainfall_mm")),
            }
            for row in forecast_rows
        ]
        daily_risks = [compute_forecast_risk_for_row(row) for row in forecast_rows]
        forecast_risk = worst_case_risk(daily_risks) if daily_risks else None

        # -- Disease/health history: never fabricated, always unavailable --
        # (nothing is logged over time anywhere in this project yet).
        disease_history = {
            "available": False,
            "reason": "Historical disease-risk observations are not yet available.",
        }
        health_history = {
            "available": False,
            "reason": "No historical crop-health observations available yet.",
        }

        # -- Reuse Phase 1's engine for the current snapshot + insights --
        rainfall_mm = resolved["rainfall_estimate"]["value"] if resolved["rainfall_estimate"] else resolved["rainfall_gp_level"]
        temp_max_c = current_row.get("temp_max_c")
        rh_max_pct = current_row.get("rh_max_pct")
        disease_risk = build_disease_risk(rh_max_pct, rainfall_mm)
        weather_risk = build_weather_risk(temp_max_c, rainfall_mm)
        recommendations = build_recommendations(rainfall_mm, temp_max_c, rh_max_pct, crop_name, stage)
        action_plan = build_action_plan(recommendations)

        insights = generate_insights(historical, forecast, rh_max_pct, disease_risk)

        return {
            "plot_id": plot_id,
            "date": resolved["date"],
            "crop": {"crop_name": crop_name, "stage": stage} if linked_crop else None,
            "requested_range_days": range_days,
            "available_ranges": ranges,
            "historical": historical,
            "rainfall_analytics": rainfall_analytics,
            "forecast": forecast,
            "forecast_risk": forecast_risk,
            "disease_history": disease_history,
            "health_history": health_history,
            "insights": insights,
            "advisor_summary": {
                "disease_risk_level": disease_risk["level"],
                "weather_risk_level": weather_risk["level"],
                "top_recommendation": action_plan[0]["label"] if action_plan else None,
            },
            "data_sources": {
                "historical_weather": "Weather observation (ERA5-Land reanalysis)" if historical["available"] else "Unavailable",
                "forecast": "Weather forecast (block-level, downscaled for rainfall)",
                "rainfall_ml": "ML model (Random Forest, GP-level)"
                + (" + spatial estimate" if resolved["rainfall_estimate"] else ""),
                "disease_risk": "Derived assessment (rule-based)",
                "weather_risk": "Derived assessment (rule-based)",
                "wind_risk": "Unavailable (no established threshold)",
            },
            "timestamp": now_iso(),
        }

    return router
