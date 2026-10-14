from src.common import read_json


def test_min_segment_size(segments, settings):
    assert (segments["n"] >= settings["segments"]["min_segment_size"]).all()


def test_weighted_rate_equals_baseline_for_complete_dimensions(segments, out):
    base = read_json(out / "baseline.json")
    complete = segments[segments["dimension_complete"]]
    assert complete["dimension"].nunique() >= 1
    for dim, g in complete.groupby("dimension"):
        assert g["n"].sum() == base["applications"], dim
        assert abs((g["bad_rate"] * g["n"]).sum() / g["n"].sum() - base["baseline_rate"]) < 1e-9, dim


def test_segment_counts_cover_dimension_population(segments, out):
    base = read_json(out / "baseline.json")
    for dim, g in segments.groupby("dimension"):
        assert g["n"].sum() <= base["applications"]
        if dim not in base["dimensions_with_excluded_segments"]:
            assert g["n"].sum() == base["applications"]


def test_wilson_contains_estimate(segments):
    assert (segments["ci_low"] <= segments["bad_rate"]).all()
    assert (segments["bad_rate"] <= segments["ci_high"]).all()
    assert (segments["ci_low"] >= 0).all() and (segments["ci_high"] <= 1).all()


def test_lift_definition(segments, out):
    base = read_json(out / "baseline.json")["baseline_rate"]
    assert ((segments["lift"] - segments["bad_rate"] / base).abs() < 1e-9).all()
