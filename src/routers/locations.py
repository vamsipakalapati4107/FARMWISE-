"""Phase 8: State -> District -> Block/Mandal -> Panchayat -> Village
hierarchy, served from the real LGD mapping CSV (the only location data
this project has ground truth for). Structured so a second block's
mapping CSV could be added as another row in BLOCK_MAPPING_FILES later
without restructuring these endpoints -- same config-driven pattern as
VARIABLE_SPECS in train_downscaling_model.py.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException

from utils import find_column

RAW_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"

# state -> district -> block -> mapping CSV. Today we only have real data
# for one block; add more entries here (and drop their CSVs in data/raw/)
# to bring more blocks online without touching the endpoints below.
BLOCK_MAPPING_FILES = {
    ("Telangana", "Khammam", "Sathupally"): RAW_DIR / "Sathupalli_Khammam_LGD_Village_GramPanchayat_Mapping.csv",
}

router = APIRouter(prefix="/locations", tags=["locations"])


@lru_cache(maxsize=None)
def _load_mapping(state: str, district: str, block: str) -> pd.DataFrame:
    path = BLOCK_MAPPING_FILES.get((state, district, block))
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail=f"No location data for {state}/{district}/{block}")

    df = pd.read_csv(path)
    gp_col = find_column(df.columns, ["gram panchayat", "gp name", "gram_panchayat", "panchayat"])
    village_col = find_column(df.columns, ["village", "village name"])
    if gp_col is None or village_col is None:
        raise HTTPException(status_code=500, detail=f"Unexpected columns in {path.name}: {list(df.columns)}")

    return df.rename(columns={gp_col: "gram_panchayat", village_col: "village"})


@router.get("/states")
def list_states():
    return sorted({state for state, _, _ in BLOCK_MAPPING_FILES})


@router.get("/districts")
def list_districts(state: str):
    districts = sorted({district for s, district, _ in BLOCK_MAPPING_FILES if s == state})
    if not districts:
        raise HTTPException(status_code=404, detail=f"No districts found for state '{state}'")
    return districts


@router.get("/blocks")
def list_blocks(state: str, district: str):
    blocks = sorted({block for s, d, block in BLOCK_MAPPING_FILES if s == state and d == district})
    if not blocks:
        raise HTTPException(status_code=404, detail=f"No blocks found for {state}/{district}")
    return blocks


@router.get("/panchayats")
def list_panchayats(state: str, district: str, block: str):
    df = _load_mapping(state, district, block)
    return sorted(df["gram_panchayat"].dropna().unique().tolist())


@router.get("/villages")
def list_villages(state: str, district: str, block: str, gram_panchayat: str):
    df = _load_mapping(state, district, block)
    rows = df[df["gram_panchayat"] == gram_panchayat]
    if rows.empty:
        raise HTTPException(status_code=404, detail=f"Unknown Gram Panchayat '{gram_panchayat}' in {block}")
    return sorted(rows["village"].dropna().unique().tolist())


@router.get("/crops")
def list_crops():
    from crop_catalog import CROPS

    return CROPS
