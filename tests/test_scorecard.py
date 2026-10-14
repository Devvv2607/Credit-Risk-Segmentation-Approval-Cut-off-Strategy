import math

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src.common import path, read_json


def test_score_strictly_decreasing_in_probability(scores):
    for split in ("validation", "test"):
        d = scores[scores["split"] == split]
        assert spearmanr(d["score"], d["p_bad"]).statistic <= -1 + 1e-12


def test_points_reproduce_scores_for_random_applicants(scores, out, metrics):
    card = pd.read_csv(out / "scorecard.csv")
    woe = pd.read_parquet(path("clean_dir") / "woe_selected.parquet")
    sample = woe.sample(n=100, random_state=42)
    expected = scores.set_index("SK_ID_CURR").loc[sample["SK_ID_CURR"], "score"].to_numpy()
    total = np.zeros(len(sample))
    for f in metrics["features"]:
        rows = card[card["feature"] == f]
        for i, w in enumerate(sample[f].to_numpy()):
            match = rows.loc[(rows["woe"] - w).abs() < 1e-9, "points_exact"]
            assert len(match) >= 1, f"no bin for {f} woe {w}"
            total[i] += match.iloc[0]
    # scorecard.csv stores points with 10 significant digits
    np.testing.assert_allclose(total, expected, rtol=0, atol=1e-6)


def test_scaling_matches_definition(out, settings):
    s = read_json(out / "scorecard_summary.json")
    c = settings["scorecard"]
    factor = c["pdo"] / math.log(2)
    assert abs(s["factor"] - factor) < 1e-12
    assert abs(s["offset"] - (c["base_score"] - factor * math.log(c["base_odds"]))) < 1e-9


def test_scorecard_features_match_model(out, metrics):
    card = pd.read_csv(out / "scorecard.csv")
    assert sorted(card["feature"].unique()) == sorted(metrics["features"])
    assert (card["points"] == card["points_exact"].round()).all()


def test_score_bands_reported(out):
    d = pd.read_csv(out / "score_distribution.csv")
    assert set(d["split"]) == {"validation", "test"}
    s = read_json(out / "scorecard_summary.json")
    assert "non_monotonic_bands_validation" in s and "non_monotonic_bands_test" in s
