import pandas as pd
import yaml

from src import cutoff
from src.common import load_assumptions, load_settings, read_json


def test_approval_non_increasing(cutoff_table):
    assert (cutoff_table["approval_rate"].diff().dropna() <= 0).all()


def test_minimum_cutoff_is_approve_all(cutoff_table, scores):
    first = cutoff_table.iloc[0]
    val = scores[scores["split"] == "validation"]
    assert first["approval_rate"] == 1.0
    assert abs(first["bad_rate"] - val["TARGET"].mean()) < 1e-9


def test_recommendation_satisfies_rule(cutoff_table, out, settings):
    rec = read_json(out / "recommendation.json")
    m = settings["cutoff"]["max_difficulty_rate"]
    ok = cutoff_table[(cutoff_table["approved"] > 0) & (cutoff_table["bad_rate"] <= m)]
    best = ok.sort_values(["profit", "cutoff"], ascending=[False, True]).iloc[0]
    assert int(best["cutoff"]) == rec["cutoff"]
    assert rec["validation"]["bad_rate"] <= m
    assert rec["rule"] == settings["cutoff"]["rule"]


def test_assumptions_change_profit_not_rates(scores, tmp_path):
    s = load_settings()
    a = load_assumptions()
    alt = yaml.safe_load(yaml.safe_dump(a))
    alt["margin"]["value"] = a["margin"]["value"] * 2
    alt["loss_given_bad"]["value"] = a["loss_given_bad"]["value"] * 0.5
    p = tmp_path / "assumptions.yaml"
    p.write_text(yaml.safe_dump(alt), encoding="utf-8")
    _, t1, _ = cutoff.validation_cutoffs(scores, s, a)
    _, t2, _ = cutoff.validation_cutoffs(scores, s, load_assumptions(p))
    assert t1["approval_rate"].equals(t2["approval_rate"])
    assert t1["bad_rate"].equals(t2["bad_rate"])
    assert not t1["profit"].equals(t2["profit"])


def test_recommendation_has_validation_and_test(out):
    rec = read_json(out / "recommendation.json")
    for k in ("approval_rate", "bad_rate", "baseline_rate"):
        assert rec["validation"][k] is not None
        assert rec["test"][k] is not None


def test_sensitivity_grid_complete(out):
    sens = pd.read_csv(out / "sensitivity.csv")
    assert len(sens) == 27
    assert sens["recommended_cutoff"].notna().all()
