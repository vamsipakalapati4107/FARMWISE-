#!/usr/bin/env bash
# Reproduces the full pipeline end to end, from raw data to a validated
# GP-level forecast + advisory table. Run from anywhere; paths are
# resolved relative to this script's location.
set -euo pipefail
cd "$(dirname "$0")"

echo "== Phase 1: fetch ground truth (geocode, elevation, proxy weather) =="
python src/fetch_ground_truth.py

echo "== Phase 1: clean IMD grid + block forecast =="
python src/clean_grid_and_forecast.py

echo "== Phase 2: build training table (spatial join) =="
python src/build_training_table.py

echo "== Phase 3: train downscaling model =="
python src/train_downscaling_model.py

echo "== Phase 4: generate GP-level forecast =="
python src/generate_gp_forecast.py

echo "== Phase 4: apply advisory rules =="
python src/advisory_rules.py

echo "== Phase 6: validate pipeline =="
python src/validate_pipeline.py

echo
echo "Pipeline complete. Start the API with: uvicorn src.api:app --reload"
