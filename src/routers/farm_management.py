"""Farm section: farmer-entered record-keeping -- disease reports,
inspection records, and farm activity log. All three are genuinely new
tables (nothing like them existed before), but reuse the exact
ownership-check pattern already established in farms.py/crops.py/plots.py,
and the disease-report "analyze" action reuses src/gemini_service.py rather
than a second AI/ML integration.
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from auth_utils import get_current_user
from db import get_db
from db_models import Crop, DiseaseReport, Farm, FarmActivity, InspectionRecord, Plot, User
from gemini_service import get_disease_guidance

router = APIRouter(tags=["farm-management"])


def _get_owned_farm(db: Session, farm_id: str, user: User) -> Farm:
    farm = db.get(Farm, farm_id)
    if farm is None or farm.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    return farm


def _validate_plot_and_crop(db: Session, farm_id: str, plot_id: str | None, crop_id: str | None) -> None:
    if plot_id is not None:
        plot = db.get(Plot, plot_id)
        if plot is None or plot.farm_id != farm_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plot not found on this farm")
    if crop_id is not None:
        crop = db.get(Crop, crop_id)
        if crop is None or crop.farm_id != farm_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found on this farm")


# ---- Disease reports ----


class DiseaseReportIn(BaseModel):
    farm_id: str
    plot_id: str | None = None
    crop_id: str | None = None
    observed_problem: str
    symptoms: str | None = None
    observed_date: dt.date | None = None
    notes: str | None = None


class DiseaseReportOut(BaseModel):
    id: str
    farm_id: str
    plot_id: str | None
    crop_id: str | None
    observed_problem: str
    symptoms: str | None
    observed_date: dt.date | None
    notes: str | None
    ai_guidance: str | None
    ai_source: str | None
    created_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


def _get_owned_disease_report(db: Session, report_id: str, user: User) -> DiseaseReport:
    report = db.get(DiseaseReport, report_id)
    if report is None or report.farm.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disease report not found")
    return report


@router.get("/disease-reports", response_model=list[DiseaseReportOut])
def list_disease_reports(farm_id: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(DiseaseReport).join(Farm).filter(Farm.owner_id == user.id)
    if farm_id is not None:
        query = query.filter(DiseaseReport.farm_id == farm_id)
    return query.order_by(DiseaseReport.created_at.desc()).all()


@router.post("/disease-reports", response_model=DiseaseReportOut, status_code=status.HTTP_201_CREATED)
def create_disease_report(payload: DiseaseReportIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_owned_farm(db, payload.farm_id, user)
    _validate_plot_and_crop(db, payload.farm_id, payload.plot_id, payload.crop_id)
    report = DiseaseReport(user_id=user.id, **payload.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.post("/disease-reports/{report_id}/analyze", response_model=DiseaseReportOut)
def analyze_disease_report(report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Calls src/gemini_service.py -- honestly returns unavailable when no
    real Gemini API key is configured, never a fabricated guidance string."""
    report = _get_owned_disease_report(db, report_id, user)
    crop = report.crop
    result = get_disease_guidance(
        {
            "observed_problem": report.observed_problem,
            "symptoms": report.symptoms,
            "crop_name": crop.crop_name if crop else None,
            "stage": crop.stage if crop else None,
        }
    )
    if result.available:
        report.ai_guidance = result.guidance
        report.ai_source = result.source
        db.commit()
        db.refresh(report)
        return report
    # Not persisted as a fabricated guidance -- surfaced via the response,
    # not written into ai_guidance, so the report stays honestly "not yet
    # analyzed" rather than recording a permanent placeholder string.
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result.reason)


# ---- Inspection records ----


class InspectionIn(BaseModel):
    farm_id: str
    plot_id: str | None = None
    crop_id: str | None = None
    inspection_date: dt.date
    observed_symptoms: str | None = None
    pest_or_disease: str | None = None
    crop_condition: str | None = None
    notes: str | None = None


class InspectionOut(BaseModel):
    id: str
    farm_id: str
    plot_id: str | None
    crop_id: str | None
    inspection_date: dt.date
    observed_symptoms: str | None
    pest_or_disease: str | None
    crop_condition: str | None
    notes: str | None
    created_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("/inspections", response_model=list[InspectionOut])
def list_inspections(farm_id: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(InspectionRecord).join(Farm).filter(Farm.owner_id == user.id)
    if farm_id is not None:
        query = query.filter(InspectionRecord.farm_id == farm_id)
    return query.order_by(InspectionRecord.inspection_date.desc()).all()


@router.post("/inspections", response_model=InspectionOut, status_code=status.HTTP_201_CREATED)
def create_inspection(payload: InspectionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_owned_farm(db, payload.farm_id, user)
    _validate_plot_and_crop(db, payload.farm_id, payload.plot_id, payload.crop_id)
    record = InspectionRecord(user_id=user.id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ---- Farm activity log ----

ACTIVITY_TYPES = ["irrigation", "fertilizer", "inspection", "sowing", "spraying", "harvesting", "weeding", "other"]


class FarmActivityIn(BaseModel):
    farm_id: str
    plot_id: str | None = None
    crop_id: str | None = None
    activity_type: str
    activity_date: dt.date
    notes: str | None = None


class FarmActivityOut(BaseModel):
    id: str
    farm_id: str
    plot_id: str | None
    crop_id: str | None
    activity_type: str
    activity_date: dt.date
    notes: str | None
    created_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("/farm-activities", response_model=list[FarmActivityOut])
def list_farm_activities(farm_id: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(FarmActivity).join(Farm).filter(Farm.owner_id == user.id)
    if farm_id is not None:
        query = query.filter(FarmActivity.farm_id == farm_id)
    return query.order_by(FarmActivity.activity_date.desc()).all()


@router.post("/farm-activities", response_model=FarmActivityOut, status_code=status.HTTP_201_CREATED)
def create_farm_activity(payload: FarmActivityIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.activity_type not in ACTIVITY_TYPES:
        raise HTTPException(status_code=422, detail=f"Unknown activity_type '{payload.activity_type}'. Valid: {ACTIVITY_TYPES}")
    _get_owned_farm(db, payload.farm_id, user)
    _validate_plot_and_crop(db, payload.farm_id, payload.plot_id, payload.crop_id)
    activity = FarmActivity(user_id=user.id, **payload.model_dump())
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity
