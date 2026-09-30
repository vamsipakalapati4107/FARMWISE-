"""Phase 8: authenticated CRUD for crops attached to a user's farm."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session

from auth_utils import get_current_user
from crop_catalog import get_crop
from db import get_db
from db_models import Crop, Farm, Plot, User

router = APIRouter(tags=["crops"])


class CropIn(BaseModel):
    farm_id: str
    plot_id: str | None = None
    crop_name: str
    variety: str | None = None
    sowing_date: dt.date | None = None
    stage: str = "Sowing"
    area_value: float | None = None
    area_unit: str = "acre"

    @field_validator("crop_name")
    @classmethod
    def crop_must_be_known(cls, v: str) -> str:
        if get_crop(v) is None:
            raise ValueError(f"Unknown crop '{v}' -- see GET /locations/crops for the valid list")
        return v


class CropUpdate(BaseModel):
    plot_id: str | None = None
    crop_name: str | None = None
    variety: str | None = None
    sowing_date: dt.date | None = None
    stage: str | None = None
    area_value: float | None = None
    area_unit: str | None = None

    @field_validator("crop_name")
    @classmethod
    def crop_must_be_known(cls, v: str | None) -> str | None:
        if v is not None and get_crop(v) is None:
            raise ValueError(f"Unknown crop '{v}' -- see GET /locations/crops for the valid list")
        return v


class CropOut(BaseModel):
    id: str
    farm_id: str
    plot_id: str | None
    crop_name: str
    variety: str | None
    sowing_date: dt.date | None
    stage: str
    area_value: float | None
    area_unit: str

    model_config = ConfigDict(from_attributes=True)


def _get_owned_farm(db: Session, farm_id: str, user: User) -> Farm:
    farm = db.get(Farm, farm_id)
    if farm is None or farm.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    return farm


def _validate_plot_belongs_to_farm(db: Session, plot_id: str, farm_id: str) -> None:
    plot = db.get(Plot, plot_id)
    if plot is None or plot.farm_id != farm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plot not found on this farm")


def _get_owned_crop(db: Session, crop_id: str, user: User) -> Crop:
    crop = db.get(Crop, crop_id)
    if crop is None or crop.farm.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")
    return crop


@router.get("/crops", response_model=list[CropOut])
def list_crops(farm_id: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Crop).join(Farm).filter(Farm.owner_id == user.id)
    if farm_id is not None:
        query = query.filter(Crop.farm_id == farm_id)
    return query.all()


@router.post("/crops", response_model=CropOut, status_code=status.HTTP_201_CREATED)
def create_crop(payload: CropIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_owned_farm(db, payload.farm_id, user)  # 404s if not the caller's farm
    if payload.plot_id is not None:
        _validate_plot_belongs_to_farm(db, payload.plot_id, payload.farm_id)
    crop = Crop(**payload.model_dump())
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return crop


@router.patch("/crops/{crop_id}", response_model=CropOut)
def update_crop(
    crop_id: str,
    payload: CropUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crop = _get_owned_crop(db, crop_id, user)
    updates = payload.model_dump(exclude_unset=True)
    if "plot_id" in updates and updates["plot_id"] is not None:
        _validate_plot_belongs_to_farm(db, updates["plot_id"], crop.farm_id)
    for field, value in updates.items():
        setattr(crop, field, value)
    db.commit()
    db.refresh(crop)
    return crop


@router.delete("/crops/{crop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_crop(crop_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    crop = _get_owned_crop(db, crop_id, user)
    db.delete(crop)
    db.commit()
