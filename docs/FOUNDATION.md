# Phase 0.5 — ML + Data Foundation

This document is the single source of truth for "what is actually ML in
FarmWise" and what changed in this foundation phase. The machine-readable
version of section A lives in `src/ml_audit.py` and is served at
`GET /ml/models` — this document and that endpoint are generated from the
same data and cannot drift apart.

## A. What ML currently exists

**Exactly one real, trained ML model exists: rainfall downscaling.**

- **Model**: `RandomForestRegressor` (scikit-learn), trained in
  `src/train_downscaling_model.py`, saved to `models/downscaling_model.pkl`.
- **Input features**: `grid_rainfall_mm`, `elevation_m`,
  `distance_to_grid_cell_km`, `day_of_year`.
- **Output**: `gp_rainfall_mm` — one 5-day forecast value per Gram Panchayat.
- **Chosen over** a per-GP delta/ratio bias correction by lower test-set MAE
  (0.225mm vs 1.79mm — see `models/training_report.md`).
- **Training data**: 2025 IMD-style rainfall grid (28 cells) as input,
  ERA5-Land reanalysis (Open-Meteo Archive API) per-GP rainfall as the
  target/proxy ground truth. Train split Jan–Oct 2025, test split Nov–Dec 2025.

## B. What is NOT ML yet (and must never be called ML)

| Component | What it actually is |
|---|---|
| Temperature (max/min), humidity, wind | **Pass-through**. The block-level forecast value is copied unchanged into every GP's row. No model exists because the real IMD grid has no gridded ground truth for these variables to train against (`VARIABLE_SPECS` in `train_downscaling_model.py` skips them automatically). |
| Hourly-estimated temperature curve | **Deterministic formula** (fixed diurnal cosine shape), not learned. Always flagged `estimated: true` in the API response. |
| Weather advisory (`advisory_rules.py`) | **Rule-based** — explicit if/elif thresholds, deliberately not ML (documented design choice: explainability over black-box models). |
| Crop-stage advisory (`crop_advisory_rules.py`) | **Rule-based** — the generic rules above, extended with a (condition, crop, stage) → action lookup table. |
| Within-GP spatial estimate (`src/spatial.py`, new this phase) | **Rule-based geometry** — inverse-distance weighting (IDW) over the nearest 3 GP centroids. Not a trained model, and never presented as one — every response carries `"source": "estimated_downscaled"` plus full provenance (which GPs, distances, weights). |
| GP centroid coordinates | **17 of 21 are raw geocoding results** (Nominatim API, spot-checked to fall within ~16km of the block cluster). **4 are estimated** (Cherukupalli, Yatalakunta, Kistapuram, Kistaram) via LGD village-code adjacency, because geocoding failed or returned wrong-district matches — see `README.md`. |

Full machine-readable classification: `GET /ml/models` (backed by `src/ml_audit.py`).

## C. Current spatial resolution

**Gram Panchayat (GP) level — 21 fixed points.** This was true before this
phase and remains true after it. Nothing in this phase changes the trained
model's resolution.

What *does* change: farms/plots can now optionally carry their own
lat/lon. When they do, the API layers a **rule-based spatial estimate**
(IDW over the nearest 3 GP centroids) on top of the GP-level model output:

```
GP-level prediction (21 fixed points, from the trained RF model)
        |
farm/plot coordinates (if configured)
        |
inverse-distance weighting (src/spatial.py) -- RULE-BASED, not ML
        |
farm/plot ESTIMATE -- always labeled "estimated_downscaled", with
                      full provenance (GPs used, distances, weights)
```

This is **not genuine plot-level ML**. It is a spatial interpolation of an
already-GP-level prediction. See section G for what would actually be
needed to train a genuine plot-level model.

IDW is applied to rainfall only (the one variable with real GP-to-GP
signal from the trained model). It is deliberately **not** applied to
temperature/humidity/wind, because those are identical pass-through values
across all 21 GPs — interpolating between 21 copies of the same number
would misleadingly imply spatial variation that doesn't exist.

## D. Current data sources

- `data/raw/khammam_2025_rainfall_grid.csv` — real IMD-style rainfall grid, 28 cells × 365 days, rainfall only.
- `data/raw/sathupally_block_forecast.csv` — real 5-day block-level forecast (rainfall, temp, RH, wind).
- `data/raw/Sathupalli_Khammam_LGD_Village_GramPanchayat_Mapping.csv` — real LGD mapping, 21 GPs.
- `data/processed/gp_centroids.csv` — GP lat/lon/elevation (see caveat in section B).
- `data/processed/panchayat_weather/*.csv` — 2025 daily ERA5-Land reanalysis per GP (proxy ground truth for training).
- `src/crop_catalog.py` — static reference catalog (7 crops, varieties, stages) — reference data, not weather/geo data.
- User-entered Farm/Plot/Crop records — real, stored in `data/app.db`.

## E. Database changes (this phase)

No destructive changes. `data/app.db` was never deleted; all pre-existing
rows were verified byte-for-byte preserved by row count before/after
migration (2 users, 3 farms, 3 crops, 4 notifications, all preserved).

**New/changed columns** (all nullable, additive only):

| Table | Change |
|---|---|
| `farms` | + `latitude`, `longitude`, `boundary_geojson`, `location_name` (all null on pre-existing rows — never invented) |
| `crops` | + `plot_id` (nullable FK to `plots.id` — pre-existing crops keep `plot_id = NULL`, still work via `farm_id` exactly as before) |
| `plots` (new table) | `id`, `farm_id`, `name`, `latitude`, `longitude`, `boundary_geojson`, `area_value`, `area_unit`, `created_at` |

**Migration mechanism**: `src/migrate_db.py` — no Alembic (disproportionate
for a handful of nullable-column additions on a single-file SQLite dev
database). Instead, a small idempotent script that:
1. Checks existing columns via `PRAGMA table_info` before adding any.
2. Only ever runs `ALTER TABLE ... ADD COLUMN` (never drops/recreates).
3. Creates new tables via `Base.metadata.create_all()`, which also never
   touches existing tables.
4. Runs automatically at API startup (`db.init_db()`) and is safe to run
   repeatedly — a no-op once applied.

Run standalone: `python src/migrate_db.py`.

## F. Prediction pipeline (data flow)

```
RAW DATA                    ML PREDICTION              DERIVED RISK           RECOMMENDATION
--------                    -------------              ------------           --------------
IMD rainfall grid      ->   Random Forest         ->    threshold rules   ->   advisory sentence
ERA5-Land proxy             (rainfall_mm, GP-level)     (heavy rain /          (what/why/action)
                                  |                      heat / fungal)
                                  v
                             IDW spatial estimate   (RULE-BASED, not ML;
                             (if plot has coords)     only applied to rainfall)

Block forecast          ->  PASS-THROUGH          ->    (same threshold   ->   (same advisory
(temp/RH/wind)               (no model)                  rules, using          pipeline)
                                                          pass-through values)
```

Endpoints exposing each stage explicitly:
- Raw/ML: `GET /plots/{id}/ml-predictions` (per-variable classification)
- Derived risk: `GET /plots/{id}/risk`, `GET /alerts`
- Recommendation: `GET /plots/{id}/advisory`, `GET /farms/{id}/crop-advisory`

## G. What needs retraining/building for genuine plot-level ML

1. **Per-plot covariates**: the current model's features
   (`elevation_m`, `distance_to_grid_cell_km`) are GP-level constants.
   Genuine plot-level prediction needs these computed per plot coordinate
   (elevation lookup at the plot's exact lat/lon; distance from the plot,
   not the GP centroid, to the nearest grid cell).
2. **Finer training signal**: ERA5-Land reanalysis (the current proxy
   ground truth) is itself a ~9-11km grid product — it cannot supervise a
   model to predict genuine sub-GP variation, because its own resolution
   is coarser than or comparable to the distance between neighboring GPs.
   A genuinely finer product (higher-res reanalysis, or real station data)
   would be needed as ground truth.
3. **Temp/RH/wind models**: would need a gridded (not single-point) source
   for these variables, analogous to the rainfall grid, before any model
   can be trained for them at all.
4. **Crop health**: no satellite/NDVI/remote-sensing data source exists in
   this project. `GET /plots/{id}/health` is an honest stub
   (`available: false`) rather than a fabricated score.
