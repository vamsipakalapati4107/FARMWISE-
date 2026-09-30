# Pipeline Validation Report

**Overall: PASS**

## [PASS] Training table has no unexpected nulls
- `date`: 0.00% null (OK, threshold 5.0%)
- `gram_panchayat`: 0.00% null (OK, threshold 5.0%)
- `elevation_m`: 0.00% null (OK, threshold 5.0%)
- `distance_to_grid_cell_km`: 0.00% null (OK, threshold 5.0%)
- `grid_rainfall_mm`: 0.00% null (OK, threshold 5.0%)
- `gp_rainfall_mm`: 0.00% null (OK, threshold 5.0%)
- `gp_temp_max`: 0.00% null (OK, threshold 5.0%)
- `gp_temp_min`: 0.00% null (OK, threshold 5.0%)
- `gp_rh_max`: 0.00% null (OK, threshold 5.0%)
- `gp_rh_min`: 0.00% null (OK, threshold 5.0%)
- `gp_wind_max`: 0.00% null (OK, threshold 5.0%)

## [PASS] Forecast table is exactly 21 GPs x 5 days, no duplicates
- GPs found: 21 (expected 21)
- Forecast days found: 5 (expected 5)
- Total rows: 105 (expected 105)
- Duplicate (date, GP) rows: 0

## [PASS] Downscaled GP rainfall differs from the raw block forecast
- Rows compared: 105
- Unchanged from raw block value: 0.0% (fails if > 90.0%)
