"""Phase 9 — Cut-off strategy (validation split only).

An applicant is approved when score >= cut-off. For every cut-off from the minimum to
the maximum validation score, in steps of cutoff.step, we count who is approved and how
many of those had payment difficulties, and value the result with the ILLUSTRATIVE
assumptions in config/assumptions.yaml:

    profit = goods_approved * avg_loan * margin - bads_approved * avg_loan * loss_given_bad

The recommendation rule is declared in config/settings.yaml (cutoff.rule) and applied
mechanically. Test data is not read here; src/final_test.py applies the frozen cut-off
to the test split once.
"""

from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd

from src.common import load_assumptions, load_settings, path, write_csv, write_json


def cutoff_grid(scores: pd.Series, step: int) -> np.ndarray:
    lo = math.floor(scores.min() / step) * step
    hi = math.ceil(scores.max() / step) * step
    return np.arange(lo, hi + step, step)


def cutoff_table(d: pd.DataFrame, grid: np.ndarray, a: dict) -> pd.DataFrame:
    """Approval and payment-difficulty figures at each cut-off, plus illustrative profit."""
    score = d["score"].to_numpy()
    bad = d["TARGET"].to_numpy().astype(bool)
    n, n_bad = len(d), int(bad.sum())
    rows = []
    for c in grid:
        appr = score >= c
        approved = int(appr.sum())
        bads_appr = int((appr & bad).sum())
        goods_appr = approved - bads_appr
        rows.append(
            {
                "cutoff": int(c),
                "approved": approved,
                "approval_rate": approved / n,
                "goods_approved": goods_appr,
                "bads_approved": bads_appr,
                "bad_rate": bads_appr / approved if approved else np.nan,
                "bads_avoided": n_bad - bads_appr,
                "goods_rejected": (n - n_bad) - goods_appr,
            }
        )
    t = pd.DataFrame(rows)
    return add_profit(t, a["avg_loan"]["value"], a["margin"]["value"], a["loss_given_bad"]["value"])


def add_profit(t: pd.DataFrame, avg_loan: float, margin: float, lgb: float) -> pd.DataFrame:
    t = t.copy()
    t["profit"] = t["goods_approved"] * avg_loan * margin - t["bads_approved"] * avg_loan * lgb
    return t


def recommend(t: pd.DataFrame, max_rate: float) -> pd.Series | None:
    """Declared rule: highest-profit cut-off whose payment-difficulty rate <= max_rate.
    Ties go to the lower cut-off (approves more applicants)."""
    ok = t[(t["approved"] > 0) & (t["bad_rate"] <= max_rate)]
    if ok.empty:
        return None
    return ok.sort_values(["profit", "cutoff"], ascending=[False, True]).iloc[0]


def sensitivity(t: pd.DataFrame, a: dict, max_rate: float, base_cutoff: int) -> pd.DataFrame:
    keys = ["avg_loan", "margin", "loss_given_bad"]
    rows = []
    for levels in itertools.product(["low", "base", "high"], repeat=3):
        vals = {k: a[k]["value" if lv == "base" else lv] for k, lv in zip(keys, levels)}
        r = recommend(add_profit(t, vals["avg_loan"], vals["margin"], vals["loss_given_bad"]), max_rate)
        rows.append(
            {
                **{f"{k}_level": lv for k, lv in zip(keys, levels)},
                **vals,
                "n_changed": sum(lv != "base" for lv in levels),
                "recommended_cutoff": None if r is None else int(r["cutoff"]),
                "approval_rate": None if r is None else r["approval_rate"],
                "bad_rate": None if r is None else r["bad_rate"],
                "profit": None if r is None else r["profit"],
                "shift_vs_base": None if r is None else int(r["cutoff"]) - base_cutoff,
            }
        )
    return pd.DataFrame(rows)


def validation_cutoffs(scores: pd.DataFrame, s: dict, a: dict):
    """Cut-off table and recommendation from the validation rows only."""
    cfg = s["cutoff"]
    val = scores[scores["split"] == "validation"]
    t = cutoff_table(val, cutoff_grid(val["score"], cfg["step"]), a)
    return val, t, recommend(t, cfg["max_difficulty_rate"])


def main() -> dict:
    s = load_settings()
    a = load_assumptions()
    cfg = s["cutoff"]
    scores = pd.read_parquet(path("clean_dir") / "scores.parquet")
    val, t, rec = validation_cutoffs(scores, s, a)
    assert rec is not None, "no cut-off satisfies the declared rule"
    base = t.iloc[0]
    sens = sensitivity(t, a, cfg["max_difficulty_rate"], int(rec["cutoff"]))
    best_profit = t.loc[t["profit"].idxmax()]

    out = path("outputs")
    write_csv(t, out / "cutoff_table.csv")
    write_csv(sens, out / "sensitivity.csv")
    one_at_a_time = sens[sens["n_changed"] <= 1]
    recommendation = {
        "cutoff": int(rec["cutoff"]),
        "rule": cfg["rule"],
        "max_difficulty_rate": cfg["max_difficulty_rate"],
        "selected_on": "validation",
        "label": "Result under the illustrative assumptions in config/assumptions.yaml; not a lending decision.",
        "validation": {
            "n": int(len(val)),
            "approved": int(rec["approved"]),
            "approval_rate": rec["approval_rate"],
            "bad_rate": rec["bad_rate"],
            "bads_avoided": int(rec["bads_avoided"]),
            "goods_rejected": int(rec["goods_rejected"]),
            "profit": rec["profit"],
            "baseline_rate": base["bad_rate"],
            "profit_approve_all": base["profit"],
            "bad_rate_reduction_pp": (base["bad_rate"] - rec["bad_rate"]) * 100,
            "bad_rate_relative_reduction": 1 - rec["bad_rate"] / base["bad_rate"],
        },
        "unconstrained_max_profit": {
            "cutoff": int(best_profit["cutoff"]),
            "approval_rate": best_profit["approval_rate"],
            "bad_rate": best_profit["bad_rate"],
            "profit": best_profit["profit"],
        },
        "sensitivity": {
            "scenarios": int(len(sens)),
            "min_cutoff": int(sens["recommended_cutoff"].min()),
            "max_cutoff": int(sens["recommended_cutoff"].max()),
            "max_abs_shift": int(sens["shift_vs_base"].abs().max()),
            "one_at_a_time_min_cutoff": int(one_at_a_time["recommended_cutoff"].min()),
            "one_at_a_time_max_cutoff": int(one_at_a_time["recommended_cutoff"].max()),
        },
        "test": None,  # filled once by src/final_test.py
    }
    write_json(recommendation, out / "recommendation.json")

    assert (t["approval_rate"].diff().dropna() <= 0).all(), "approval rate must not increase with cut-off"
    assert base["approval_rate"] == 1.0
    assert abs(base["bad_rate"] - val["TARGET"].mean()) < 1e-12
    v = recommendation["validation"]
    print(f"recommended cut-off {recommendation['cutoff']}: approval {v['approval_rate']:.2%}, "
          f"payment-difficulty rate {v['bad_rate']:.2%} vs {v['baseline_rate']:.2%} approving everyone")
    print(f"unconstrained max-profit cut-off {best_profit['cutoff']} ({best_profit['bad_rate']:.2%})")
    print(f"sensitivity: cut-off ranges {recommendation['sensitivity']['min_cutoff']}-"
          f"{recommendation['sensitivity']['max_cutoff']} across {len(sens)} scenarios")
    return recommendation


if __name__ == "__main__":
    main()
