"""Phase 4: apply the trained downscaling model to the live block forecast
to produce a distinct 5-day forecast for each of the 21 Gram Panchayats.

Run from the project root:
    python src/generate_gp_forecast.py

Inputs:
    data/processed/block_forecast_clean.csv  (Phase 1)
    data/processed/training_table.csv        (Phase 2 -- source of per-GP
                                               elevation/distance, so this
                                               script never recomputes
                                               nearest-neighbor logic)
    models/downscaling_model.pkl             (Phase 3)

Output:
    data/processed/gp_forecast_latest.csv
        columns: date, gram_panchayat, rainfall_mm, temp_max_c, temp_min_c,
                 rh_max_pct, wind_max_kmh, confidence
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import pandas as pd

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

FORECAST_FILE = PROCESSED_DIR / "block_forecast_clean.csv"
TRAINING_TABLE_FILE = PROCESSED_DIR / "training_table.csv"
MODEL_FILE = MODELS_DIR / "downscaling_model.pkl"
OUT_FILE = PROCESSED_DIR / "gp_forecast_latest.csv"

# variable name -> column in block_forecast_clean.csv that stands in for
# the "coarse" input at inference time (in training this role was played by
# the historical IMD grid column of the same variable).
INFERENCE_INPUT_COLUMNS = {
    "rainfall": "rainfall_mm",
    "temp_max": "temp_max_c",
    "temp_min": "temp_min_c",
    "rh_max": "rh_max_pct",
    "rh_min": "rh_min_pct",
    "wind_max": "wind_speed_max_kmh",
}

# variable name -> column name in the Phase 4 output schema. rh_min is
# tracked internally but isn't part of the requested output columns.
OUTPUT_COLUMN_NAMES = {
    "rainfall": "rainfall_mm",
    "temp_max": "temp_max_c",
    "temp_min": "temp_min_c",
    "rh_max": "rh_max_pct",
    "wind_max": "wind_max_kmh",
}

OUTPUT_COLUMNS = [
    "date",
    "gram_panchayat",
    "rainfall_mm",
    "temp_max_c",
    "temp_min_c",
    "rh_max_pct",
    "wind_max_kmh",
    "confidence",
]


def load_gp_static_features() -> pd.DataFrame:
    """Per-GP elevation_m + distance_to_grid_cell_km, read back from Phase
    2's join rather than recomputed here."""
    if not TRAINING_TABLE_FILE.exists():
        sys.exit(f"Missing {TRAINING_TABLE_FILE}. Run src/build_training_table.py first.")

    table = pd.read_csv(TRAINING_TABLE_FILE)
    static = (
        table.groupby("gram_panchayat", as_index=False)
        .first()[["gram_panchayat", "elevation_m", "distance_to_grid_cell_km"]]
    )
    return static


def apply_correction(
    variable_bundle: dict,
    raw_value: float,
    elevation_m: float,
    distance_km: float,
    day_of_year: int,
    gp_name: str,
) -> float:
    best_method = variable_bundle["best_method"]

    if best_method == "delta":
        correction = variable_bundle["delta_corrections"].get(gp_name)
        if correction is None:
            return raw_value
        if correction["type"] == "additive":
            return raw_value + correction["value"]
        return raw_value * correction["value"]

    model = variable_bundle["rf_model"]
    feature_cols = variable_bundle["feature_cols"]
    feature_values = {
        variable_bundle["grid_col"]: raw_value,
        "elevation_m": elevation_m,
        "distance_to_grid_cell_km": distance_km,
        "day_of_year": day_of_year,
    }
    row = pd.DataFrame([feature_values])[feature_cols]
    return float(model.predict(row)[0])


def main() -> None:
    if not FORECAST_FILE.exists():
        sys.exit(f"Missing {FORECAST_FILE}. Run src/clean_grid_and_forecast.py first.")
    if not MODEL_FILE.exists():
        sys.exit(f"Missing {MODEL_FILE}. Run src/train_downscaling_model.py first.")

    forecast_df = pd.read_csv(FORECAST_FILE, parse_dates=["date"])
    bundle = joblib.load(MODEL_FILE)
    static_features = load_gp_static_features()

    median_distance = static_features["distance_to_grid_cell_km"].median()
    print(f"Median distance-to-grid-cell across {len(static_features)} GPs: {median_distance:.2f} km")

    rows = []
    for _, gp in static_features.iterrows():
        gp_name = gp["gram_panchayat"]
        distance_km = gp["distance_to_grid_cell_km"]
        confidence = "high" if pd.notna(distance_km) and distance_km < median_distance else "medium"
        print(f"  {gp_name}: distance={distance_km:.2f} km -> confidence={confidence}")

        for _, day in forecast_df.iterrows():
            day_of_year = pd.Timestamp(day["date"]).dayofyear
            out_row = {
                "date": pd.Timestamp(day["date"]).strftime("%Y-%m-%d"),
                "gram_panchayat": gp_name,
                "confidence": confidence,
            }

            for variable, input_col in INFERENCE_INPUT_COLUMNS.items():
                out_col = OUTPUT_COLUMN_NAMES.get(variable)
                if out_col is None:
                    continue

                if input_col not in forecast_df.columns or pd.isna(day.get(input_col)):
                    out_row[out_col] = None
                    continue

                raw_value = day[input_col]
                variable_bundle = bundle["variables"].get(variable)
                if variable_bundle is None:
                    # No trained model for this variable yet -- pass the
                    # block-level value through unchanged rather than
                    # inventing a correction.
                    out_row[out_col] = raw_value
                else:
                    out_row[out_col] = apply_correction(
                        variable_bundle, raw_value, gp["elevation_m"], distance_km, day_of_year, gp_name
                    )

            rows.append(out_row)

    result = pd.DataFrame(rows)
    for col in OUTPUT_COLUMNS:
        if col not in result.columns:
            result[col] = None
    result = result[OUTPUT_COLUMNS].sort_values(["date", "gram_panchayat"]).reset_index(drop=True)

    result.to_csv(OUT_FILE, index=False)
    print(
        f"\nSaved {len(result)} rows ({result['gram_panchayat'].nunique()} GPs x "
        f"{result['date'].nunique()} days) to {OUT_FILE}"
    )


if __name__ == "__main__":
    main()
