"""Phase 5: Smart Alerts & Early Warning System.

Named `/alert-center` (not the bare `/alerts` the spec's example suggests)
because `GET /alerts` and `GET /alerts/{gp_name}` already exist from Phase
11 (public, GP-scoped weather alerts, no auth) -- reusing that exact path
for this new, authenticated, farm/plot-scoped concept would either break
FastAPI's route matching or silently shadow one of the two. Farm-scoped and
plot-scoped alert routes don't collide with anything, so they keep the
natural `/alerts` suffix.

Alerts are generated lazily (same pattern as notifications.py): every read
re-syncs the calling user's alerts from their plots' real current data,
using src/alert_engine.py (itself reusing Phase 1/2/4 functions -- no
second recommendation engine). Deduplication is enforced by a unique
`dedupe_key` column; expiry is swept on every read.
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from alert_engine import generate_candidate_alerts
from auth_utils import get_current_user
from crop_health import build_crop_health
from db import get_db
from db_models import Alert, Farm, HealthSnapshot, Plot, User
from farm_advisor import build_disease_risk, build_recommendations, build_weather_risk
from plot_weather import all_forecast_rows, resolve_plot_weather
from sms_service import alert_sms_status, send_sms_for_alert

router = APIRouter(tags=["alerts"])


def _alert_to_dict(a: Alert, user: User, db: Session) -> dict:
    linked_crop = next((c for c in a.plot.crops), None) if a.plot else None
    return {
        "id": a.id,
        "farm_id": a.farm_id,
        "farm_name": a.farm.name,
        "plot_id": a.plot_id,
        "plot_name": a.plot.name if a.plot else None,
        "crop_name": linked_crop.crop_name if linked_crop else None,
        "alert_type": a.alert_type,
        "severity": a.severity,
        "title": a.title,
        "condition": a.condition,
        "reason": a.reason,
        "recommended_action": a.recommended_action,
        "source": a.source,
        "status": a.status,
        "valid_until": a.valid_until.isoformat() if a.valid_until else None,
        "created_at": a.created_at.isoformat(),
        "sms": alert_sms_status(a.id, a.severity, a.alert_type, user, db),
    }


def sync_all_alerts(router_state: dict, db: Session, user: User) -> None:
    """Module-level (not closure-nested) so other routers -- e.g.
    plots.py's /plots/intelligence, for Phase 3 map integration -- can
    reuse the exact same sync instead of re-deriving alert state."""
    today = dt.date.today()

    farms = db.query(Farm).filter(Farm.owner_id == user.id).all()
    for farm in farms:
        for plot in farm.plots:
            resolved = resolve_plot_weather(router_state, plot, farm)
            forecast_rows = all_forecast_rows(router_state, farm.gram_panchayat)
            row = resolved["current_row"]

            rainfall_mm = (
                resolved["rainfall_estimate"]["value"] if resolved["rainfall_estimate"] else resolved["rainfall_gp_level"]
            )
            temp_max_c = row.get("temp_max_c")
            rh_max_pct = row.get("rh_max_pct")

            linked_crop = next((c for c in plot.crops), None)
            crop_name = linked_crop.crop_name if linked_crop else None
            stage = linked_crop.stage if linked_crop else None

            disease_risk = build_disease_risk(rh_max_pct, rainfall_mm)
            weather_risk = build_weather_risk(temp_max_c, rainfall_mm)
            health = build_crop_health(disease_risk, weather_risk)
            recommendations = build_recommendations(rainfall_mm, temp_max_c, rh_max_pct, crop_name, stage)

            # -- Real health snapshot logging (never backfilled) --
            previous_status = None
            if health["available"]:
                existing_today = (
                    db.query(HealthSnapshot)
                    .filter(HealthSnapshot.plot_id == plot.id, HealthSnapshot.date == resolved["date"])
                    .first()
                )
                if existing_today is None:
                    prior = (
                        db.query(HealthSnapshot)
                        .filter(HealthSnapshot.plot_id == plot.id)
                        .order_by(HealthSnapshot.date.desc())
                        .first()
                    )
                    previous_status = prior.status if prior else None
                    db.add(HealthSnapshot(plot_id=plot.id, date=resolved["date"], status=health["status"]))
                else:
                    prior = (
                        db.query(HealthSnapshot)
                        .filter(HealthSnapshot.plot_id == plot.id, HealthSnapshot.date < resolved["date"])
                        .order_by(HealthSnapshot.date.desc())
                        .first()
                    )
                    previous_status = prior.status if prior else None

            candidates = generate_candidate_alerts(
                farm_id=farm.id,
                plot_id=plot.id,
                today_date=resolved["date"],
                forecast_rows=forecast_rows,
                disease_risk=disease_risk,
                recommendations=recommendations,
                previous_health_status=previous_status,
                current_health_status=health["status"] if health["available"] else None,
            )

            for candidate in candidates:
                exists = db.query(Alert).filter(Alert.dedupe_key == candidate["dedupe_key"]).first()
                if exists:
                    continue
                valid_until = dt.date.fromisoformat(candidate["valid_until"]) if candidate.get("valid_until") else None
                new_alert = Alert(
                    user_id=user.id,
                    farm_id=farm.id,
                    plot_id=plot.id,
                    alert_type=candidate["alert_type"],
                    severity=candidate["severity"],
                    title=candidate["title"],
                    condition=candidate["condition"],
                    reason=candidate["reason"],
                    recommended_action=candidate["recommended_action"],
                    source=candidate["source"],
                    status="new",
                    dedupe_key=candidate["dedupe_key"],
                    valid_until=valid_until,
                )
                db.add(new_alert)
                # Flush so new_alert.id exists (SmsMessage.alert_id needs a
                # real, committed-order id) before deciding whether to text
                # the farmer about this brand-new (never-before-seen) alert.
                db.flush()
                send_sms_for_alert(candidate, new_alert.id, user, db)

    # -- Expiry sweep: a forecast-based alert automatically expires once
    # the date it concerned has passed, unless already resolved. --
    db.query(Alert).filter(
        Alert.user_id == user.id,
        Alert.status.in_(["new", "read"]),
        Alert.valid_until.is_not(None),
        Alert.valid_until < today,
    ).update({"status": "expired"}, synchronize_session=False)

    db.commit()


def register(router_state: dict) -> APIRouter:
    def _get_owned_alert(db: Session, alert_id: str, user: User) -> Alert:
        alert = db.get(Alert, alert_id)
        if alert is None or alert.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        return alert

    @router.get("/alert-center")
    def list_all_alerts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        sync_all_alerts(router_state, db, user)
        alerts = db.query(Alert).filter(Alert.user_id == user.id).order_by(Alert.created_at.desc()).all()
        return [_alert_to_dict(a, user, db) for a in alerts]

    @router.get("/farms/{farm_id}/alerts")
    def list_farm_alerts(farm_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        farm = db.get(Farm, farm_id)
        if farm is None or farm.owner_id != user.id:
            raise HTTPException(status_code=404, detail="Farm not found")
        sync_all_alerts(router_state, db, user)
        alerts = (
            db.query(Alert)
            .filter(Alert.user_id == user.id, Alert.farm_id == farm_id)
            .order_by(Alert.created_at.desc())
            .all()
        )
        return [_alert_to_dict(a, user, db) for a in alerts]

    @router.get("/plots/{plot_id}/alerts")
    def list_plot_alerts(plot_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        plot = db.get(Plot, plot_id)
        if plot is None or plot.farm.owner_id != user.id:
            raise HTTPException(status_code=404, detail="Plot not found")
        sync_all_alerts(router_state, db, user)
        alerts = (
            db.query(Alert)
            .filter(Alert.user_id == user.id, Alert.plot_id == plot_id)
            .order_by(Alert.created_at.desc())
            .all()
        )
        return [_alert_to_dict(a, user, db) for a in alerts]

    @router.patch("/alerts/{alert_id}/read")
    def mark_alert_read(alert_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        alert = _get_owned_alert(db, alert_id, user)
        if alert.status == "new":
            alert.status = "read"
            db.commit()
        return _alert_to_dict(alert, user, db)

    @router.patch("/alerts/{alert_id}/resolve")
    def resolve_alert(alert_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        alert = _get_owned_alert(db, alert_id, user)
        alert.status = "resolved"
        db.commit()
        return _alert_to_dict(alert, user, db)

    return router
