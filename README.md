# Panchayat Downscaling (SIH 26074)

## Problem statement

IMD/MoES currently issues weather forecasts at Block/Mandal resolution, but
farmers need advisories at Gram Panchayat (GP) resolution. This project
downscales the Sathupally block-level 5-day forecast into a distinct,
explainable forecast for each of its 21 Gram Panchayats, and turns each
GP's forecast into a plain-language agro-advisory (e.g. delay
spraying/harvest ahead of heavy rain, irrigate early to avoid heat stress,
watch for fungal risk under high humidity + rain).

The goal is a **defensible method**, not certified meteorological
accuracy: every downscaled value should be explainable in terms of
elevation, distance to the nearest coarse grid cell, and historical bias
— not a black box.

## Data sources (and the proxy-ground-truth caveat)

| Dataset | Source | Role |
|---|---|---|
| IMD 0.25° gridded rainfall, 2025 | IMD | Coarse historical rainfall input |
| Sathupally block forecast | Provided/mock | Live 5-day forecast to be downscaled |
| LGD village/GP mapping | LGD | GP list + join keys |
| GP centroids + elevation | Nominatim + Open-Meteo Elevation | Generated in Phase 1 |
| Panchayat-level historical weather, 2025 | Open-Meteo Historical Weather Archive (ERA5-Land) | **Proxy** panchayat ground truth |
| Telangana district boundaries (33 districts, 2016) | [udit-001/india-maps-data](https://github.com/udit-001/india-maps-data) | State-wide district picker + choropleth (`webapp/public/data/telangana_districts.geojson`) |
| Khammam-area mandal names | [gggodhwani/telangana_boundaries](https://github.com/gggodhwani/telangana_boundaries) | Block/Mandal picker level; uses pre-2016 Khammam boundary, so a few listed mandals (e.g. Bhadrachalam, Manuguru) are now in Bhadradri Kothagudem district -- see `webapp/src/lib/telanganaLocations.ts` |

**Important:** there is no real GP-level weather station network for
Sathupally. "GP ground truth" in this project is ERA5-Land reanalysis
(~9-11 km resolution) sampled at each GP's centroid — a defensible,
clearly-labelled stand-in, not a physical observation. The downscaling
method itself (spatial join + bias correction, validated against this
proxy) is what's being demonstrated, not proxy-free accuracy.

## Architecture

```
Raw data (IMD grid, block forecast, LGD mapping)
        |
Phase 1: geocode GPs, pull elevation + proxy ground truth, clean grid/forecast
        |
Phase 2: spatial join -- nearest grid cell per GP, build training table
        |
Phase 3: downscaling model -- per-GP bias correction (delta method) vs.
         pooled Random Forest (elevation + distance + day-of-year), trained
         on the 2025 grid-vs-proxy overlap
        |
Phase 4: apply best model to the live block forecast -> GP forecast,
         then rule-based advisory engine
        |
Phase 5: FastAPI + single-file dashboard
        |
Phase 6: validation checks + one-command reproduction
```

Config lives in the per-variable specs at the top of
`src/train_downscaling_model.py` and `src/generate_gp_forecast.py` --
adding a new weather variable (once its grid counterpart exists) or a
second Block does not require restructuring the pipeline.

## How to run

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Drop the raw source files into `data/raw/`, then reproduce the whole
pipeline with one command:

```bash
./run_all.sh
```

This runs, in order: `fetch_ground_truth.py` -> `clean_grid_and_forecast.py`
-> `build_training_table.py` -> `train_downscaling_model.py` ->
`generate_gp_forecast.py` -> `advisory_rules.py` -> `validate_pipeline.py`,
and stops immediately (non-zero exit) if any validation check fails. See
`reports/validation_report.md` afterwards for the pass/fail summary.

Or run phases individually -- see each script's docstring for its exact
inputs/outputs:

```bash
python src/fetch_ground_truth.py
python src/clean_grid_and_forecast.py
python src/build_training_table.py
python src/plot_sanity_check.py          # optional: eyeball grid vs. GP rainfall
python src/train_downscaling_model.py
python src/generate_gp_forecast.py
python src/advisory_rules.py
python src/validate_pipeline.py
```

Tests: `pytest tests/`

### API + Dashboard

```bash
uvicorn src.api:app --reload
```

Serves `http://localhost:8000` with `GET /gps`, `GET /forecast`, and
`GET /forecast/{gp_name}`. Then open `frontend/index.html` directly in a
browser (or serve it statically, e.g.
`python -m http.server --directory frontend 8080`). Edit the `API_BASE`
constant near the top of `frontend/index.html` if the API runs on a
different host/port.

## Demo script (~1 minute, the core idea)

Show the raw block forecast -- **one** rainfall/temp/RH/wind value for the
whole Sathupally block -- side by side with the dashboard's 21
differentiated GP values for that same day. That contrast, "1 number
becomes 21 locally-adjusted numbers," is the clearest way to demonstrate
real downscaling (not a UI wrapper on one number) to judges. Follow with
one GP under a heavy-rain advisory next to a dry neighboring GP under
normal operations, to show the advisories are genuinely location-specific.
Close with `reports/validation_report.md` and state plainly that ground
truth here is ERA5-Land reanalysis, not physical stations.

## Known limitations

- **Proxy ground truth**: ERA5-Land reanalysis, not physical panchayat
  stations, may not capture true local variation the method is meant to
  detect. This is disclosed in the dashboard footer and API design, not
  hidden.
- **Rainfall-only grid input**: the IMD grid provided is rainfall-only, so
  temp/RH/wind are currently passed through from the block forecast
  unchanged rather than downscaled. The pipeline is built so adding a
  gridded temp/RH/wind source later requires no code restructuring (see
  `VARIABLE_SPECS` in `src/train_downscaling_model.py`).
  Currently modeled: **rainfall only**.
- **Small sample**: 1 year (2025) of data per GP, 21 GPs. This is why the
  MVP favors simple, explainable statistical methods (per-GP delta/ratio
  correction) over deep learning, and pools all GPs into one Random Forest
  per variable rather than training 21 separate models.
- **Single Block**: Sathupally only. Multi-block scaling is a config
  change away in principle, but untested.
- **4 of 21 GP coordinates are estimated, not geocoded**: Nominatim
  returned no match for Cherukupalli and Yatalakunta, and returned
  wrong-district matches (45–57 km off, a known issue with common Telugu
  village names) for Kistapuram and Kistaram. All four were corrected using
  the LGD village-code adjacency in the mapping file (each shares or
  neighbors a village code with an already-correctly-geocoded GP) rather
  than a real geocode. See `data/processed/gp_centroids.csv`; the other 17
  GPs are Nominatim-geocoded and were sanity-checked to fall within ~16 km
  of the block cluster center.
- **Generic advisory thresholds**: not crop-specific.
- **No live delivery**: API + web dashboard only, no SMS/WhatsApp/IVR.
