"""Phase 2: spatial join + feature table build.

Pairs each Gram Panchayat with its nearest 0.25-degree IMD grid cell, then
joins that cell's daily rainfall against the GP's own proxy ground-truth
weather (from Open-Meteo / ERA5-Land) for every day of 2025.

Run from the project root:
    python src/build_training_table.py

Inputs (from data/processed/, produced by Phase 1):
    gp_centroids.csv
    rainfall_grid_clean.csv
    panchayat_weather/<gp_name>.csv

Output:
    data/processed/training_table.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from utils import find_column, haversine_km, safe_filename

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
CENTROIDS_FILE = PROCESSED_DIR / "gp_centroids.csv"
GRID_FILE = PROCESSED_DIR / "rainfall_grid_clean.csv"
WEATHER_DIR = PROCESSED_DIR / "panchayat_weather"
OUT_FILE = PROCESSED_DIR / "training_table.csv"

OUTPUT_COLUMNS = [
    "date",
    "gram_panchayat",
    "grid_rainfall_mm",
    "gp_rainfall_mm",
    "gp_temp_max",
    "gp_temp_min",
    "gp_rh_max",
    "gp_rh_min",
    "gp_wind_max",
    "elevation_m",
    "distance_to_grid_cell_km",
]


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    for f in (CENTROIDS_FILE, GRID_FILE):
        if not f.exists():
            sys.exit(f"Missing input file: {f}. Run Phase 1 scripts first.")

    centroids = pd.read_csv(CENTROIDS_FILE).dropna(subset=["latitude", "longitude"])
    grid = pd.read_csv(GRID_FILE, parse_dates=["date"])
    return centroids, grid


def nearest_grid_cell(gp_lat: float, gp_lon: float, grid_cells: pd.DataFrame) -> tuple[float, float, float]:
    """Return (grid_lat, grid_lon, distance_km) of the closest unique grid cell."""
    distances = grid_cells.apply(
        lambda row: haversine_km(gp_lat, gp_lon, row["latitude"], row["longitude"]), axis=1
    )
    nearest_idx = distances.idxmin()
    nearest = grid_cells.loc[nearest_idx]
    return nearest["latitude"], nearest["longitude"], distances[nearest_idx]


def load_gp_weather(gp_name: str) -> pd.DataFrame | None:
    path = WEATHER_DIR / f"{safe_filename(gp_name)}.csv"
    if not path.exists():
        print(f"  WARNING: no weather file for {gp_name} at {path}, skipping this GP")
        return None

    df = pd.read_csv(path)
    date_col = find_column(df.columns, ["time", "date"])
    if date_col is None:
        print(f"  WARNING: no date/time column in {path.name}, skipping this GP")
        return None

    rename = {
        date_col: "date",
        "precipitation_sum": "gp_rainfall_mm",
        "temperature_2m_max": "gp_temp_max",
        "temperature_2m_min": "gp_temp_min",
        "relative_humidity_2m_max": "gp_rh_max",
        "relative_humidity_2m_min": "gp_rh_min",
        "wind_speed_10m_max": "gp_wind_max",
    }
    df = df.rename(columns=rename)
    df["date"] = pd.to_datetime(df["date"])
    keep = ["date"] + [c for c in rename.values() if c != "date" and c in df.columns]
    return df[keep]


def build_table(centroids: pd.DataFrame, grid: pd.DataFrame) -> pd.DataFrame:
    grid_cells = grid[["latitude", "longitude"]].drop_duplicates().reset_index(drop=True)
    all_rows = []

    for _, gp in centroids.iterrows():
        gp_name = gp["gram_panchayat"]
        print(f"Joining {gp_name}...")

        gp_weather = load_gp_weather(gp_name)
        if gp_weather is None:
            continue

        grid_lat, grid_lon, distance_km = nearest_grid_cell(gp["latitude"], gp["longitude"], grid_cells)
        grid_series = grid[
            (grid["latitude"] == grid_lat) & (grid["longitude"] == grid_lon)
        ][["date", "rainfall_mm"]].rename(columns={"rainfall_mm": "grid_rainfall_mm"})
        grid_series["date"] = pd.to_datetime(grid_series["date"])

        merged = pd.merge(grid_series, gp_weather, on="date", how="inner")
        merged["gram_panchayat"] = gp_name
        merged["elevation_m"] = gp.get("elevation_m")
        merged["distance_to_grid_cell_km"] = distance_km

        all_rows.append(merged)

    if not all_rows:
        sys.exit("No GPs could be joined -- check that Phase 1 outputs exist and are populated.")

    table = pd.concat(all_rows, ignore_index=True)
    for col in OUTPUT_COLUMNS:
        if col not in table.columns:
            table[col] = None
    table = table[OUTPUT_COLUMNS].sort_values(["gram_panchayat", "date"]).reset_index(drop=True)
    return table


def print_summary(df: pd.DataFrame) -> None:
    print("\n--- Training table summary ---")
    print(f"Rows: {len(df)}")
    print(f"GPs: {df['gram_panchayat'].nunique()}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print("Missing values per column:")
    print(df.isna().sum().to_string())


def main() -> None:
    centroids, grid = load_inputs()
    table = build_table(centroids, grid)
    table.to_csv(OUT_FILE, index=False)
    print(f"\nSaved {len(table)} rows to {OUT_FILE}")
    print_summary(table)


if __name__ == "__main__":
    main()
