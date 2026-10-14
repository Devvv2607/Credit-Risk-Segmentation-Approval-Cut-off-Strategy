"""Final evaluation on the held-out test split — run once, after everything is frozen.

By the time this runs, the bins, features, coefficients, scorecard and recommended
cut-off have all been fixed using train and validation only. This step:
  - computes test AUC / Gini / KS for the scorecard model (labelled final);
  - writes aggregated ROC and KS curves for the test split;
  - adds the test score-band distribution;
  - applies the frozen cut-off to test and records approval and payment-difficulty rates;
  - fits an unconstrained benchmark (HistGradientBoosting on raw features, train only)
    purely to measure what the explainable scorecard gives up.
Nothing here feeds back into any earlier step.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_curve

from src.binning import candidate_columns, load_model_frame
from src.common import connect, load_settings, path, read_json, write_csv, write_json
from src.model import metrics
from src.scorecard import score_distribution

warnings.filterwarnings("ignore")


def roc_points(y, score, n_points: int = 101) -> pd.DataFrame:
    """ROC curve thinned to at most n_points aggregated points (no applicant rows)."""
    fpr, tpr, thr = roc_curve(y, -score)  # higher score = safer, so rank risk by -score
    idx = np.unique(np.linspace(0, len(fpr) - 1, n_points).round().astype(int))
    return pd.DataFrame({"fpr": fpr[idx], "tpr": tpr[idx], "score_threshold": -thr[idx]}).replace(
        [np.inf, -np.inf], np.nan
    )


def ks_curve(y, score, step: int = 2) -> pd.DataFrame:
    """Cumulative share of bads and goods at or below each score threshold."""
    y = np.asarray(y).astype(bool)
    grid = np.arange(np.floor(score.min() / step) * step, np.ceil(score.max() / step) * step + step, step)
    s_bad, s_good = np.sort(score[y]), np.sort(score[~y])
    cum_bad = np.searchsorted(s_bad, grid, side="left") / len(s_bad)
    cum_good = np.searchsorted(s_good, grid, side="left") / len(s_good)
    return pd.DataFrame(
        {"score_threshold": grid, "cum_bad_share": cum_bad, "cum_good_share": cum_good, "ks": cum_bad - cum_good}
    )


def benchmark(s) -> dict:
    con = connect(read_only=True)
    df = load_model_frame(con)
    con.close()
    cols, categorical = candidate_columns(df, s["protected_attributes"])
    X = df[cols].copy()
    for c in categorical:
        X[c] = X[c].astype("category")
    tr, va, te = (df["split"] == k for k in ("train", "validation", "test"))
    clf = HistGradientBoostingClassifier(random_state=s["seed"], categorical_features="from_dtype")
    clf.fit(X[tr], df.loc[tr, "TARGET"])
    return {
        "model": "HistGradientBoostingClassifier (sklearn defaults) on all non-protected raw candidate features",
        "n_features": len(cols),
        "trained_on": "train",
        "validation": metrics(df.loc[va, "TARGET"].to_numpy(), clf.predict_proba(X[va])[:, 1]),
        "test": metrics(df.loc[te, "TARGET"].to_numpy(), clf.predict_proba(X[te])[:, 1]),
    }


def main() -> dict:
    s = load_settings()
    out = path("outputs")
    scores = pd.read_parquet(path("clean_dir") / "scores.parquet")
    test = scores[scores["split"] == "test"]
    y, p, score = test["TARGET"].to_numpy(), test["p_bad"].to_numpy(), test["score"].to_numpy()

    m = read_json(out / "metrics.json")
    m["test"] = {**metrics(y, p), "label": "final — computed once after all modelling and cut-off choices were frozen"}
    m["validation_test_gini_gap"] = m["validation"]["gini"] - m["test"]["gini"]
    m["benchmark"] = benchmark(s)
    m["benchmark_test_gini_gap"] = m["benchmark"]["test"]["gini"] - m["test"]["gini"]

    write_csv(roc_points(y, score), out / "roc_points.csv")
    write_csv(ks_curve(y, score), out / "ks_curve.csv")

    sc = read_json(out / "scorecard_summary.json")
    edges = np.array(sc["band_edges"])
    dist = pd.read_csv(out / "score_distribution.csv")
    dist = pd.concat([dist[dist["split"] == "validation"], score_distribution(scores, "test", edges)], ignore_index=True)
    write_csv(dist, out / "score_distribution.csv")
    from src.scorecard import non_monotonic_bands

    sc["non_monotonic_bands_test"] = non_monotonic_bands(dist[dist["split"] == "test"])
    from scipy.stats import spearmanr

    sc["spearman_score_vs_p_test"] = spearmanr(score, p).statistic
    write_json(sc, out / "scorecard_summary.json")

    rec = read_json(out / "recommendation.json")
    appr = score >= rec["cutoff"]
    t = {
        "n": int(len(test)),
        "approved": int(appr.sum()),
        "approval_rate": float(appr.mean()),
        "bad_rate": float(y[appr].mean()),
        "baseline_rate": float(y.mean()),
    }
    t["bad_rate_reduction_pp"] = (t["baseline_rate"] - t["bad_rate"]) * 100
    t["approval_rate_diff_pp_vs_validation"] = (t["approval_rate"] - rec["validation"]["approval_rate"]) * 100
    t["bad_rate_diff_pp_vs_validation"] = (t["bad_rate"] - rec["validation"]["bad_rate"]) * 100
    t["consistent_with_validation"] = bool(
        abs(t["approval_rate_diff_pp_vs_validation"]) < 1.0 and abs(t["bad_rate_diff_pp_vs_validation"]) < 0.5
    )
    t["consistency_rule"] = "approval within 1pp and payment-difficulty rate within 0.5pp of validation"
    rec["test"] = t
    write_json(rec, out / "recommendation.json")
    write_json(m, out / "metrics.json")

    print(f"TEST (final): AUC {m['test']['auc']:.4f}  Gini {m['test']['gini']:.4f}  KS {m['test']['ks']:.4f}")
    print(f"benchmark test Gini {m['benchmark']['test']['gini']:.4f} (gap {m['benchmark_test_gini_gap']:.4f})")
    print(f"cut-off {rec['cutoff']} on test: approval {t['approval_rate']:.2%}, rate {t['bad_rate']:.2%} "
          f"(validation {rec['validation']['approval_rate']:.2%}, {rec['validation']['bad_rate']:.2%})")
    return m


if __name__ == "__main__":
    main()
