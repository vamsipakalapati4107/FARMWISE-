"""Phase 0.5, item 3: machine-readable ML audit -- the single source of
truth for "what is actually ML here" that both docs/FOUNDATION.md and the
/ml/models API endpoint are generated from, so the documentation and the
API can never drift apart.

Classification is restricted to exactly four buckets (no fabricated
in-between categories):
    REAL_ML_PREDICTION | RULE_BASED_LOGIC | RAW_DATA_API_VALUE | PASS_THROUGH_VALUE
"""
from __future__ import annotations

REAL_ML_PREDICTION = "REAL_ML_PREDICTION"
RULE_BASED_LOGIC = "RULE_BASED_LOGIC"
RAW_DATA_API_VALUE = "RAW_DATA_API_VALUE"
PASS_THROUGH_VALUE = "PASS_THROUGH_VALUE"

ML_AUDIT: list[dict] = [
    {
        "component": "rainfall_downscaling_model",
        "display_name": "Rainfall GP-level Downscaling Model (Random Forest)",
        "classification": REAL_ML_PREDICTION,
        "input_features": ["grid_rainfall_mm", "elevation_m", "distance_to_grid_cell_km", "day_of_year"],
        "output": "gp_rainfall_mm (5-day forecast, per Gram Panchayat)",
        "training_data": (
            "2025 IMD-style rainfall grid (28 cells, data/raw/khammam_2025_rainfall_grid.csv) "
            "as input, ERA5-Land reanalysis proxy per-GP rainfall "
            "(data/processed/panchayat_weather/*.csv) as target. "
            "Train: 2025-01-01..2025-10-31, Test: 2025-11-01..2025-12-31."
        ),
        "spatial_resolution": "21 fixed Gram Panchayat points (GP-level). NOT plot-level.",
        "temporal_resolution": "Daily",
        "model_type": "RandomForestRegressor (scikit-learn), chosen over a per-GP delta/ratio "
        "correction by lower test-set MAE (0.225mm vs 1.79mm) -- see models/training_report.md",
        "how_loaded": "joblib.load() -- but only by the offline batch script "
        "src/generate_gp_forecast.py, run manually/via run_all.sh. The live API does NOT "
        "load or call this model; it only reads the static CSV the batch script produced.",
        "how_predictions_generated": "Offline: generate_gp_forecast.py calls model.predict() once "
        "per run and writes data/processed/gp_forecast_latest.csv. The API's "
        "/forecast, /weather/current, /alerts etc. endpoints read that file -- no live inference.",
    },
    {
        "component": "temp_rh_wind_forecast",
        "display_name": "Temperature / Humidity / Wind per-GP values",
        "classification": PASS_THROUGH_VALUE,
        "input_features": ["sathupally_block_forecast.csv (single block-level value per day)"],
        "output": "temp_max_c, temp_min_c, rh_max_pct, wind_max_kmh -- identical across all 21 GPs",
        "training_data": "None -- no model exists for these variables.",
        "spatial_resolution": "Block-level (1 point for the whole Sathupally block), copied to all 21 GPs unchanged.",
        "temporal_resolution": "Daily",
        "model_type": "N/A -- no model. VARIABLE_SPECS in train_downscaling_model.py skips these "
        "because the real IMD grid has no gridded ground truth for them to train against.",
        "how_loaded": "N/A",
        "how_predictions_generated": "generate_gp_forecast.py copies the raw block forecast value "
        "for each variable into every GP's row, unchanged.",
    },
    {
        "component": "hourly_estimated_temperature",
        "display_name": "Hourly-estimated temperature curve",
        "classification": RULE_BASED_LOGIC,
        "input_features": ["temp_min_c", "temp_max_c (that day's real values)"],
        "output": "24 hourly temp_c points, each flagged estimated: true",
        "training_data": "None -- deterministic formula, not learned.",
        "spatial_resolution": "Same as the underlying daily GP-level value.",
        "temporal_resolution": "Hourly (interpolated, not observed)",
        "model_type": "Fixed diurnal cosine formula (peak ~15:00, trough ~03:00) -- a hand-written "
        "mathematical rule, not a risk-threshold rule and not a trained model.",
        "how_loaded": "N/A -- pure function, src/routers/weather.py",
        "how_predictions_generated": "Computed synchronously per request from that day's real min/max.",
    },
    {
        "component": "weather_advisory_rules",
        "display_name": "Weather advisory rules (generic)",
        "classification": RULE_BASED_LOGIC,
        "input_features": ["rainfall_mm", "temp_max_c", "rh_max_pct"],
        "output": "Advisory sentence + severity (critical/warning/safe)",
        "training_data": "None -- explicit hand-set thresholds (src/advisory_rules.py).",
        "spatial_resolution": "Same as the underlying GP-level forecast row.",
        "temporal_resolution": "Daily",
        "model_type": "If/elif threshold rules, deliberately not ML (documented design choice: "
        "explainability over black-box models).",
        "how_loaded": "N/A -- pure function",
        "how_predictions_generated": "Evaluated per request in src/routers/alerts.py.",
    },
    {
        "component": "crop_stage_advisory_rules",
        "display_name": "Crop-and-stage-aware advisory rules",
        "classification": RULE_BASED_LOGIC,
        "input_features": ["rainfall_mm", "temp_max_c", "rh_max_pct", "crop_name", "growth_stage"],
        "output": "Crop-specific advisory sentence + severity",
        "training_data": "None -- explicit override table (src/crop_advisory_rules.py).",
        "spatial_resolution": "Same as the underlying GP-level forecast row.",
        "temporal_resolution": "Daily",
        "model_type": "Threshold rules + a (condition, crop, stage) -> action lookup table.",
        "how_loaded": "N/A -- pure function",
        "how_predictions_generated": "Evaluated per request in src/routers/crop_advisory.py.",
    },
    {
        "component": "gp_plot_spatial_estimate",
        "display_name": "Within-GP spatial estimate (Phase 0.5, new)",
        "classification": RULE_BASED_LOGIC,
        "input_features": ["plot/farm latitude+longitude", "nearest GP centroids' forecast values"],
        "output": "An ESTIMATED value at a farm/plot's coordinates -- explicitly labeled "
        "'estimated_downscaled', never presented as a plot-trained ML prediction.",
        "training_data": "None -- inverse-distance weighting (IDW) over the nearest 3 GP centroids.",
        "spatial_resolution": "Interpolated between GP points; still bounded by the same 21-point "
        "GP-level source data. This is NOT genuine plot-level ML -- see docs/FOUNDATION.md.",
        "temporal_resolution": "Same as the underlying GP-level forecast row.",
        "model_type": "Deterministic geometric formula (src/spatial.py), not learned.",
        "how_loaded": "N/A -- pure function",
        "how_predictions_generated": "Computed synchronously per request when a plot has coordinates.",
    },
    {
        "component": "gp_centroids_geocoding",
        "display_name": "GP centroid coordinates",
        "classification": RAW_DATA_API_VALUE,
        "input_features": ["GP name + district/state"],
        "output": "latitude, longitude, elevation_m",
        "training_data": "N/A",
        "spatial_resolution": "21 Gram Panchayat points",
        "temporal_resolution": "Static (geocoded once)",
        "model_type": "N/A -- 17 of 21 are real Nominatim geocoding results (verified within ~16km "
        "of the block cluster); 4 (Cherukupalli, Yatalakunta, Kistapuram, Kistaram) are "
        "estimated via LGD village-code adjacency because geocoding failed or returned "
        "wrong-district matches -- see README.md 'Known limitations'.",
        "how_loaded": "Read from data/processed/gp_centroids.csv at API startup.",
        "how_predictions_generated": "N/A -- not a prediction, a one-time geocoding lookup.",
    },
]


def get_audit() -> list[dict]:
    return ML_AUDIT


def get_component(name: str) -> dict | None:
    return next((c for c in ML_AUDIT if c["component"] == name), None)
