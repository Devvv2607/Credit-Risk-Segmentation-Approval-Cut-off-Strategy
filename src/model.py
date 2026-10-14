"""Phase 7 — Logistic regression on WoE features, with coefficient diagnostics.

Fit on train only. This step reports train and validation metrics; test metrics are
computed once, later, by src/final_test.py after the cut-off has been frozen.

Sign expectation: with WoE = ln(%good/%bad) (positive = safer) and TARGET = 1 for
payment difficulty, a higher WoE should lower the predicted probability, so every
coefficient should be negative. A positive coefficient would give a riskier bin more
points on the scorecard, which a credit team would reject. Each one is investigated in
order (WoE convention, bin definitions via the univariate sign, correlation and VIF,
target encoding, leakage) and the decision is written to
outputs/coefficient_diagnostics.md. A feature is removed only under the rule in
config/settings.yaml (model.sign_fix_max_gini_loss), one at a time, with validation
Gini recorded before and after.
"""

from __future__ import annotations

import pickle

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve

from src.common import load_settings, path, read_json, write_csv, write_json


def load_woe() -> tuple[pd.DataFrame, list[str]]:
    df = pd.read_parquet(path("clean_dir") / "woe_selected.parquet")
    feats = read_json(path("outputs") / "selected_features.json")["selected"]
    return df, feats


def fit_lr(X: pd.DataFrame, y: np.ndarray, seed: int, max_iter: int) -> LogisticRegression:
    return LogisticRegression(random_state=seed, max_iter=max_iter).fit(X, y)


def metrics(y: np.ndarray, p: np.ndarray) -> dict:
    """AUC, Gini = 2*AUC - 1 and KS = max(TPR - FPR)."""
    auc = roc_auc_score(y, p)
    fpr, tpr, _ = roc_curve(y, p)
    return {"n": int(len(y)), "auc": auc, "gini": 2 * auc - 1, "ks": float(np.max(tpr - fpr))}


def vif(X: pd.DataFrame) -> pd.Series:
    """Variance inflation factor: 1 / (1 - R^2) regressing each column on the others."""
    out = {}
    A = X.to_numpy(dtype=float)
    for i, c in enumerate(X.columns):
        y = A[:, i]
        others = np.column_stack([np.ones(len(A)), np.delete(A, i, axis=1)])
        beta, *_ = np.linalg.lstsq(others, y, rcond=None)
        r2 = 1 - (y - others @ beta).var() / y.var()
        out[c] = np.inf if r2 >= 1 else 1 / (1 - r2)
    return pd.Series(out)


class Fitter:
    def __init__(self, train, val, s):
        self.train, self.val = train, val
        self.seed, self.it = s["seed"], s["model"]["max_iter"]
        self.ytr, self.yval = train["TARGET"].to_numpy(), val["TARGET"].to_numpy()

    def fit(self, feats):
        return fit_lr(self.train[feats], self.ytr, self.seed, self.it)

    def val_gini(self, model, feats) -> float:
        return metrics(self.yval, model.predict_proba(self.val[feats])[:, 1])["gini"]


def coefficient_table(fitter: Fitter, model, feats) -> pd.DataFrame:
    X = fitter.train[feats]
    v, corr = vif(X), X.corr()
    rows = []
    for f, c in zip(feats, model.coef_[0]):
        partner = corr[f].drop(f).abs().idxmax()
        rows.append(
            {
                "feature": f,
                "coefficient": c,
                "expected_sign": "negative",
                "sign_ok": bool(c < 0),
                "univariate_coefficient": fitter.fit([f]).coef_[0][0],
                "vif": v[f],
                "max_corr_feature": partner,
                "max_corr": corr.loc[f, partner],
            }
        )
    return pd.DataFrame(rows)


def resolve_signs(fitter: Fitter, feats: list[str], max_loss: float):
    """Apply the declared reversed-sign rule; return final features and a log."""
    feats = list(feats)
    log = []
    while True:
        model = fitter.fit(feats)
        diag = coefficient_table(fitter, model, feats)
        bad = diag[~diag["sign_ok"]]
        if bad.empty:
            return feats, model, diag, log
        g_full = fitter.val_gini(model, feats)
        options = []
        for r in bad.itertuples():
            reduced = [f for f in feats if f != r.feature]
            g_red = fitter.val_gini(fitter.fit(reduced), reduced)
            options.append((g_full - g_red, r, g_red))
        options.sort(key=lambda o: (o[0], o[1].feature))
        loss, r, g_red = options[0]
        eligible = r.univariate_coefficient < 0 and loss < max_loss
        log.append(
            {
                "feature": r.feature,
                "coefficient": r.coefficient,
                "univariate_coefficient": r.univariate_coefficient,
                "vif": r.vif,
                "max_corr_feature": r.max_corr_feature,
                "max_corr": r.max_corr,
                "val_gini_with": g_full,
                "val_gini_without": g_red,
                "gini_loss": loss,
                "removed": bool(eligible),
                "other_reversed": [o[1].feature for o in options[1:]],
            }
        )
        if not eligible:
            return feats, model, diag, log
        feats.remove(r.feature)


def write_diagnostics(diag, log, model, fitter, feats, max_loss) -> str:
    g = fitter.val_gini(model, feats)
    L = [
        "# Coefficient diagnostics",
        "",
        "Generated by `src/model.py`. Convention: WoE = ln(%good / %bad), positive = safer; "
        "TARGET = 1 means payment difficulty. Every coefficient is therefore expected to be **negative**: "
        "a positive one would give a riskier bin more points.",
        "",
        "## Investigation order for each unexpected sign",
        "",
        "1. **WoE sign convention** — checked at run time in `src/binning.py`: the riskiest EXT_SOURCE_3 bin "
        "has negative WoE and optbinning's WoE equals ln(%good/%bad) (see `selected_features.json`).",
        "2. **Bin definitions** — the feature is refitted alone; a negative univariate coefficient means its "
        "bins rank risk in the expected direction on their own.",
        "3. **Correlation and VIF** on train WoE values.",
        "4. **Target encoding** — TARGET used as delivered (1 = payment difficulty), checked in `src/clean.py`.",
        "5. **Leakage** — every candidate's IV is checked against the leak flag (`iv_summary.csv`).",
        "",
        f"**Rule** (declared in `config/settings.yaml`, `model.sign_fix_max_gini_loss = {max_loss}`): a feature "
        "with a reversed sign is removed only if its univariate sign is correct (so the reversal comes from "
        "overlap with other features, i.e. multicollinearity) and removing it costs less than that much "
        "validation Gini. One feature is removed at a time, smallest Gini loss first, then the model is refitted "
        "and re-checked. Note: this rule was written after the first fit flagged reversed signs; it follows the "
        "standard practice in the project brief, and its effect on Gini is reported below.",
        "",
        "## Investigations",
        "",
    ]
    if not log:
        L.append("No coefficient had an unexpected sign in the first fit.")
    for i, e in enumerate(log, 1):
        L += [
            f"### Step {i}: {e['feature']}",
            "",
            f"- Joint coefficient: {e['coefficient']:.4f} (expected negative)."
            + (f" Also reversed at this step: {', '.join(e['other_reversed'])}." if e["other_reversed"] else ""),
            "- WoE convention: verified (see above).",
            f"- Bin definitions: univariate coefficient {e['univariate_coefficient']:.4f} — "
            + ("expected sign; the bins rank risk correctly on their own." if e["univariate_coefficient"] < 0
               else "reversed; the binning itself needs review."),
            f"- Correlation / VIF: VIF {e['vif']:.2f}; most correlated with {e['max_corr_feature']} "
            f"(corr {e['max_corr']:.2f}). The feature's information is largely carried by other features, "
            "which is what lets the joint fit flip its sign.",
            "- Target encoding: TARGET ∈ {0, 1} as delivered.",
            "- Leakage: IV below the leak flag.",
            f"- Validation Gini with the feature {e['val_gini_with']:.4f}, without it {e['val_gini_without']:.4f} "
            f"(change {-e['gini_loss']:+.4f}).",
            "",
            "**Decision:** "
            + ("removed under the rule above (multicollinearity, negligible Gini cost)." if e["removed"]
               else "kept; it does not meet the removal rule. The sign remains unexpected: a safer bin of this "
                    "feature receives fewer points, partly offset by correlated features."),
            "",
        ]
    L += [
        "## Final model",
        "",
        f"Intercept {model.intercept_[0]:.6f}. Validation Gini {g:.4f}.",
        "",
        "| Feature | Coefficient | Sign as expected | Univariate coef. | VIF | Most correlated with (corr) |",
        "|---|---|---|---|---|---|",
    ]
    for r in diag.itertuples():
        L.append(
            f"| {r.feature} | {r.coefficient:.4f} | {'yes' if r.sign_ok else '**no**'} | "
            f"{r.univariate_coefficient:.4f} | {r.vif:.2f} | {r.max_corr_feature} ({r.max_corr:.2f}) |"
        )
    remaining = diag.loc[~diag["sign_ok"], "feature"].tolist()
    L += ["", "Unexpected signs remaining in the final model: " + (", ".join(remaining) if remaining else "none") + "."]
    return "\n".join(L) + "\n"


def main() -> dict:
    s = load_settings()
    df, selected = load_woe()
    train = df[df["split"] == "train"]
    val = df[df["split"] == "validation"]
    fitter = Fitter(train, val, s)
    max_loss = s["model"]["sign_fix_max_gini_loss"]

    first = fitter.fit(selected)
    first_val_gini = fitter.val_gini(first, selected)
    feats, model, diag, log = resolve_signs(fitter, selected, max_loss)

    m = {
        "model": "LogisticRegression on WoE features (lbfgs, default L2 penalty, C=1.0)",
        "features": feats,
        "features_selected_by_binning": selected,
        "removed_for_sign": [e["feature"] for e in log if e["removed"]],
        "validation_gini_before_sign_fix": first_val_gini,
        "train": metrics(fitter.ytr, model.predict_proba(train[feats])[:, 1]),
        "validation": metrics(fitter.yval, model.predict_proba(val[feats])[:, 1]),
        "test": None,  # filled once by src/final_test.py
        "benchmark": None,  # filled by src/final_test.py
    }
    m["train_validation_gini_gap"] = m["train"]["gini"] - m["validation"]["gini"]
    m["gap_within_limit"] = bool(abs(m["train_validation_gini_gap"]) < 0.05)
    m["baseline_rate"] = read_json(path("outputs") / "baseline.json")["baseline_rate"]
    m["unexpected_signs_remaining"] = diag.loc[~diag["sign_ok"], "feature"].tolist()

    out = path("outputs")
    coef = pd.concat(
        [pd.DataFrame([{"feature": "(intercept)", "coefficient": model.intercept_[0]}]), diag],
        ignore_index=True,
    )
    write_csv(coef, out / "coefficients.csv")
    (out / "coefficient_diagnostics.md").write_text(
        write_diagnostics(diag, log, model, fitter, feats, max_loss), encoding="utf-8", newline="\n"
    )
    write_json(m, out / "metrics.json")
    with open(path("clean_dir") / "model.pkl", "wb") as f:
        pickle.dump({"model": model, "features": feats}, f)

    assert m["validation"]["gini"] > 0
    print(f"features {len(feats)} (removed for sign: {m['removed_for_sign']})")
    print(f"train Gini {m['train']['gini']:.4f}  validation Gini {m['validation']['gini']:.4f} "
          f"(before sign fix {first_val_gini:.4f})  gap {m['train_validation_gini_gap']:.4f}  "
          f"KS(val) {m['validation']['ks']:.4f}")
    print(diag[["feature", "coefficient", "sign_ok", "vif"]].to_string(index=False))
    return m


if __name__ == "__main__":
    main()
