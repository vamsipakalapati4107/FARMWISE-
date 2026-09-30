"""Phase 1: standardize the coarse IMD rainfall grid and the live Sathupally
block forecast into clean, consistently-named CSVs.

Run from the project root:
    python src/clean_grid_and_forecast.py

Inputs (place in data/raw/):
    khammam_2025_rainfall_grid.csv  (or a .nc equivalent, see below)
    sathupally_block_forecast.csv

Outputs (written to data/processed/):
    rainfall_grid_clean.csv   -- latitude, longitude, date, rainfall_mm
    block_forecast_clean.csv -- date, rainfall_mm, temp_max_c, temp_min_c,
                                 rh_max_pct, rh_min_pct, wind_speed_max_kmh
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from utils import find_column

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

GRID_CSV = RAW_DIR / "khammam_2025_rainfall_grid.csv"
GRID_NC = RAW_DIR / "khammam_2025_rainfall_grid.nc"
FORECAST_CSV = RAW_DIR / "sathupally_block_forecast.csv"

GRID_OUT = PROCESSED_DIR / "rainfall_grid_clean.csv"
FORECAST_OUT = PROCESSED_DIR / "block_forecast_clean.csv"


def clean_rainfall_grid_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    lat_col = find_column(df.columns, ["latitude", "lat"])
    lon_col = find_column(df.columns, ["longitude", "long", "lon"])
    date_col = find_column(df.columns, ["date", "time", "day"])
    rain_col = find_column(df.columns, ["rainfall", "precipitation", "precip", "rain"])

    missing = [
        name
        for name, col in [("latitude", lat_col), ("longitude", lon_col), ("date", date_col), ("rainfall", rain_col)]
        if col is None
    ]
    if missing:
        sys.exit(
            f"Could not find column(s) {missing} in {path.name}. "
            f"Columns found: {list(df.columns)}"
        )

    out = df.rename(
        columns={lat_col: "latitude", lon_col: "longitude", date_col: "date", rain_col: "rainfall_mm"}
    )[["latitude", "longitude", "date", "rainfall_mm"]].copy()

    out["date"] = pd.to_datetime(out["date"]).dt.date
    out["latitude"] = out["latitude"].astype(float)
    out["longitude"] = out["longitude"].astype(float)
    out["rainfall_mm"] = pd.to_numeric(out["rainfall_mm"], errors="coerce")
    return out.sort_values(["date", "latitude", "longitude"]).reset_index(drop=True)


def clean_rainfall_grid_netcdf(path: Path) -> pd.DataFrame:
    import netCDF4

    ds = netCDF4.Dataset(path)
    try:
        var_names = list(ds.variables.keys())

        lat_name = find_column(var_names, ["latitude", "lat"])
        lon_name = find_column(var_names, ["longitude", "lon"])
        time_name = find_column(var_names, ["time", "date"])
        if not all([lat_name, lon_name, time_name]):
            sys.exit(
                f"Could not identify lat/lon/time variables in {path.name}. "
                f"Variables found: {var_names}"
            )

        data_candidates = [
            name
            for name in var_names
            if name not in (lat_name, lon_name, time_name) and ds.variables[name].ndim == 3
        ]
        if not data_candidates:
            sys.exit(
                f"Could not find a 3-D (time, lat, lon) rainfall variable in {path.name}. "
                f"Variables found: {var_names}"
            )
        rain_name = data_candidates[0]

        lats = ds.variables[lat_name][:]
        lons = ds.variables[lon_name][:]
        time_var = ds.variables[time_name]
        dates = netCDF4.num2date(time_var[:], units=time_var.units, calendar=getattr(time_var, "calendar", "standard"))
        rainfall = ds.variables[rain_name][:]  # shape: (time, lat, lon)

        rows = []
        for t_idx, date in enumerate(dates):
            for la_idx, lat in enumerate(lats):
                for lo_idx, lon in enumerate(lons):
                    value = rainfall[t_idx, la_idx, lo_idx]
                    if hasattr(value, "mask") and value.mask:
                        continue
                    rows.append(
                        {
                            "latitude": float(lat),
                            "longitude": float(lon),
                            "date": pd.Timestamp(date.isoformat()).date(),
                            "rainfall_mm": float(value),
                        }
                    )
        return pd.DataFrame(rows).sort_values(["date", "latitude", "longitude"]).reset_index(drop=True)
    finally:
        ds.close()


def clean_rainfall_grid() -> pd.DataFrame:
    if GRID_CSV.exists():
        print(f"Loading rainfall grid from {GRID_CSV.name}")
        return clean_rainfall_grid_csv(GRID_CSV)
    if GRID_NC.exists():
        print(f"Loading rainfall grid from {GRID_NC.name}")
        return clean_rainfall_grid_netcdf(GRID_NC)
    sys.exit(
        f"Missing rainfall grid input. Expected one of:\n  {GRID_CSV}\n  {GRID_NC}"
    )


def clean_block_forecast() -> pd.DataFrame:
    if not FORECAST_CSV.exists():
        sys.exit(f"Missing input file: {FORECAST_CSV}")

    print(f"Loading block forecast from {FORECAST_CSV.name}")
    df = pd.read_csv(FORECAST_CSV)

    col_map = {
        "date": find_column(df.columns, ["date", "day", "forecast_date"]),
        "rainfall_mm": find_column(df.columns, ["rainfall", "precipitation", "precip", "rain"]),
        "temp_max_c": find_column(df.columns, ["temp_max", "tmax", "temperature_max", "max_temp"]),
        "temp_min_c": find_column(df.columns, ["temp_min", "tmin", "temperature_min", "min_temp"]),
        "rh_max_pct": find_column(
            df.columns, ["rh_max", "max_rh", "humidity_max", "max_humidity", "relative_humidity_max"]
        ),
        "rh_min_pct": find_column(
            df.columns, ["rh_min", "min_rh", "humidity_min", "min_humidity", "relative_humidity_min"]
        ),
        "wind_speed_max_kmh": find_column(df.columns, ["wind_speed", "wind_max", "wind"]),
    }

    missing = [std_name for std_name, col in col_map.items() if col is None]
    if missing:
        print(
            f"Warning: could not find column(s) {missing} in {FORECAST_CSV.name}. "
            f"Columns found: {list(df.columns)}. These fields will be left blank."
        )

    out = pd.DataFrame()
    for std_name, col in col_map.items():
        out[std_name] = df[col] if col is not None else None

    out["date"] = pd.to_datetime(out["date"]).dt.date
    for numeric_col in [c for c in col_map if c != "date"]:
        out[numeric_col] = pd.to_numeric(out[numeric_col], errors="coerce")

    return out.sort_values("date").reset_index(drop=True)


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    grid_df = clean_rainfall_grid()
    grid_df.to_csv(GRID_OUT, index=False)
    print(f"Saved {len(grid_df)} rows to {GRID_OUT}")

    forecast_df = clean_block_forecast()
    forecast_df.to_csv(FORECAST_OUT, index=False)
    print(f"Saved {len(forecast_df)} rows to {FORECAST_OUT}")


if __name__ == "__main__":
    main()
