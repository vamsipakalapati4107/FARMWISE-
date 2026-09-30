"""Phase 6: end-to-end sanity checks that make the pipeline defensible in
front of judges -- confirms the spatial join has no unexpected gaps, the
forecast table has the right shape, and downscaling is actually happening
(not a pass-through copy of the raw block value).

Run from the project root:
    python src/validate_pipeline.py

Exits with status 1 if any check fails, so run_all.sh (or CI) can catch it.
Always writes reports/validation_report.md, whether checks pass or fail.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

TRAINING_TABLE_FILE = PROCESSED_DIR / "training_table.csv"
FORECAST_FILE = PROCESSED_DIR / "gp_forecast_with_advisory.csv"
BLOCK_FORECAST_FILE = PROCESSED_DIR / "block_forecast_clean.csv"
REPORT_FILE = REPORTS_DIR / "validation_report.md"

EXPECTED_GP_COUNT = 21
EXPECTED_FORECAST_DAYS = 5
NULL_THRESHOLD_PCT = 5.0
PASS_THROUGH_FAIL_THRESHOLD_PCT = 90.0
RAINFALL_TOLERANCE_MM = 1e-6

TRAINING_TABLE_KEY_COLUMNS = [
    "date",
    "gram_panchayat",
    "elevation_m",
    "distance_to_grid_cell_km",
    "grid_rainfall_mm",
    "gp_rainfall_mm",
    "gp_temp_max",
    "gp_temp_min",
    "gp_rh_max",
    "gp_rh_min",
    "gp_wind_max",
]


class Check:
    def __init__(self, name: str, passed: bool, details: str):
        self.name = name
        self.passed = passed
        self.details = details


def check_training_table_nulls() -> Check:
    if not TRAINING_TABLE_FILE.exists():
        return Check("Training table has no unexpected nulls", False, f"Missing {TRAINING_TABLE_FILE}")

    df = pd.read_csv(TRAINING_TABLE_FILE)
    lines = []
    all_ok = True
    for col in TRAINING_TABLE_KEY_COLUMNS:
        if col not in df.columns:
            lines.append(f"- `{col}`: MISSING COLUMN")
            all_ok = False
            continue
        pct_null = 100 * df[col].isna().mean()
        ok = pct_null <= NULL_THRESHOLD_PCT
        all_ok = all_ok and ok
        lines.append(f"- `{col}`: {pct_null:.2f}% null ({'OK' if ok else 'FAIL'}, threshold {NULL_THRESHOLD_PCT}%)")

    return Check("Training table has no unexpected nulls", all_ok, "\n".join(lines))


def check_forecast_shape() -> Check:
    if not FORECAST_FILE.exists():
        return Check("Forecast table is exactly 21 GPs x 5 days, no duplicates", False, f"Missing {FORECAST_FILE}")

    df = pd.read_csv(FORECAST_FILE)
    n_gps = df["gram_panchayat"].nunique()
    n_days = df["date"].nunique()
    n_rows = len(df)
    n_duplicates = int(df.duplicated(subset=["date", "gram_panchayat"]).sum())
    expected_rows = EXPECTED_GP_COUNT * EXPECTED_FORECAST_DAYS

    passed = (
        n_gps == EXPECTED_GP_COUNT
        and n_days == EXPECTED_FORECAST_DAYS
        and n_rows == expected_rows
        and n_duplicates == 0
    )

    details = (
        f"- GPs found: {n_gps} (expected {EXPECTED_GP_COUNT})\n"
        f"- Forecast days found: {n_days} (expected {EXPECTED_FORECAST_DAYS})\n"
        f"- Total rows: {n_rows} (expected {expected_rows})\n"
        f"- Duplicate (date, GP) rows: {n_duplicates}"
    )
    return Check("Forecast table is exactly 21 GPs x 5 days, no duplicates", passed, details)


def check_downscaling_is_real() -> Check:
    name = "Downscaled GP rainfall differs from the raw block forecast"
    if not FORECAST_FILE.exists():
        return Check(name, False, f"Missing {FORECAST_FILE}")
    if not BLOCK_FORECAST_FILE.exists():
        return Check(name, False, f"Missing {BLOCK_FORECAST_FILE}")

    forecast_df = pd.read_csv(FORECAST_FILE)
    block_df = pd.read_csv(BLOCK_FORECAST_FILE)[["date", "rainfall_mm"]].rename(
        columns={"rainfall_mm": "block_rainfall_mm"}
    )

    merged = forecast_df.merge(block_df, on="date", how="left")
    comparable = merged.dropna(subset=["rainfall_mm", "block_rainfall_mm"])
    if comparable.empty:
        return Check(name, False, "No rows had both a GP value and a matching block value to compare.")

    unchanged = (comparable["rainfall_mm"] - comparable["block_rainfall_mm"]).abs() <= RAINFALL_TOLERANCE_MM
    pct_unchanged = 100 * unchanged.mean()
    passed = pct_unchanged <= PASS_THROUGH_FAIL_THRESHOLD_PCT

    details = (
        f"- Rows compared: {len(comparable)}\n"
        f"- Unchanged from raw block value: {pct_unchanged:.1f}% "
        f"(fails if > {PASS_THROUGH_FAIL_THRESHOLD_PCT}%)"
    )
    return Check(name, passed, details)


def write_report(checks: list[Check]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    all_passed = all(c.passed for c in checks)

    lines = ["# Pipeline Validation Report", "", f"**Overall: {'PASS' if all_passed else 'FAIL'}**", ""]
    for check in checks:
        lines.append(f"## [{'PASS' if check.passed else 'FAIL'}] {check.name}")
        lines.append(check.details)
        lines.append("")

    REPORT_FILE.write_text("\n".join(lines))
    print(f"\nSaved validation report to {REPORT_FILE}")


def main() -> None:
    checks = [
        check_training_table_nulls(),
        check_forecast_shape(),
        check_downscaling_is_real(),
    ]

    for check in checks:
        print(f"\n[{'PASS' if check.passed else 'FAIL'}] {check.name}")
        print(check.details)

    write_report(checks)

    if not all(c.passed for c in checks):
        print("\nVALIDATION FAILED -- see reports/validation_report.md for details.")
        sys.exit(1)

    print("\nAll validation checks passed.")


if __name__ == "__main__":
    main()
