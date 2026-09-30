"""Phase 3: downscaling model training.

For each weather variable that has both a coarse ("grid") and proxy
ground-truth ("gp") column in the training table, fits and compares two
approaches:
  a) Delta/ratio method   -- per-GP additive or multiplicative bias
                              correction (whichever fits better in-sample).
  b) Random Forest        -- one pooled model per variable, using
                              [grid_value, elevation_m, distance_to_grid_cell_km,
                              day_of_year] to predict the GP value.

Both are evaluated on a Jan-Oct 2025 train / Nov-Dec 2025 test split, with
per-GP and overall MAE/RMSE. Everything is saved to models/downscaling_model.pkl
(via joblib) plus a human-readable models/training_report.md.

New variables (temp, RH, wind) are picked up automatically as soon as a
matching grid_<var> column appears in training_table.csv -- see
VARIABLE_SPECS below.

Run from the project root:
    python src/train_downscaling_model.py
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
TABLE_FILE = PROCESSED_DIR / "training_table.csv"
MODEL_FILE = MODELS_DIR / "downscaling_model.pkl"
REPORT_FILE = MODELS_DIR / "training_report.md"

TRAIN_END = "2025-10-31"
TEST_START = "2025-11-01"

# variable name -> (grid column, gp/target column). Only variables whose
# grid column actually exists in training_table.csv get a model -- today
# that's rainfall only, since the IMD grid is rainfall-only. Add a row here
# (and the matching grid_<var> column upstream) to bring temp/RH/wind online
# later without touching the rest of this file.
VARIABLE_SPECS = {
    "rainfall": ("grid_rainfall_mm", "gp_rainfall_mm"),
    "temp_max": ("grid_temp_max", "gp_temp_max"),
    "temp_min": ("grid_temp_min", "gp_temp_min"),
    "rh_max": ("grid_rh_max", "gp_rh_max"),
    "rh_min": ("grid_rh_min", "gp_rh_min"),
    "wind_max": ("grid_wind_max", "gp_wind_max"),
}

RF_PARAMS = dict(n_estimators=200, random_state=42, n_jobs=-1)
MIN_NONZERO_DAYS_FOR_RATIO = 5


def rmse(y_true, y_pred) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def compute_delta_correction(train_df: pd.DataFrame, grid_col: str, gp_col: str) -> dict | None:
    """Fit the best of an additive or multiplicative bias correction for one GP."""
    valid = train_df.dropna(subset=[grid_col, gp_col])
    if valid.empty:
        return None

    additive_delta = float((valid[gp_col] - valid[grid_col]).mean())
    candidates = {"additive": valid[grid_col] + additive_delta}

    nonzero = valid[valid[grid_col] > 1e-6]
    if len(nonzero) >= MIN_NONZERO_DAYS_FOR_RATIO:
        ratio = float((nonzero[gp_col] / nonzero[grid_col]).mean())
        candidates["multiplicative"] = valid[grid_col] * ratio
    else:
        ratio = None

    best_type, best_mae = "additive", mean_absolute_error(valid[gp_col], candidates["additive"])
    if "multiplicative" in candidates:
        mult_mae = mean_absolute_error(valid[gp_col], candidates["multiplicative"])
        if mult_mae < best_mae:
            best_type, best_mae = "multiplicative", mult_mae

    value = additive_delta if best_type == "additive" else ratio
    return {"type": best_type, "value": value}


def apply_delta_correction(test_df: pd.DataFrame, grid_col: str, correction: dict | None) -> pd.Series:
    if correction is None:
        return pd.Series(np.nan, index=test_df.index)
    if correction["type"] == "additive":
        return test_df[grid_col] + correction["value"]
    return test_df[grid_col] * correction["value"]


def evaluate(y_true: pd.Series, y_pred: pd.Series) -> tuple[float, float] | tuple[None, None]:
    mask = y_true.notna() & y_pred.notna()
    if mask.sum() == 0:
        return None, None
    return mean_absolute_error(y_true[mask], y_pred[mask]), rmse(y_true[mask], y_pred[mask])


def train_variable(df: pd.DataFrame, variable: str, grid_col: str, gp_col: str) -> dict:
    print(f"\n=== {variable} ({grid_col} -> {gp_col}) ===")
    train_df = df[df["date"] <= TRAIN_END].copy()
    test_df = df[df["date"] >= TEST_START].copy()

    # --- Delta/ratio method, fit per GP on the train split ---
    delta_corrections: dict[str, dict] = {}
    delta_rows = []
    delta_test_preds = pd.Series(index=test_df.index, dtype=float)

    for gp_name, gp_train in train_df.groupby("gram_panchayat"):
        correction = compute_delta_correction(gp_train, grid_col, gp_col)
        if correction is not None:
            delta_corrections[gp_name] = correction

        gp_test = test_df[test_df["gram_panchayat"] == gp_name]
        preds = apply_delta_correction(gp_test, grid_col, correction)
        delta_test_preds.loc[gp_test.index] = preds

        mae, rmse_val = evaluate(gp_test[gp_col], preds)
        delta_rows.append({"gram_panchayat": gp_name, "delta_mae": mae, "delta_rmse": rmse_val})

    delta_overall_mae, delta_overall_rmse = evaluate(test_df[gp_col], delta_test_preds)

    # --- Random Forest, one pooled model per variable ---
    feature_cols = [grid_col, "elevation_m", "distance_to_grid_cell_km", "day_of_year"]
    rf_train = train_df.dropna(subset=feature_cols + [gp_col])
    rf_test = test_df.dropna(subset=feature_cols)

    rf_model = None
    rf_rows = []
    rf_overall_mae = rf_overall_rmse = None

    if len(rf_train) >= 10 and not rf_test.empty:
        rf_model = RandomForestRegressor(**RF_PARAMS)
        rf_model.fit(rf_train[feature_cols], rf_train[gp_col])

        rf_preds = pd.Series(rf_model.predict(rf_test[feature_cols]), index=rf_test.index)
        rf_overall_mae, rf_overall_rmse = evaluate(test_df.loc[rf_test.index, gp_col], rf_preds)

        for gp_name, gp_test in rf_test.groupby(test_df.loc[rf_test.index, "gram_panchayat"]):
            preds = rf_preds.loc[gp_test.index]
            mae, rmse_val = evaluate(test_df.loc[gp_test.index, gp_col], preds)
            rf_rows.append({"gram_panchayat": gp_name, "rf_mae": mae, "rf_rmse": rmse_val})
    else:
        print(f"  Skipping Random Forest for {variable}: not enough rows (train={len(rf_train)}, test={len(rf_test)})")

    per_gp_report = pd.merge(
        pd.DataFrame(delta_rows), pd.DataFrame(rf_rows) if rf_rows else pd.DataFrame(columns=["gram_panchayat"]),
        on="gram_panchayat", how="outer",
    ).sort_values("gram_panchayat")

    print(per_gp_report.to_string(index=False))
    print(f"  OVERALL  delta: MAE={delta_overall_mae}, RMSE={delta_overall_rmse}")
    print(f"  OVERALL  rf:    MAE={rf_overall_mae}, RMSE={rf_overall_rmse}")

    best_method = "random_forest" if (
        rf_overall_mae is not None and (delta_overall_mae is None or rf_overall_mae < delta_overall_mae)
    ) else "delta"

    return {
        "variable": variable,
        "grid_col": grid_col,
        "gp_col": gp_col,
        "feature_cols": feature_cols,
        "delta_corrections": delta_corrections,
        "delta_overall_mae": delta_overall_mae,
        "delta_overall_rmse": delta_overall_rmse,
        "rf_model": rf_model,
        "rf_overall_mae": rf_overall_mae,
        "rf_overall_rmse": rf_overall_rmse,
        "best_method": best_method,
        "per_gp_report": per_gp_report,
    }


def write_report(results: list[dict]) -> None:
    lines = ["# Downscaling Model -- Training Report", ""]
    lines.append(f"Train period: 2025-01-01 to {TRAIN_END}  |  Test period: {TEST_START} to 2025-12-31")
    lines.append("")

    for r in results:
        lines.append(f"## {r['variable']}")
        lines.append(f"- Grid column: `{r['grid_col']}`  |  GP column: `{r['gp_col']}`")
        lines.append(
            f"- Overall test MAE/RMSE -- delta: {r['delta_overall_mae']:.3f} / {r['delta_overall_rmse']:.3f}"
            if r["delta_overall_mae"] is not None else "- Overall test MAE/RMSE -- delta: n/a"
        )
        lines.append(
            f"- Overall test MAE/RMSE -- random forest: {r['rf_overall_mae']:.3f} / {r['rf_overall_rmse']:.3f}"
            if r["rf_overall_mae"] is not None else "- Overall test MAE/RMSE -- random forest: n/a"
        )
        lines.append(f"- **Best method: {r['best_method']}**")
        lines.append("")
        lines.append(r["per_gp_report"].to_markdown(index=False))
        lines.append("")

    REPORT_FILE.write_text("\n".join(lines))
    print(f"\nSaved training report to {REPORT_FILE}")


def main() -> None:
    if not TABLE_FILE.exists():
        raise SystemExit(f"Missing {TABLE_FILE}. Run src/build_training_table.py first.")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(TABLE_FILE, parse_dates=["date"])
    df["day_of_year"] = df["date"].dt.dayofyear
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    results = []
    for variable, (grid_col, gp_col) in VARIABLE_SPECS.items():
        if grid_col not in df.columns:
            print(f"\n=== {variable} ===\n  Skipping: no '{grid_col}' column in training_table.csv yet.")
            continue
        results.append(train_variable(df, variable, grid_col, gp_col))

    if not results:
        raise SystemExit("No variables had a matching grid column -- nothing to train.")

    model_bundle = {
        "trained_at": dt.datetime.now().isoformat(),
        "train_end": TRAIN_END,
        "test_start": TEST_START,
        "variables": {
            r["variable"]: {
                "grid_col": r["grid_col"],
                "gp_col": r["gp_col"],
                "feature_cols": r["feature_cols"],
                "delta_corrections": r["delta_corrections"],
                "rf_model": r["rf_model"],
                "best_method": r["best_method"],
                "delta_overall_mae": r["delta_overall_mae"],
                "rf_overall_mae": r["rf_overall_mae"],
            }
            for r in results
        },
    }
    joblib.dump(model_bundle, MODEL_FILE)
    print(f"\nSaved model bundle to {MODEL_FILE}")

    write_report(results)


if __name__ == "__main__":
    main()
