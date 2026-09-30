"""Phase 8: static crop/variety/stage reference catalog for the crop
selector and onboarding wizard.

This is reference data (common crops grown around Sathupally block,
Khammam district), not weather/geographic data -- distinct from the
"never present fake weather/location data as real" rule. Extend CROPS to
add more crops; no other file needs to change.
"""
from __future__ import annotations

CROPS: list[dict] = [
    {
        "name": "Cotton",
        "varieties": ["Bunny BG II", "RCH 2 BG II", "Mallika"],
        "stages": ["Sowing", "Vegetative", "Squaring", "Flowering", "Boll Formation", "Maturity", "Harvest"],
    },
    {
        "name": "Paddy (Rice)",
        "varieties": ["BPT 5204 (Samba Masuri)", "MTU 1010", "RNR 15048"],
        "stages": [
            "Nursery",
            "Transplanting",
            "Vegetative",
            "Tillering",
            "Panicle Initiation",
            "Flowering",
            "Grain Filling",
            "Maturity",
            "Harvest",
        ],
    },
    {
        "name": "Maize",
        "varieties": ["DHM 117", "Pioneer 3396"],
        "stages": ["Sowing", "Vegetative", "Tasseling", "Silking", "Grain Filling", "Maturity", "Harvest"],
    },
    {
        "name": "Chilli",
        "varieties": ["Teja", "Byadgi"],
        "stages": ["Nursery", "Transplanting", "Vegetative", "Flowering", "Fruiting", "Harvest"],
    },
    {
        "name": "Turmeric",
        "varieties": ["Duggirala", "Kesari"],
        "stages": ["Planting", "Vegetative", "Rhizome Development", "Maturity", "Harvest"],
    },
    {
        "name": "Redgram (Toor Dal)",
        "varieties": ["Asha (ICPL 87119)", "LRG 41"],
        "stages": ["Sowing", "Vegetative", "Flowering", "Pod Formation", "Maturity", "Harvest"],
    },
    {
        "name": "Groundnut",
        "varieties": ["Kadiri 6", "TAG 24"],
        "stages": ["Sowing", "Vegetative", "Flowering", "Pegging", "Pod Development", "Maturity", "Harvest"],
    },
]

CROP_NAMES = [c["name"] for c in CROPS]


def get_crop(name: str) -> dict | None:
    return next((c for c in CROPS if c["name"] == name), None)
