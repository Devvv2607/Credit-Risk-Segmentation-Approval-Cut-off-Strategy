import filecmp
import shutil

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from src import model as model_step
from src.common import path, read_json


def test_no_protected_attribute(settings, out, metrics):
    sel = read_json(out / "selected_features.json")
    iv_features = pd.read_csv(out / "iv_summary.csv")["feature"].tolist()
    for p in settings["protected_attributes"]:
        assert p not in sel["selected"]
        assert p not in metrics["features"]
        assert p not in iv_features


def test_selected_features_meet_iv(out, settings):
    iv = pd.read_csv(out / "iv_summary.csv")
    assert (iv.loc[iv["decision"] == "selected", "iv"] >= settings["binning"]["iv_min"]).all()


def test_diagnostics_cover_unexpected_signs(out, metrics):
    text = (out / "coefficient_diagnostics.md").read_text(encoding="utf-8")
    coefs = pd.read_csv(out / "coefficients.csv")
    wrong = coefs[(coefs["feature"] != "(intercept)") & (coefs["coefficient"] >= 0)]["feature"]
    for f in wrong:
        assert f in text
    for f in metrics["removed_for_sign"]:
        assert "### Step" in text and f in text
    assert "Unexpected signs remaining in the final model" in text


def _ks(y, p):
    """KS = max(TPR - FPR), evaluated at every distinct threshold."""
    order = np.argsort(-p, kind="mergesort")
    y, ps = np.asarray(y)[order], p[order]
    tpr = np.cumsum(y) / y.sum()
    fpr = np.cumsum(1 - y) / (1 - y).sum()
    last = np.r_[ps[1:] != ps[:-1], True]
    return np.max(tpr[last] - fpr[last])


def test_gini_and_ks_recomputed(scores, metrics):
    for split in ("train", "validation", "test"):
        d = scores[scores["split"] == split]
        auc = roc_auc_score(d["TARGET"], d["p_bad"])
        assert abs(metrics[split]["auc"] - auc) < 1e-12
        assert abs(metrics[split]["gini"] - (2 * auc - 1)) < 1e-12
        assert abs(metrics[split]["ks"] - _ks(d["TARGET"].to_numpy(), d["p_bad"].to_numpy())) < 1e-9


def test_test_metrics_present_and_final(metrics):
    assert metrics["test"] is not None and "final" in metrics["test"]["label"]
    assert metrics["validation"]["gini"] > 0
    assert abs(metrics["train_validation_gini_gap"]) < 0.05


def test_model_step_deterministic(tmp_path):
    """Run the model step twice; outputs must be byte-identical. Originals are restored."""
    out = path("outputs")
    produced = [out / "metrics.json", out / "coefficients.csv", out / "coefficient_diagnostics.md"]
    files = produced + [path("clean_dir") / "model.pkl"]
    backup = tmp_path / "backup"
    backup.mkdir()
    for f in files:
        shutil.copy2(f, backup / f.name)
    try:
        runs = []
        for i in range(2):
            model_step.main()
            d = tmp_path / f"run{i}"
            d.mkdir()
            for f in produced:
                shutil.copy2(f, d / f.name)
            runs.append(d)
        for f in produced:
            assert filecmp.cmp(runs[0] / f.name, runs[1] / f.name, shallow=False), f.name
    finally:
        for f in files:
            shutil.copy2(backup / f.name, f)
