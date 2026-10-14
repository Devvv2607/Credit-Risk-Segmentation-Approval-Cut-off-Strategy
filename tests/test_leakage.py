import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from src import binning, cutoff
from src.common import connect, json_keys, load_assumptions, load_settings, path, read_json
from src.model import fit_lr

ID_COLS = {"SK_ID_CURR", "SK_ID_PREV", "SK_ID_BUREAU"}


def test_split_ids_exclusive_and_complete(con):
    ids = pd.read_parquet(path("clean_dir") / "split_ids.parquet")
    sets = {k: set(g["SK_ID_CURR"]) for k, g in ids.groupby("split")}
    assert set(sets) == {"train", "validation", "test"}
    assert not (sets["train"] & sets["validation"])
    assert not (sets["train"] & sets["test"])
    assert not (sets["validation"] & sets["test"])
    pop = set(con.execute("SELECT SK_ID_CURR FROM model_table").df()["SK_ID_CURR"])
    assert set().union(*sets.values()) == pop


def test_binning_fit_on_train_ids_only(out):
    sel = read_json(out / "selected_features.json")
    meta = read_json(path("clean_dir") / "binning_fit_meta.json")
    split = read_json(out / "split_summary.json")
    assert sel["fit_n"] == meta["fit_n"] == split["splits"]["train"]["n"]
    ids = pd.read_parquet(path("clean_dir") / "split_ids.parquet")
    train_ids = np.sort(ids.loc[ids["split"] == "train", "SK_ID_CURR"].to_numpy())
    assert hashlib.sha256(train_ids.tobytes()).hexdigest() == meta["fit_ids_sha256"]


@pytest.fixture(scope="module")
def small_frame():
    s = load_settings()
    c = connect(read_only=True)
    df = binning.load_model_frame(c)
    c.close()
    return df.sample(n=20000, random_state=s["seed"]).reset_index(drop=True), s


def _fit(df, s, feats):
    categorical = [f for f in feats if df[f].dtype == object]
    bp, train = binning.fit_on_train(df, feats, categorical, s)
    tables = {f: binning.bin_table(bp, f) for f in feats}
    X = binning.woe_transform(bp, tables, train, feats)
    model = fit_lr(X, train["TARGET"].to_numpy(), s["seed"], s["model"]["max_iter"])
    return tables, model


def test_non_train_targets_do_not_change_bins_or_coefficients(small_frame):
    df, s = small_frame
    feats = ["EXT_SOURCE_3", "years_employed", "OCCUPATION_TYPE"]
    t1, m1 = _fit(df, s, feats)
    flipped = df.copy()
    mask = flipped["split"] != "train"
    flipped.loc[mask, "TARGET"] = 1 - flipped.loc[mask, "TARGET"]
    t2, m2 = _fit(flipped, s, feats)
    for f in feats:
        pd.testing.assert_frame_equal(t1[f], t2[f])
    np.testing.assert_array_equal(m1.coef_, m2.coef_)
    np.testing.assert_array_equal(m1.intercept_, m2.intercept_)


def test_test_targets_do_not_change_cutoff(scores):
    s, a = load_settings(), load_assumptions()
    _, _, r1 = cutoff.validation_cutoffs(scores, s, a)
    flipped = scores.copy()
    mask = flipped["split"] == "test"
    flipped.loc[mask, "TARGET"] = 1 - flipped.loc[mask, "TARGET"]
    _, _, r2 = cutoff.validation_cutoffs(flipped, s, a)
    assert r1["cutoff"] == r2["cutoff"] == read_json(path("outputs") / "recommendation.json")["cutoff"]


@pytest.mark.parametrize("folder", ["outputs", "web_data"])
def test_no_applicant_level_data_published(folder):
    root = path(folder)
    files = [p for p in root.rglob("*") if p.suffix in (".csv", ".json", ".parquet")]
    assert files, f"nothing to scan in {root}"
    for p in files:
        assert p.suffix != ".parquet", p
        if p.suffix == ".csv":
            df = pd.read_csv(p)
            assert not ID_COLS & set(df.columns), p
            assert len(df) <= 5000, f"{p} looks applicant-level ({len(df)} rows)"
        else:
            data = json.loads(p.read_text(encoding="utf-8"))
            assert not json_keys(data) & ID_COLS, p
            if isinstance(data, list):
                assert len(data) <= 5000, p


def test_no_applicant_level_downloads():
    downloads = path("web_data").parent / "downloads"
    for p in downloads.glob("*.csv"):
        df = pd.read_csv(p)
        assert not ID_COLS & set(df.columns), p
        assert len(df) <= 5000, p
