"""Phase 8 — Points scorecard (PDO scaling), implemented by hand.

Scaling: a score of base_score corresponds to good:bad odds of base_odds, and every
pdo points doubles the odds.
    factor = pdo / ln(2)
    offset = base_score - factor * ln(base_odds)
    points(bin) = -(beta * WoE + intercept / n) * factor + offset / n
Summing points across the n features gives offset - factor * logit(p_bad), i.e. a score
that rises as the odds of repaying rise. Points are rounded for display only; scores
are computed from unrounded points.
"""

from __future__ import annotations

import math
import pickle
import warnings

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src.binning import bin_table
from src.common import load_settings, path, write_csv, write_json

warnings.filterwarnings("ignore")


def scaling(s) -> tuple[float, float]:
    sc = s["scorecard"]
    factor = sc["pdo"] / math.log(2)
    offset = sc["base_score"] - factor * math.log(sc["base_odds"])
    return factor, offset


def load_model():
    with open(path("clean_dir") / "model.pkl", "rb") as f:
        d = pickle.load(f)
    return d["model"], d["features"]


def build_scorecard(s) -> pd.DataFrame:
    model, feats = load_model()
    with open(path("clean_dir") / "binning_process.pkl", "rb") as f:
        bp = pickle.load(f)
    factor, offset = scaling(s)
    n = len(feats)
    b0 = model.intercept_[0]
    rows = []
    for f, beta in zip(feats, model.coef_[0]):
        t = bin_table(bp, f)
        t["coefficient"] = beta
        t["points_exact"] = -(beta * t["woe"] + b0 / n) * factor + offset / n
        rows.append(t)
    card = pd.concat(rows, ignore_index=True)
    card["points"] = card["points_exact"].round().astype(int)
    return card


def score_applicants(s, card: pd.DataFrame) -> pd.DataFrame:
    """Scores from the model (closed form) and from summing bin points — both kept."""
    model, feats = load_model()
    factor, offset = scaling(s)
    df = pd.read_parquet(path("clean_dir") / "woe_selected.parquet")
    logit = df[feats].to_numpy() @ model.coef_[0] + model.intercept_[0]
    out = df[["SK_ID_CURR", "TARGET", "split"]].copy()
    out["p_bad"] = 1 / (1 + np.exp(-logit))
    out["score"] = offset - factor * logit
    pts = np.zeros(len(df))
    for f in feats:
        lut = card[card["feature"] == f].set_index("woe")["points_exact"]
        lut = lut[~lut.index.duplicated()]
        pts += df[f].map(lut).to_numpy()
    out["score_from_points"] = pts
    return out


def band_edges(scores: pd.Series, width: int) -> np.ndarray:
    """Fixed-width bands between the 1st and 99th percentile; tails are open-ended."""
    lo = math.floor(scores.quantile(0.01) / width) * width
    hi = math.ceil(scores.quantile(0.99) / width) * width
    return np.arange(lo, hi + width, width)


def score_distribution(scores: pd.DataFrame, split: str, edges: np.ndarray) -> pd.DataFrame:
    d = scores[scores["split"] == split]
    bins = np.concatenate([[-np.inf], edges[1:-1], [np.inf]])
    cat = pd.cut(d["score"], bins=bins, right=False)
    g = d.groupby(cat, observed=False)["TARGET"].agg(["count", "sum"]).reset_index()
    labels = [f"<{int(edges[1])}"] + [f"{int(a)}-{int(b) - 1}" for a, b in zip(edges[1:-2], edges[2:-1])] + [f"{int(edges[-2])}+"]
    return pd.DataFrame(
        {
            "split": split,
            "band_order": range(len(labels)),
            "score_band": labels,
            "band_low": np.where(np.isfinite(bins[:-1]), bins[:-1], np.nan),
            "band_high": np.where(np.isfinite(bins[1:]), bins[1:], np.nan),
            "count": g["count"].astype(int),
            "bads": g["sum"].astype(int),
            "bad_rate": np.where(g["count"] > 0, g["sum"] / g["count"].replace(0, np.nan), np.nan),
            "share": g["count"] / len(d),
        }
    )


def non_monotonic_bands(dist: pd.DataFrame) -> list[str]:
    r = dist["bad_rate"].to_numpy()
    return [dist["score_band"].iloc[i] for i in range(1, len(r)) if r[i] > r[i - 1]]


def optbinning_crosscheck(s, card) -> dict:
    """Fit optbinning.Scorecard with the same settings on train and compare points."""
    try:
        from optbinning import BinningProcess, Scorecard
        from sklearn.linear_model import LogisticRegression

        from src.binning import candidate_columns, load_model_frame
        from src.common import connect

        _, feats = load_model()
        con = connect(read_only=True)
        df = load_model_frame(con)
        con.close()
        train = df[df["split"] == "train"]
        _, categorical = candidate_columns(df, s["protected_attributes"])
        b = s["binning"]
        bp = BinningProcess(
            variable_names=feats,
            categorical_variables=[f for f in feats if f in categorical],
            min_bin_size=b["min_bin_size"],
            max_n_bins=b["max_n_bins"],
            binning_fit_params={f: {"monotonic_trend": "auto_asc_desc"} for f in feats if f not in categorical},
        )
        sc = s["scorecard"]
        model = Scorecard(
            binning_process=bp,
            estimator=LogisticRegression(random_state=s["seed"], max_iter=s["model"]["max_iter"]),
            scaling_method="pdo_odds",
            scaling_method_params={"pdo": sc["pdo"], "odds": sc["base_odds"], "scorecard_points": sc["base_score"]},
        )
        # optbinning feeds missing values to the regression as WoE 0 by default; use the
        # Missing bin's own WoE, as this project does, so both sides see the same inputs.
        model.fit(train[feats], train["TARGET"].to_numpy(), metric_missing="empirical", metric_special="empirical")
        t = model.table(style="detailed")
        t = t[t["Count"] > 0]
        ours = card[card["count"] > 0]
        if len(t) != len(ours):
            return {"ran": True, "comparable": False, "note": "different bin counts"}
        per_row = np.abs(t["Points"].to_numpy() - ours["points_exact"].to_numpy())
        return {
            "ran": True,
            "comparable": True,
            "rows_compared": int(len(per_row)),
            "max_abs_point_difference": float(per_row.max()),
            "note": "optbinning.Scorecard fitted on train with the same binning settings and "
                    "metric_missing='empirical'; small differences come from solver tolerance.",
        }
    except Exception as e:  # cross-check is informative only
        return {"ran": False, "error": f"{type(e).__name__}: {e}"}


def main() -> dict:
    s = load_settings()
    factor, offset = scaling(s)
    card = build_scorecard(s)
    scores = score_applicants(s, card)
    scores.to_parquet(path("clean_dir") / "scores.parquet", index=False)

    max_recon = float(np.abs(scores["score"] - scores["score_from_points"]).max())
    val = scores[scores["split"] == "validation"]
    rho = spearmanr(val["score"], val["p_bad"]).statistic
    edges = band_edges(scores.loc[scores["split"] == "train", "score"], s["score_bands"]["width"])
    dist_val = score_distribution(scores, "validation", edges)

    out = path("outputs")
    write_csv(
        card[["feature", "bin_index", "bin", "count", "bad_rate", "woe", "coefficient", "points_exact", "points"]],
        out / "scorecard.csv",
    )
    write_csv(dist_val, out / "score_distribution.csv")
    xc = optbinning_crosscheck(s, card)
    summary = {
        "base_score": s["scorecard"]["base_score"],
        "base_odds": s["scorecard"]["base_odds"],
        "pdo": s["scorecard"]["pdo"],
        "factor": factor,
        "offset": offset,
        "n_features": int(card["feature"].nunique()),
        "band_edges": edges.tolist(),
        "band_edges_fit_on": "train score 1st-99th percentile",
        "max_abs_score_vs_points_difference": max_recon,
        "spearman_score_vs_p_validation": rho,
        "non_monotonic_bands_validation": non_monotonic_bands(dist_val),
        "score_range_validation": [float(val["score"].min()), float(val["score"].max())],
        "optbinning_crosscheck": xc,
    }
    write_json(summary, out / "scorecard_summary.json")
    assert max_recon < 1e-8, "points do not reproduce the score"
    assert rho <= -1 + 1e-12, "score is not strictly decreasing in predicted probability"
    print({k: v for k, v in summary.items() if k != "band_edges"})
    print(dist_val[["score_band", "count", "bad_rate"]].to_string(index=False))
    return summary


if __name__ == "__main__":
    main()
