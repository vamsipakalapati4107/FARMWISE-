"""Phase 0.5, item 3/9: exposes the ML audit (src/ml_audit.py) over the API
so the frontend can show an accurate "source/type" label next to any
weather/advisory value instead of assuming everything is ML.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ml_audit import get_audit, get_component

router = APIRouter(prefix="/ml", tags=["ml-audit"])


@router.get("/models")
def list_ml_components():
    return get_audit()


@router.get("/models/{component}")
def get_ml_component(component: str):
    result = get_component(component)
    if result is None:
        available = [c["component"] for c in get_audit()]
        raise HTTPException(status_code=404, detail=f"Unknown component '{component}'. Available: {available}")
    return result
