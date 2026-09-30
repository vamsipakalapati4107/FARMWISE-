"""Phase 2: quick visual sanity check that grid rainfall and GP proxy
rainfall are correlated but not identical (i.e. downscaling has signal to
learn from, not just noise).

Usage:
    python src/plot_sanity_check.py                  # picks the first GP
    python src/plot_sanity_check.py "Sathupally"      # picks a specific GP
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
TABLE_FILE = PROCESSED_DIR / "training_table.csv"


def main() -> None:
    if not TABLE_FILE.exists():
        sys.exit(f"Missing {TABLE_FILE}. Run src/build_training_table.py first.")

    df = pd.read_csv(TABLE_FILE)

    gp_name = sys.argv[1] if len(sys.argv) > 1 else df["gram_panchayat"].iloc[0]
    gp_df = df[df["gram_panchayat"] == gp_name]
    if gp_df.empty:
        sys.exit(f"No rows found for GP '{gp_name}'. Available: {sorted(df['gram_panchayat'].unique())}")

    correlation = gp_df["grid_rainfall_mm"].corr(gp_df["gp_rainfall_mm"])

    plt.figure(figsize=(6, 6))
    plt.scatter(gp_df["grid_rainfall_mm"], gp_df["gp_rainfall_mm"], alpha=0.5, s=15)
    max_val = max(gp_df["grid_rainfall_mm"].max(), gp_df["gp_rainfall_mm"].max())
    plt.plot([0, max_val], [0, max_val], linestyle="--", color="gray", label="y = x")
    plt.xlabel("Grid rainfall (mm) -- coarse IMD cell")
    plt.ylabel("GP proxy rainfall (mm) -- ERA5-Land")
    plt.title(f"{gp_name}: grid vs. GP rainfall (r = {correlation:.2f})")
    plt.legend()
    plt.tight_layout()

    out_path = PROCESSED_DIR / f"sanity_check_{gp_name.replace(' ', '_')}.png"
    plt.savefig(out_path, dpi=150)
    print(f"Saved plot to {out_path}")
    print(f"Correlation (grid vs. GP rainfall) for {gp_name}: {correlation:.3f}")

    plt.show()


if __name__ == "__main__":
    main()
