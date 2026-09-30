"""Phase 8: authenticated CRUD for a user's farms."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from auth_utils import get_current_user
from db import get_db
from db_models import Farm, User

router = APIRouter(prefix="/farms", tags=["farms"])


class FarmIn(BaseModel):
    name: str
    gram_panchayat: str
    state: str = "Telangana"
    district: str = "Khammam"
    block: str = "Sathupally"
    village: str | None = None
    area_value: float | None = None
    area_unit: str = "acre"
    irrigation: str | None = None
    soil_type: str | None = None
    # Phase 0.5: plot-precision location, distinct from gram_panchayat.
    # Left null (never invented) for farms created before this field existed.
    latitude: float | None = None
    longitude: float | None = None
    boundary_geojson: str | None = None
    location_name: str | None = None


class FarmUpdate(BaseModel):
    name: str | None = None
    village: str | None = None
    area_value: float | None = None
    area_unit: str | None = None
    irrigation: str | None = None
    soil_type: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    boundary_geojson: str | None = None
    location_name: str | None = None


class FarmOut(FarmIn):
    id: str
    owner_id: str

    model_config = ConfigDict(from_attributes=True)


def _get_owned_farm(db: Session, farm_id: str, user: User) -> Farm:
    farm = db.get(Farm, farm_id)
    if farm is None or farm.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    return farm


@router.get("", response_model=list[FarmOut])
def list_farms(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Farm).filter(Farm.owner_id == user.id).all()


@router.post("", response_model=FarmOut, status_code=status.HTTP_201_CREATED)
def create_farm(payload: FarmIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    farm = Farm(owner_id=user.id, **payload.model_dump())
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@router.get("/{farm_id}", response_model=FarmOut)
def get_farm(farm_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_owned_farm(db, farm_id, user)


@router.patch("/{farm_id}", response_model=FarmOut)
def update_farm(
    farm_id: str,
    payload: FarmUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = _get_owned_farm(db, farm_id, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(farm, field, value)
    db.commit()
    db.refresh(farm)
    return farm


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farm(farm_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    farm = _get_owned_farm(db, farm_id, user)
    db.delete(farm)
    db.commit()
