"""Phase 0.5: within-GP spatial estimation for farm/plot coordinates.

This is NOT a new trained model. The existing downscaling model
(models/downscaling_model.pkl) is unchanged and still operates at Gram
Panchayat level (21 fixed points) -- see docs/FOUNDATION.md. This module
adds one derivation step on top of that GP-level output:

    GP-level prediction (21 points)
            |
    farm/plot coordinates
            |
    inverse-distance weighting over nearest GP centroids
            |
    farm/plot ESTIMATE (explicitly labeled, never called an ML prediction)

If a farm/plot has no coordinates, callers should use the GP-level value
directly and label it "gp_level" -- this module is only invoked when real
coordinates exist.
"""
from __future__ import annotations

from utils import haversine_km

DEFAULT_NEAREST_N = 3
IDW_POWER = 2  # standard inverse-distance-weighting exponent


def idw_estimate(
    lat: float,
    lon: float,
    gp_values: dict[str, tuple[float, float, float]],
    nearest_n: int = DEFAULT_NEAREST_N,
) -> dict | None:
    """gp_values: {gp_name: (gp_lat, gp_lon, value)}. Returns None if no
    gp_values are provided. Returns a dict with the estimate plus full
    provenance (which GPs/distances/weights were used) so the result is
    auditable rather than an opaque number.
    """
    if not gp_values:
        return None

    distances = [
        (gp_name, haversine_km(lat, lon, gp_lat, gp_lon), value)
        for gp_name, (gp_lat, gp_lon, value) in gp_values.items()
    ]
    distances.sort(key=lambda item: item[1])
    nearest = distances[:nearest_n]

    # Exact coincidence with a GP centroid (distance == 0): avoid dividing by
    # zero, just use that GP's value directly.
    for gp_name, distance_km, value in nearest:
        if distance_km < 1e-6:
            return {
                "value": value,
                "method": "exact_match",
                "sources": [{"gram_panchayat": gp_name, "distance_km": 0.0, "weight": 1.0}],
            }

    weights = [1 / (distance_km**IDW_POWER) for _, distance_km, _ in nearest]
    total_weight = sum(weights)
    estimate = sum(w * value for (_, _, value), w in zip(nearest, weights)) / total_weight

    return {
        "value": round(estimate, 3),
        "method": f"idw_nearest_{len(nearest)}",
        "sources": [
            {
                "gram_panchayat": gp_name,
                "distance_km": round(distance_km, 2),
                "weight": round(w / total_weight, 3),
            }
            for (gp_name, distance_km, _), w in zip(nearest, weights)
        ],
    }
