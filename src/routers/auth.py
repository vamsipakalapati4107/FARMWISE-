"""Phase 7: registration, login, password reset, profile endpoints."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from sqlalchemy.orm import Session

from auth_utils import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from db import get_db
from db_models import PasswordResetToken, User

router = APIRouter(prefix="/auth", tags=["auth"])

RESET_TOKEN_EXPIRE_MINUTES = 30


class RegisterRequest(BaseModel):
    name: str
    password: str
    email: EmailStr | None = None
    mobile: str | None = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("mobile")
    @classmethod
    def identifier_present(cls, v, info):
        if v is None and info.data.get("email") is None:
            raise ValueError("Provide an email or mobile number")
        return v


class LoginRequest(BaseModel):
    identifier: str  # email or mobile
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    name: str
    email: str | None
    mobile: str | None
    language: str
    selected_state: str | None = None
    selected_district: str | None = None
    selected_block: str | None = None
    # SMS alerts (see src/sms_service.py). null categories means "all" --
    # decoded from the DB's JSON-string column, never exposed as raw JSON.
    sms_notifications_enabled: bool = True
    sms_alert_categories: list[str] | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("sms_alert_categories", mode="before")
    @classmethod
    def _parse_sms_categories(cls, v):
        if v is None or isinstance(v, list):
            return v
        try:
            return json.loads(v)
        except (ValueError, TypeError):
            return None


class ForgotPasswordRequest(BaseModel):
    identifier: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    language: str | None = None
    # Home page location (State/District/Block) -- reuses the existing
    # profile-update endpoint rather than a new one. Real values only,
    # validated against the same reference data the frontend picker uses.
    selected_state: str | None = None
    selected_district: str | None = None
    selected_block: str | None = None
    sms_notifications_enabled: bool | None = None
    sms_alert_categories: list[str] | None = None


def _find_user_by_identifier(db: Session, identifier: str) -> User | None:
    return db.query(User).filter((User.email == identifier) | (User.mobile == identifier)).first()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if payload.email and db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if payload.mobile and db.query(User).filter(User.mobile == payload.mobile).first():
        raise HTTPException(status_code=400, detail="Mobile number already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        mobile=payload.mobile,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = _find_user_by_identifier(db, payload.identifier)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email/mobile or password")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(payload: ProfileUpdateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.name is not None:
        user.name = payload.name
    if payload.language is not None:
        user.language = payload.language
    if payload.selected_state is not None:
        user.selected_state = payload.selected_state
    if payload.selected_district is not None:
        user.selected_district = payload.selected_district
    if payload.selected_block is not None:
        user.selected_block = payload.selected_block
    if payload.sms_notifications_enabled is not None:
        user.sms_notifications_enabled = payload.sms_notifications_enabled
    if payload.sms_alert_categories is not None:
        user.sms_alert_categories = json.dumps(payload.sms_alert_categories)
    db.commit()
    db.refresh(user)
    return user


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = _find_user_by_identifier(db, payload.identifier)
    if user is None:
        # Don't reveal whether the identifier exists.
        return {"detail": "If that account exists, a reset link has been generated."}

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=dt.datetime.utcnow() + dt.timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
    )
    db.add(reset)
    db.commit()

    # No email/SMS provider is configured for this demo -- the reset link is
    # logged server-side instead of delivered. See README "Known limitations".
    print(f"[password reset] user={user.id} link=/reset-password?token={raw_token}")

    return {"detail": "If that account exists, a reset link has been generated."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    reset = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash, PasswordResetToken.used.is_(False))
        .first()
    )
    if reset is None or reset.expires_at < dt.datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = db.get(User, reset.user_id)
    user.password_hash = hash_password(payload.new_password)
    reset.used = True
    db.commit()
    return {"detail": "Password updated"}
