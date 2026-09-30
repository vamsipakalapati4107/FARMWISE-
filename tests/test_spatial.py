from spatial import idw_estimate


def test_empty_gp_values_returns_none():
    assert idw_estimate(17.2, 80.85, {}) is None


def test_exact_match_returns_that_gps_value_directly():
    gp_values = {
        "A": (17.2, 80.85, 10.0),
        "B": (17.5, 80.90, 20.0),
    }
    result = idw_estimate(17.2, 80.85, gp_values)
    assert result["method"] == "exact_match"
    assert result["value"] == 10.0
    assert result["sources"][0]["gram_panchayat"] == "A"
    assert result["sources"][0]["distance_km"] == 0.0


def test_closer_gp_has_more_weight():
    # A is much closer to the query point than B.
    gp_values = {
        "A": (17.2001, 80.8501, 10.0),
        "B": (18.5, 82.0, 20.0),
    }
    result = idw_estimate(17.2, 80.85, gp_values)
    weight_a = next(s["weight"] for s in result["sources"] if s["gram_panchayat"] == "A")
    weight_b = next(s["weight"] for s in result["sources"] if s["gram_panchayat"] == "B")
    assert weight_a > weight_b
    # Estimate should be pulled much closer to A's value than a plain average.
    assert result["value"] < 15.0


def test_symmetric_points_average_evenly():
    # Two GPs placed symmetrically around the query point get equal weight.
    gp_values = {
        "A": (17.1, 80.85, 10.0),
        "B": (17.3, 80.85, 20.0),
    }
    result = idw_estimate(17.2, 80.85, gp_values)
    weights = {s["gram_panchayat"]: s["weight"] for s in result["sources"]}
    assert abs(weights["A"] - weights["B"]) < 1e-6
    assert abs(result["value"] - 15.0) < 0.5


def test_respects_nearest_n_limit():
    gp_values = {
        "A": (17.2001, 80.8501, 10.0),
        "B": (17.21, 80.86, 20.0),
        "C": (17.22, 80.87, 30.0),
        "D": (19.0, 85.0, 999.0),  # far away, should be excluded by nearest_n=3
    }
    result = idw_estimate(17.2, 80.85, gp_values, nearest_n=3)
    names = {s["gram_panchayat"] for s in result["sources"]}
    assert "D" not in names
    assert len(names) == 3
