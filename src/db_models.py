"""Phase 7/8: SQLAlchemy ORM models for the platform's app database."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, unique=True, nullable=True, index=True)
    mobile: Mapped[str | None] = mapped_column(String, unique=True, nullable=True, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str] = mapped_column(String, default="en")
    # Home page location (State/District/Block) -- distinct from Farm.
    # Nullable/unset for existing users; never inferred/invented.
    selected_state: Mapped[str | None] = mapped_column(String, nullable=True)
    selected_district: Mapped[str | None] = mapped_column(String, nullable=True)
    selected_block: Mapped[str | None] = mapped_column(String, nullable=True)
    # SMS notifications (see src/sms_service.py). `sms_alert_categories` is a
    # JSON-encoded list of category keys (see SMS_CATEGORIES); null means
    # "all categories" (the default), not "none" -- never silently opts a
    # user out of a category they never chose to disable.
    sms_notifications_enabled: Mapped[bool] = mapped_column(default=True)
    sms_alert_categories: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    farms: Mapped[list["Farm"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(default=False)


class Farm(Base):
    """A farm's `gram_panchayat` remains its resolved location for weather
    lookups (unchanged). `latitude`/`longitude`/`boundary_geojson` are new,
    nullable, plot-precision fields added in the Phase 0.5 foundation work --
    existing farms keep them null rather than having coordinates invented.
    See docs/FOUNDATION.md."""

    __tablename__ = "farms"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(String, default="Telangana")
    district: Mapped[str] = mapped_column(String, default="Khammam")
    block: Mapped[str] = mapped_column(String, default="Sathupally")
    gram_panchayat: Mapped[str] = mapped_column(String, nullable=False)
    village: Mapped[str | None] = mapped_column(String, nullable=True)
    area_value: Mapped[float | None] = mapped_column(nullable=True)
    area_unit: Mapped[str] = mapped_column(String, default="acre")
    irrigation: Mapped[str | None] = mapped_column(String, nullable=True)
    soil_type: Mapped[str | None] = mapped_column(String, nullable=True)
    # -- Phase 0.5 additions (all nullable; see src/migrate_db.py) --
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    boundary_geojson: Mapped[str | None] = mapped_column(String, nullable=True)
    location_name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    owner: Mapped[User] = relationship(back_populates="farms")
    crops: Mapped[list["Crop"]] = relationship(back_populates="farm", cascade="all, delete-orphan")
    plots: Mapped[list["Plot"]] = relationship(back_populates="farm", cascade="all, delete-orphan")


class Plot(Base):
    """Phase 0.5: a farm may contain one or more plots. A plot optionally
    carries its own coordinates/boundary, distinct from (and finer-grained
    than) the farm's Gram Panchayat. Crops may optionally be linked to a
    specific plot via Crop.plot_id (nullable, backward compatible -- crops
    created before this phase stay attached to their farm only)."""

    __tablename__ = "plots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    farm_id: Mapped[str] = mapped_column(String, ForeignKey("farms.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    boundary_geojson: Mapped[str | None] = mapped_column(String, nullable=True)
    area_value: Mapped[float | None] = mapped_column(nullable=True)
    area_unit: Mapped[str] = mapped_column(String, default="acre")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    farm: Mapped[Farm] = relationship(back_populates="plots")
    crops: Mapped[list["Crop"]] = relationship(back_populates="plot")


class Crop(Base):
    __tablename__ = "crops"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    farm_id: Mapped[str] = mapped_column(String, ForeignKey("farms.id"), nullable=False)
    plot_id: Mapped[str | None] = mapped_column(String, ForeignKey("plots.id"), nullable=True)
    crop_name: Mapped[str] = mapped_column(String, nullable=False)
    variety: Mapped[str | None] = mapped_column(String, nullable=True)
    sowing_date: Mapped[dt.date | None] = mapped_column(nullable=True)
    stage: Mapped[str] = mapped_column(String, default="Sowing")
    area_value: Mapped[float | None] = mapped_column(nullable=True)
    area_unit: Mapped[str] = mapped_column(String, default="acre")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    farm: Mapped[Farm] = relationship(back_populates="crops")
    plot: Mapped[Plot | None] = relationship(back_populates="crops")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, default="info")
    read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class Alert(Base):
    """Phase 5: Smart Alerts & Early Warning System. Distinct from the
    Phase 0.5/13 `Notification` table (kept unchanged) -- Alerts carry full
    farm/plot/crop context, a 4-tier severity, a typed `source`, and a
    NEW/READ/RESOLVED/EXPIRED lifecycle, generated by src/alert_engine.py.

    `dedupe_key` is unique per user and encodes
    (farm_id, plot_id, alert_type, source, the specific date the alert
    concerns) so the same real-world condition is never re-alerted twice --
    see src/routers/alert_center.py's sync logic."""

    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    farm_id: Mapped[str] = mapped_column(String, ForeignKey("farms.id"), nullable=False)
    plot_id: Mapped[str | None] = mapped_column(String, ForeignKey("plots.id"), nullable=True)
    alert_type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)  # critical | warning | attention | info
    title: Mapped[str] = mapped_column(String, nullable=False)
    condition: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    recommended_action: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="new")  # new | read | resolved | expired
    dedupe_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    valid_until: Mapped[dt.date | None] = mapped_column(nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    # One-directional (no back_populates -- Farm/Plot don't need an .alerts
    # collection today); lets the API attach farm/plot/crop names for
    # display without a second query per alert.
    farm: Mapped[Farm] = relationship("Farm", viewonly=True)
    plot: Mapped["Plot | None"] = relationship("Plot", viewonly=True)


class SmsMessage(Base):
    """Phase 6: Farmer SMS alerts. One row per SMS ever generated for an
    Alert -- `alert_id` is unique, so "one SMS per Alert row" is enforced at
    the schema level (and since alert_engine.py already mints one Alert row
    per condition per real calendar date, this is the actual per-day dedup
    mechanism, not a second one). No real SMS provider is configured in this
    project (see src/sms_service.py) -- `simulated=True` on every row here
    until one is; delivery is never claimed without a real provider response.
    """

    __tablename__ = "sms_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    alert_id: Mapped[str] = mapped_column(String, ForeignKey("alerts.id"), nullable=False, unique=True)
    to_number: Mapped[str] = mapped_column(String, nullable=False)
    alert_type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str] = mapped_column(String, default="en")
    status: Mapped[str] = mapped_column(String, default="QUEUED")  # QUEUED | SENT | DELIVERED | FAILED
    simulated: Mapped[bool] = mapped_column(default=True)
    provider_response: Mapped[str | None] = mapped_column(String, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)


class HealthSnapshot(Base):
    """Phase 5: one real logged Crop Health observation per plot per day,
    appended organically as the alert engine runs (never backfilled or
    fabricated). Enables genuine Crop Health Decline detection once 2+ real
    snapshots exist for a plot -- see src/alert_engine.py."""

    __tablename__ = "health_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    plot_id: Mapped[str] = mapped_column(String, ForeignKey("plots.id"), nullable=False)
    date: Mapped[str] = mapped_column(String, nullable=False)  # the forecast/current date this snapshot is for
    status: Mapped[str] = mapped_column(String, nullable=False)  # GOOD | FAIR | POOR
    recorded_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class DiseaseReport(Base):
    """Farm section: a farmer's own observation, always labeled as such --
    never auto-upgraded to a confirmed diagnosis. `ai_guidance`/`ai_source`
    are filled in by src/gemini_service.py on request (see /disease-reports/
    {id}/analyze); both stay null until the farmer explicitly asks for
    guidance, and null forever if no real Gemini API key is configured."""

    __tablename__ = "disease_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    farm_id: Mapped[str] = mapped_column(String, ForeignKey("farms.id"), nullable=False)
    plot_id: Mapped[str | None] = mapped_column(String, ForeignKey("plots.id"), nullable=True)
    crop_id: Mapped[str | None] = mapped_column(String, ForeignKey("crops.id"), nullable=True)
    observed_problem: Mapped[str] = mapped_column(String, nullable=False)
    symptoms: Mapped[str | None] = mapped_column(String, nullable=True)
    observed_date: Mapped[dt.date | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_guidance: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_source: Mapped[str | None] = mapped_column(String, nullable=True)  # e.g. "gemini" -- null until analyzed
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    farm: Mapped[Farm] = relationship("Farm", viewonly=True)
    plot: Mapped["Plot | None"] = relationship("Plot", viewonly=True)
    crop: Mapped["Crop | None"] = relationship("Crop", viewonly=True)


class InspectionRecord(Base):
    """Farm section: a farmer-logged field inspection. The system can
    *recommend* an inspection (derived from real risk data, see
    farm_advisor.py's field_inspection category) but never claims one
    happened unless the farmer records it here."""

    __tablename__ = "inspection_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    farm_id: Mapped[str] = mapped_column(String, ForeignKey("farms.id"), nullable=False)
    plot_id: Mapped[str | None] = mapped_column(String, ForeignKey("plots.id"), nullable=True)
    crop_id: Mapped[str | None] = mapped_column(String, ForeignKey("crops.id"), nullable=True)
    inspection_date: Mapped[dt.date] = mapped_column(nullable=False)
    observed_symptoms: Mapped[str | None] = mapped_column(String, nullable=True)
    pest_or_disease: Mapped[str | None] = mapped_column(String, nullable=True)
    crop_condition: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    farm: Mapped[Farm] = relationship("Farm", viewonly=True)
    plot: Mapped["Plot | None"] = relationship("Plot", viewonly=True)
    crop: Mapped["Crop | None"] = relationship("Crop", viewonly=True)


class FarmActivity(Base):
    """Farm section: a farmer-logged activity (irrigation done, fertilizer
    applied, sowing, spraying, ...). Purely user-entered record-keeping --
    never inferred from weather/ML data."""

    __tablename__ = "farm_activities"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    farm_id: Mapped[str] = mapped_column(String, ForeignKey("farms.id"), nullable=False)
    plot_id: Mapped[str | None] = mapped_column(String, ForeignKey("plots.id"), nullable=True)
    crop_id: Mapped[str | None] = mapped_column(String, ForeignKey("crops.id"), nullable=True)
    activity_type: Mapped[str] = mapped_column(String, nullable=False)  # irrigation | fertilizer | inspection | sowing | spraying | harvesting | weeding | other
    activity_date: Mapped[dt.date] = mapped_column(nullable=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    farm: Mapped[Farm] = relationship("Farm", viewonly=True)
    plot: Mapped["Plot | None"] = relationship("Plot", viewonly=True)
    crop: Mapped["Crop | None"] = relationship("Crop", viewonly=True)
