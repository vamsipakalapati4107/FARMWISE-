"""Phase 6: Farmer SMS alerts -- provider abstraction + send decision.

No real SMS provider (Twilio/MSG91/etc.) is configured anywhere in this
project -- SMS_PROVIDER defaults to "simulated", the only implementation
shipped. It never claims real delivery: every row it writes carries
simulated=True and status="SENT" (meaning "handed to the simulated
provider", not "delivered to a handset"). Swapping in a real provider later
means implementing SmsProvider.send() for it and setting the SMS_PROVIDER
env var -- nothing in alert_center.py (the only caller) needs to change.

Reuses, rather than duplicates, the existing Alert pipeline: this module is
only ever invoked from src/routers/alert_center.py, right after a genuinely
NEW Alert row is inserted (alert_engine.py already guarantees at most one
Alert per real-world condition per calendar date via `dedupe_key`) -- so
"one SMS per Alert" (enforced by SmsMessage.alert_id being unique) is the
per-condition dedup, and DEFAULT_COOLDOWN_MINUTES below is an additional,
separate throttle across different alerts for the same user.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass

from sqlalchemy.orm import Session

from db_models import SmsMessage, User

# Only these two severities are ever SMS-worthy -- never "attention"/"info",
# never every daily advisory (see the product spec this implements).
SMS_ELIGIBLE_SEVERITIES = {"critical", "warning"}

# Coarse categories a farmer can opt out of individually. Maps
# alert_engine.py's ALERT_TYPES into the 4 farmer-facing buckets requested.
SMS_CATEGORIES: dict[str, str] = {
    "heavy_rainfall": "severe_weather",
    "heat_risk": "severe_weather",
    "strong_wind": "severe_weather",  # not currently generated (no threshold exists) -- mapped for forward compatibility
    "excess_moisture": "severe_weather",
    "disease_risk": "disease_risk",
    "crop_stress": "crop_stress",  # not currently generated (no model exists) -- mapped for forward compatibility
    "crop_health_decline": "crop_stress",
    "irrigation_concern": "farm_actions",
    "farm_operation": "farm_actions",
}
ALL_SMS_CATEGORIES = ["severe_weather", "disease_risk", "crop_stress", "farm_actions"]

DEFAULT_COOLDOWN_MINUTES = int(os.environ.get("SMS_COOLDOWN_MINUTES", "60"))
SMS_PROVIDER_NAME = os.environ.get("SMS_PROVIDER", "simulated")


@dataclass
class SmsSendResult:
    status: str  # SENT | FAILED  (DELIVERED is provider-confirmed only, never set here)
    simulated: bool
    provider_response: str | None
    failure_reason: str | None


class SmsProvider:
    """Abstraction point -- a real provider (Twilio, MSG91, ...) implements
    this and is selected via SMS_PROVIDER; nothing else in this module or
    alert_center.py needs to change to add one."""

    def send(self, to: str, message: str) -> SmsSendResult:
        raise NotImplementedError


class SimulatedSmsProvider(SmsProvider):
    """The only provider shipped -- no real SMS credentials exist in this
    project. Never claims delivery; records exactly what happened (a
    simulated hand-off), so nothing downstream mistakes this for a real
    sent message."""

    def send(self, to: str, message: str) -> SmsSendResult:
        return SmsSendResult(
            status="SENT",
            simulated=True,
            provider_response="Simulated -- no real SMS provider is configured for this deployment.",
            failure_reason=None,
        )


def get_provider() -> SmsProvider:
    if SMS_PROVIDER_NAME == "simulated":
        return SimulatedSmsProvider()
    # A real provider would be wired in here, e.g.:
    #   if SMS_PROVIDER_NAME == "twilio": return TwilioSmsProvider()
    # Never silently fall back to "simulated" for an explicitly-configured
    # provider that isn't implemented -- that would risk claiming delivery
    # that didn't happen.
    raise NotImplementedError(
        f"SMS_PROVIDER={SMS_PROVIDER_NAME!r} has no implementation yet. Add a provider class and wire it in here."
    )


def user_sms_categories(user: User) -> set[str]:
    """Null/unset means "all categories" (the default), never "none"."""
    if not user.sms_alert_categories:
        return set(ALL_SMS_CATEGORIES)
    try:
        return set(json.loads(user.sms_alert_categories))
    except (ValueError, TypeError):
        return set(ALL_SMS_CATEGORIES)


def render_sms_message(candidate: dict) -> str:
    """Short, farmer-friendly, English only -- no Telugu/Hindi text exists
    anywhere in this backend to translate from, so this is honestly
    English-only for now (see docs) rather than a fabricated translation."""
    return f"FarmWise Alert: {candidate['reason']} {candidate['recommended_action']} Open FarmWise for details."[:320]


def should_send_sms(candidate: dict, user: User, db: Session) -> tuple[bool, str | None]:
    """Pure decision function (same shape as advisory_rules.py/alert_engine.py's
    rule functions) -- returns (should_send, skip_reason)."""
    if candidate["severity"] not in SMS_ELIGIBLE_SEVERITIES:
        return False, "severity not SMS-eligible"
    if not user.sms_notifications_enabled:
        return False, "user has SMS notifications disabled"
    if not user.mobile:
        return False, "no mobile number on file"

    category = SMS_CATEGORIES.get(candidate["alert_type"])
    if category and category not in user_sms_categories(user):
        return False, f"user has '{category}' SMS category disabled"

    last = db.query(SmsMessage).filter(SmsMessage.user_id == user.id).order_by(SmsMessage.created_at.desc()).first()
    if last is not None and dt.datetime.utcnow() - last.created_at < dt.timedelta(minutes=DEFAULT_COOLDOWN_MINUTES):
        return False, f"cooldown active ({DEFAULT_COOLDOWN_MINUTES}min)"

    return True, None


def send_sms_for_alert(candidate: dict, alert_id: str, user: User, db: Session) -> SmsMessage | None:
    """Called once per newly-inserted Alert row (see alert_center.py). Returns
    the SmsMessage it added to `db` (not yet committed -- caller commits), or
    None if it decided not to send."""
    should, _skip_reason = should_send_sms(candidate, user, db)
    if not should:
        return None

    message_text = render_sms_message(candidate)
    result = get_provider().send(user.mobile, message_text)
    sms = SmsMessage(
        user_id=user.id,
        alert_id=alert_id,
        to_number=user.mobile,
        alert_type=candidate["alert_type"],
        severity=candidate["severity"],
        message=message_text,
        language=user.language or "en",
        status=result.status,
        simulated=result.simulated,
        provider_response=result.provider_response,
        failure_reason=result.failure_reason,
        sent_at=dt.datetime.utcnow() if result.status in ("SENT", "DELIVERED") else None,
    )
    db.add(sms)
    return sms


def alert_sms_status(alert_id: str, alert_severity: str, alert_type: str, user: User, db: Session) -> dict:
    """For Alert Center display -- 'traceable' status, never claims a send
    that didn't happen."""
    sms = db.query(SmsMessage).filter(SmsMessage.alert_id == alert_id).first()
    if sms is not None:
        return {"status": sms.status, "simulated": sms.simulated}
    if alert_severity not in SMS_ELIGIBLE_SEVERITIES:
        return {"status": "NOT_APPLICABLE", "simulated": False}
    if not user.sms_notifications_enabled or not user.mobile:
        return {"status": "DISABLED", "simulated": False}
    category = SMS_CATEGORIES.get(alert_type)
    if category and category not in user_sms_categories(user):
        return {"status": "DISABLED", "simulated": False}
    return {"status": "NOT_SENT", "simulated": False}
