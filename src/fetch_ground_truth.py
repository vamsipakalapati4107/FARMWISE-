"""Phase 1: build GP centroids (geocode + elevation) and pull per-GP proxy
ground-truth weather (ERA5-Land via Open-Meteo Archive) for 2025.

Run from the project root:
    python src/fetch_ground_truth.py

Inputs (place in data/raw/):
    Sathupalli_Khammam_LGD_Village_GramPanchayat_Mapping.csv

Outputs (written to data/processed/):
    gp_centroids.csv                  -- gram_panchayat, latitude, longitude, elevation_m
    panchayat_weather/<gp_name>.csv   -- one file per GP, daily 2025 weather
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import requests

from utils import find_column, safe_filename

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
WEATHER_DIR = PROCESSED_DIR / "panchayat_weather"

MAPPING_FILE = RAW_DIR / "Sathupalli_Khammam_LGD_Village_GramPanchayat_Mapping.csv"
CENTROIDS_FILE = PROCESSED_DIR / "gp_centroids.csv"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Nominatim's usage policy requires a descriptive User-Agent with contact
# info. Edit CONTACT below to your own email before running at any volume.
CONTACT = "set-your-contact-email-here"
USER_AGENT = f"panchayat-downscaling-sih26074/1.0 (contact: {CONTACT})"

GEOCODE_RATE_LIMIT_SEC = 1.0
DAILY_VARS = [
    "precipitation_sum",
    "temperature_2m_max",
    "temperature_2m_min",
    "relative_humidity_2m_max",
    "relative_humidity_2m_min",
    "wind_speed_10m_max",
]
START_DATE = "2025-01-01"
END_DATE = "2025-12-31"


def load_gp_names() -> list[str]:
    """Extract the unique list of Gram Panchayat names from the LGD mapping file."""
    if not MAPPING_FILE.exists():
        sys.exit(
            f"Missing input file: {MAPPING_FILE}\n"
            "Drop the LGD village/GP mapping CSV into data/raw/ and re-run."
        )

    df = pd.read_csv(MAPPING_FILE)
    gp_col = find_column(
        df.columns,
        ["gram panchayat name", "gp name", "gram_panchayat", "gram panchayat", "panchayat"],
    )
    if gp_col is None:
        sys.exit(
            "Could not find a Gram Panchayat name column in "
            f"{MAPPING_FILE.name}. Columns found: {list(df.columns)}"
        )

    names = sorted(df[gp_col].dropna().astype(str).str.strip().unique().tolist())
    print(f"Found {len(names)} unique Gram Panchayats in {MAPPING_FILE.name}")
    return names


def geocode_gp(session: requests.Session, gp_name: str) -> tuple[float, float] | None:
    query = f"{gp_name}, Khammam, Telangana, India"
    resp = session.get(
        NOMINATIM_URL,
        params={"q": query, "format": "json", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])


def build_centroids(gp_names: list[str]) -> pd.DataFrame:
    session = requests.Session()
    rows = []
    for i, gp_name in enumerate(gp_names, start=1):
        print(f"[{i}/{len(gp_names)}] Geocoding {gp_name}...", end=" ")
        try:
            coords = geocode_gp(session, gp_name)
        except requests.RequestException as exc:
            print(f"FAILED ({exc})")
            coords = None
        else:
            print("ok" if coords else "NOT FOUND")

        rows.append(
            {
                "gram_panchayat": gp_name,
                "latitude": coords[0] if coords else None,
                "longitude": coords[1] if coords else None,
            }
        )
        time.sleep(GEOCODE_RATE_LIMIT_SEC)

    df = pd.DataFrame(rows)
    missing = df[df["latitude"].isna()]
    if not missing.empty:
        print(
            f"\n{len(missing)} GP(s) failed to geocode and need manual coordinate entry: "
            f"{missing['gram_panchayat'].tolist()}"
        )
    return df


def add_elevation(df: pd.DataFrame) -> pd.DataFrame:
    geocoded = df.dropna(subset=["latitude", "longitude"])
    if geocoded.empty:
        df["elevation_m"] = None
        return df

    print(f"Fetching elevation for {len(geocoded)} centroids...")
    lat_str = ",".join(str(v) for v in geocoded["latitude"])
    lon_str = ",".join(str(v) for v in geocoded["longitude"])

    resp = requests.get(
        ELEVATION_URL,
        params={"latitude": lat_str, "longitude": lon_str},
        timeout=30,
    )
    resp.raise_for_status()
    elevations = resp.json().get("elevation", [])

    df.loc[geocoded.index, "elevation_m"] = elevations
    return df


def fetch_gp_weather(session: requests.Session, gp_name: str, lat: float, lon: float) -> pd.DataFrame:
    resp = session.get(
        ARCHIVE_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "daily": ",".join(DAILY_VARS),
            "timezone": "auto",
        },
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    if "daily" not in payload:
        raise RuntimeError(f"Unexpected response for {gp_name}: {payload}")
    return pd.DataFrame(payload["daily"])


def fetch_all_weather(df: pd.DataFrame) -> None:
    WEATHER_DIR.mkdir(parents=True, exist_ok=True)
    geocoded = df.dropna(subset=["latitude", "longitude"])
    session = requests.Session()

    for i, row in enumerate(geocoded.itertuples(index=False), start=1):
        gp_name = row.gram_panchayat
        print(f"[{i}/{len(geocoded)}] Fetching 2025 historical weather for {gp_name}...", end=" ")
        try:
            weather_df = fetch_gp_weather(session, gp_name, row.latitude, row.longitude)
        except (requests.RequestException, RuntimeError) as exc:
            print(f"FAILED ({exc})")
            continue

        out_path = WEATHER_DIR / f"{safe_filename(gp_name)}.csv"
        weather_df.to_csv(out_path, index=False)
        print(f"saved {out_path.relative_to(PROCESSED_DIR.parent.parent)}")


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    gp_names = load_gp_names()
    centroids = build_centroids(gp_names)
    centroids = add_elevation(centroids)

    centroids.to_csv(CENTROIDS_FILE, index=False)
    print(f"\nSaved centroids to {CENTROIDS_FILE}")

    fetch_all_weather(centroids)
    print("\nDone.")


if __name__ == "__main__":
    main()
