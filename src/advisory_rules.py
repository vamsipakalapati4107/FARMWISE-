"""Phase 4: rule-based agro-advisory engine.

generate_advisory(row) takes one forecast row (a dict or pandas Series with
rainfall_mm, temp_max_c, rh_max_pct) and returns a plain-language advisory
string. Thresholds are generic, not crop-specific (see PRD non-goals).

Run as a script to apply this to every row of gp_forecast_latest.csv and
save data/processed/gp_forecast_with_advisory.csv:
    python src/advisory_rules.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
FORECAST_FILE = PROCESSED_DIR / "gp_forecast_latest.csv"
OUT_FILE = PROCESSED_DIR / "gp_forecast_with_advisory.csv"

HEAVY_RAIN_THRESHOLD_MM = 20
HEAT_STRESS_THRESHOLD_C = 38
HUMID_RH_THRESHOLD_PCT = 85
HUMID_RAIN_THRESHOLD_MM = 5

HEAVY_RAIN_ADVISORY = "Heavy rain expected — delay spraying/harvest, ensure field drainage."
HEAT_STRESS_ADVISORY = "Heat stress risk — irrigate in early morning/evening, avoid midday fieldwork."
FUNGAL_RISK_ADVISORY = "High humidity + rain — monitor for fungal disease, consider preventive fungicide."
NORMAL_ADVISORY = "No significant weather risk — normal operations."


def generate_advisory(row) -> str:
    """row must support `.get(key)` (a dict or pandas Series)."""
    rainfall_mm = row.get("rainfall_mm")
    temp_max_c = row.get("temp_max_c")
    rh_max_pct = row.get("rh_max_pct")

    if pd.notna(rainfall_mm) and rainfall_mm > HEAVY_RAIN_THRESHOLD_MM:
        return HEAVY_RAIN_ADVISORY

    if pd.notna(temp_max_c) and temp_max_c > HEAT_STRESS_THRESHOLD_C:
        return HEAT_STRESS_ADVISORY

    if (
        pd.notna(rh_max_pct)
        and pd.notna(rainfall_mm)
        and rh_max_pct > HUMID_RH_THRESHOLD_PCT
        and rainfall_mm > HUMID_RAIN_THRESHOLD_MM
    ):
        return FUNGAL_RISK_ADVISORY

    return NORMAL_ADVISORY


def main() -> None:
    if not FORECAST_FILE.exists():
        sys.exit(f"Missing {FORECAST_FILE}. Run src/generate_gp_forecast.py first.")

    df = pd.read_csv(FORECAST_FILE)
    df["advisory"] = df.apply(generate_advisory, axis=1)
    df.to_csv(OUT_FILE, index=False)

    trigger_counts = df["advisory"].value_counts()
    print(f"Saved {len(df)} rows to {OUT_FILE}")
    print("\nAdvisory trigger counts:")
    print(trigger_counts.to_string())


if __name__ == "__main__":
    main()
