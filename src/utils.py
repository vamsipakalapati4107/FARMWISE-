"""Small shared helpers for locating columns with unpredictable raw naming."""
from __future__ import annotations

import math
import re


def safe_filename(name: str) -> str:
    """Turn a Gram Panchayat name into the same filesystem-safe stem used
    when writing its per-GP weather CSV, so later scripts can look it up.
    """
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometers."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def find_column(columns, candidates: list[str]) -> str | None:
    """Return the first column in `columns` whose lowercased name matches
    (exactly, or via substring) one of `candidates`. Returns None if no match.
    """
    lower_map = {c.lower().strip(): c for c in columns}

    for cand in candidates:
        if cand in lower_map:
            return lower_map[cand]

    for cand in candidates:
        for lower_name, original in lower_map.items():
            if cand in lower_name:
                return original

    return None
