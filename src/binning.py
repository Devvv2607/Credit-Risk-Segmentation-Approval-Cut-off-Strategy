"""Phase 6 — WoE binning, IV and feature selection (train split only).

Convention used throughout the project: WoE = ln(%good / %bad), so a positive WoE
marks a safer-than-average bin and a negative WoE a riskier one. optbinning uses the
same convention; this is verified at run time on the riskiest bin of EXT_SOURCE_3
(low external score = more payment difficulty, so its WoE must be negative).

Missing values get their own bin. Note: optbinning's transform() maps missing values
to WoE 0 by default; we always pass metric_missing="empirical" so an applicant with a
missing value receives the Missing bin's own WoE.

Selection, in order, with every decision recorded:
  1. protected attributes are never candidates (fairness: not used in the model);
  2. IV >= iv_min (weaker features add noise, not separation);
  3. IV > iv_leak_flag is flagged as a possible leak and reported;
  4. for any pair with |corr| > corr_max on train WoE, the lower-IV one is dropped
     (multicollinearity flips coefficient signs and makes points unstable);
  5. the strongest max_features remaining (by IV) are kept.
"""

from __future__ import annotations

import hashlib
import pickle
import warnings

import numpy as np
import pandas as pd
from optbinning import BinningProcess

from src.common import connect, load_settings, path, write_csv, write_json

warnings.filterwarnings("ignore")

# Columns never offered to the binning: identifiers, the target, the protected
# attributes (handled separately), and raw day counts replaced by engineered years.
NON_CANDIDATES = {"SK_ID_CURR", "TARGET", "DAYS_BIRTH", "DAYS_EMPLOYED"}
SIGN_CHECK_FEATURE = "EXT_SOURCE_3"


def load_model_frame(con) -> pd.DataFrame:
    """Model table joined to split labels, ordered by ID for determinism."""
    return con.execute(
        "SELECT m.*, s.split FROM model_table m JOIN split_ids s USING (SK_ID_CURR) "
        "ORDER BY m.SK_ID_CURR"
    ).df()


def candidate_columns(df: pd.DataFrame, protected: list[str]) -> tuple[list[str], list[str]]:
    cols = [c for c in df.columns if c not in NON_CANDIDATES | {"split"} | set(protected)]
    categorical = [c for c in cols if df[c].dtype == object]
    return cols, categorical


def bin_table(bp: BinningProcess, name: str) -> pd.DataFrame:
    """Binning table for one feature with WoE recomputed as ln(%good/%bad)."""
    t = bp.get_binned_variable(name).binning_table.build().iloc[:-1].copy()  # drop Totals
    t = t.reset_index(drop=True)
    goods, bads = t["Non-event"].astype(float), t["Event"].astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        woe = np.log((goods / goods.sum()) / (bads / bads.sum()))
    woe = woe.where(np.isfinite(woe), 0.0)  # empty Special/Missing bins carry no evidence
    iv_contrib = (goods / goods.sum() - bads / bads.sum()) * woe
    return pd.DataFrame(
        {
            "feature": name,
            "bin_index": range(len(t)),
            "bin": t["Bin"].map(lambda b: ", ".join(map(str, b)) if isinstance(b, (list, np.ndarray)) else str(b)),
            "count": t["Count"].astype(int),
            "goods": goods.astype(int),
            "bads": bads.astype(int),
            "bad_rate": np.where(t["Count"] > 0, bads / t["Count"].replace(0, np.nan), np.nan),
            "woe": woe,
            "woe_library": t["WoE"].astype(float),
            "iv_contribution": iv_contrib,
        }
    )


def woe_transform(bp: BinningProcess, tables: dict[str, pd.DataFrame], df: pd.DataFrame, feats) -> pd.DataFrame:
    """Map every applicant to its bin index, then to that bin's WoE."""
    out = {}
    for f in feats:
        ob = bp.get_binned_variable(f)
        idx = ob.transform(df[f].values, metric="indices", metric_missing="empirical", metric_special="empirical")
        out[f] = tables[f]["woe"].to_numpy()[np.asarray(idx, dtype=int)]
    return pd.DataFrame(out, index=df.index)


def fit_binning(train: pd.DataFrame, cols, categorical, s) -> BinningProcess:
    b = s["binning"]
    numeric = [c for c in cols if c not in categorical]
    bp = BinningProcess(
        variable_names=cols,
        categorical_variables=categorical,
        min_bin_size=b["min_bin_size"],
        max_n_bins=b["max_n_bins"],
        binning_fit_params={c: {"monotonic_trend": "auto_asc_desc"} for c in numeric},
        n_jobs=1,
    )
    bp.fit(train[cols], train["TARGET"].to_numpy())
    return bp


def fit_on_train(df: pd.DataFrame, cols, categorical, s) -> tuple[BinningProcess, pd.DataFrame]:
    """Fit the binning on the rows labelled train — the only rows binning ever sees."""
    train = df[df["split"] == "train"].reset_index(drop=True)
    return fit_binning(train, cols, categorical, s), train


def select_features(iv: pd.DataFrame, woe_train: pd.DataFrame, s) -> pd.DataFrame:
    b = s["binning"]
    iv = iv.sort_values(["iv", "feature"], ascending=[False, True]).reset_index(drop=True)
    iv["leak_flag"] = iv["iv"] > b["iv_leak_flag"]
    decision, reason = {}, {}
    survivors: list[str] = []  # passed IV and correlation filters, in IV order
    kept: list[str] = []
    corr = woe_train.corr()
    for f, v in zip(iv["feature"], iv["iv"]):
        if v < b["iv_min"]:
            decision[f], reason[f] = "dropped", f"IV below {b['iv_min']}"
            continue
        clash = [k for k in survivors if abs(corr.loc[f, k]) > b["corr_max"]]
        if clash:
            k = clash[0]
            decision[f] = "dropped"
            reason[f] = f"|corr| {abs(corr.loc[f, k]):.2f} with {k} (higher IV) exceeds {b['corr_max']}"
            continue
        survivors.append(f)
        if len(kept) >= b["max_features"]:
            decision[f], reason[f] = "dropped", f"passed filters but outside top {b['max_features']} by IV"
            continue
        kept.append(f)
        decision[f] = "selected"
        reason[f] = "IV above threshold, not highly correlated with a stronger feature" + (
            "; IV above leak flag, reviewed" if v > b["iv_leak_flag"] else ""
        )
    iv["decision"] = iv["feature"].map(decision)
    iv["reason"] = iv["feature"].map(reason)
    return iv


def main() -> dict:
    s = load_settings()
    protected = s["protected_attributes"]
    con = connect()
    df = load_model_frame(con)
    con.close()
    cols, categorical = candidate_columns(df, protected)
    print(f"binning {len(cols)} candidate features on the train split ...")
    bp, train = fit_on_train(df, cols, categorical, s)

    tables = {c: bin_table(bp, c) for c in cols}
    # Every table must be built on exactly the train rows.
    fit_counts = {c: int(t["count"].sum()) for c, t in tables.items()}
    assert set(fit_counts.values()) == {len(train)}, "binning not fit on the train split"

    # Sign convention check on an obviously risky bin.
    sc = tables[SIGN_CHECK_FEATURE]
    risky = sc[sc["count"] > 0].sort_values("bad_rate", ascending=False).iloc[0]
    assert risky["woe"] < 0, "WoE sign convention violated"
    assert np.allclose(sc["woe"], sc["woe_library"], atol=1e-9), "library WoE differs from ln(%good/%bad)"

    iv = pd.DataFrame(
        {"feature": c, "iv": t["iv_contribution"].sum(), "n_bins": int((t["count"] > 0).sum()),
         "dtype": "categorical" if c in categorical else "numerical"}
        for c, t in tables.items()
    )
    woe_train = woe_transform(bp, tables, train, cols)
    sel = select_features(iv, woe_train, s)
    selected = sel.loc[sel["decision"] == "selected", "feature"].tolist()
    assert not set(selected) & set(protected)

    # Applicant-level WoE matrix for every split: local only.
    woe_all = woe_transform(bp, tables, df, selected)
    woe_all.insert(0, "SK_ID_CURR", df["SK_ID_CURR"].to_numpy())
    woe_all.insert(1, "TARGET", df["TARGET"].to_numpy())
    woe_all.insert(2, "split", df["split"].to_numpy())
    woe_all.to_parquet(path("clean_dir") / "woe_selected.parquet", index=False)
    with open(path("clean_dir") / "binning_process.pkl", "wb") as f:
        pickle.dump(bp, f)
    fit_ids = np.sort(train["SK_ID_CURR"].to_numpy())
    write_json(
        {"fit_n": len(train), "fit_ids_sha256": hashlib.sha256(fit_ids.tobytes()).hexdigest()},
        path("clean_dir") / "binning_fit_meta.json",
    )

    out = path("outputs")
    write_csv(sel[["feature", "dtype", "iv", "n_bins", "leak_flag", "decision", "reason"]], out / "iv_summary.csv")
    bins = pd.concat([tables[f] for f in selected], ignore_index=True)
    bins = bins[bins["count"] > 0][["feature", "bin_index", "bin", "count", "bad_rate", "woe", "iv_contribution"]]
    write_csv(bins, out / "bins.csv")
    write_json(
        {
            "woe_convention": "WoE = ln(%good / %bad); positive = safer than average",
            "sign_check": {
                "feature": SIGN_CHECK_FEATURE,
                "riskiest_bin": risky["bin"],
                "bad_rate": risky["bad_rate"],
                "woe": risky["woe"],
                "library_matches_convention": True,
            },
            "fit_split": "train",
            "fit_n": len(train),
            "candidates_evaluated": len(cols),
            "protected_attributes_excluded": protected,
            "thresholds": s["binning"],
            "leak_flags": sel.loc[sel["leak_flag"], "feature"].tolist(),
            "selected": selected,
            "decisions": sel[["feature", "iv", "decision", "reason"]].to_dict(orient="records"),
        },
        out / "selected_features.json",
    )
    print(sel.head(25)[["feature", "iv", "decision", "reason"]].to_string(index=False))
    print(f"selected {len(selected)} of {len(cols)}; leak flags: {sel.loc[sel['leak_flag'], 'feature'].tolist()}")
    return {"selected": selected}


if __name__ == "__main__":
    main()
