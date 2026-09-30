"""Phase 13: notification center.

There's no background job scheduler in this stack, so notifications are
synced lazily: whenever a user's notification list is requested, we check
their farms' Gram Panchayats for active alerts and insert any that aren't
already recorded (deduped by an embedded GP+date key in the title, so this
is safe to call repeatedly without creating duplicates).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth_utils import get_current_user
from db import get_db
from db_models import Farm, Notification, User
from routers.alerts import build_alert

router = APIRouter(prefix="/notifications", tags=["notifications"])


def register(router_state: dict) -> APIRouter:
    def _sync_notifications(db: Session, user: User) -> None:
        farms = db.query(Farm).filter(Farm.owner_id == user.id).all()
        forecast_df = router_state["forecast"]

        for farm in farms:
            gp_rows = forecast_df[forecast_df["gram_panchayat"] == farm.gram_panchayat]
            for _, row in gp_rows.iterrows():
                alert = build_alert(row)
                if alert is None:
                    continue

                dedupe_title = f"{alert['title']} — {farm.gram_panchayat} ({alert['date']})"
                exists = (
                    db.query(Notification)
                    .filter(Notification.user_id == user.id, Notification.title == dedupe_title)
                    .first()
                )
                if exists:
                    continue

                db.add(
                    Notification(
                        user_id=user.id,
                        title=dedupe_title,
                        body=f"{alert['description']} {alert['action']}",
                        severity=alert["severity"],
                    )
                )
        db.commit()

    @router.get("")
    def list_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        _sync_notifications(db, user)
        rows = (
            db.query(Notification)
            .filter(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .all()
        )
        return [
            {
                "id": n.id,
                "title": n.title,
                "body": n.body,
                "severity": n.severity,
                "read": n.read,
                "created_at": n.created_at.isoformat(),
            }
            for n in rows
        ]

    @router.post("/{notification_id}/read")
    def mark_read(notification_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        notification = db.get(Notification, notification_id)
        if notification is None or notification.user_id != user.id:
            raise HTTPException(status_code=404, detail="Notification not found")
        notification.read = True
        db.commit()
        return {"detail": "ok"}

    @router.post("/read-all")
    def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        db.query(Notification).filter(Notification.user_id == user.id, Notification.read.is_(False)).update(
            {"read": True}
        )
        db.commit()
        return {"detail": "ok"}

    return router
