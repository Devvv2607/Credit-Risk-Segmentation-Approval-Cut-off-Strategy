import numpy as np

from src.common import path, read_json


def test_manifest_counts_match_tables(con, out):
    for f in read_json(out / "data_manifest.json")["files"]:
        assert con.execute(f"SELECT COUNT(*) FROM {f['table']}").fetchone()[0] == f["rows"]


def test_manifest_counts_match_fresh_csv_count(out):
    """Count data lines in each raw CSV independently of DuckDB."""
    raw = path("raw_dir")
    for f in read_json(out / "data_manifest.json")["files"]:
        with open(raw / f["file"], "rb") as fh:
            lines = sum(buf.count(b"\n") for buf in iter(lambda: fh.read(1 << 24), b""))
        assert lines - 1 == f["rows"]


def test_model_table_ids_unique(con):
    n, u = con.execute("SELECT COUNT(*), COUNT(DISTINCT SK_ID_CURR) FROM model_table").fetchone()
    assert n == u


def test_target_binary(con):
    vals = {r[0] for r in con.execute("SELECT DISTINCT TARGET FROM model_table").fetchall()}
    assert vals == {0, 1}


def test_baseline_matches_metrics(con, metrics, out):
    rate = con.execute("SELECT AVG(TARGET) FROM model_table").fetchone()[0]
    assert abs(rate - metrics["baseline_rate"]) < 1e-12
    assert abs(rate - read_json(out / "baseline.json")["baseline_rate"]) < 1e-12


def test_no_infinite_engineered_features(con):
    cols = ["annuity_to_income", "credit_to_income", "credit_to_goods", "employed_to_age",
            "age_years", "years_employed", "bureau_debt_to_credit", "prev_refusal_rate"]
    df = con.execute(f"SELECT {', '.join(cols)} FROM model_table").df()
    assert not np.isinf(df.to_numpy(dtype=float)).any()


def test_anomaly_flag_and_null(con):
    flagged, nonnull = con.execute(
        "SELECT SUM(flag_days_employed_anomaly), COUNT(*) FILTER (WHERE flag_days_employed_anomaly = 1 "
        "AND DAYS_EMPLOYED IS NOT NULL) FROM model_table"
    ).fetchone()
    assert flagged > 0 and nonnull == 0


def test_no_history_gets_null_amounts(con):
    n = con.execute(
        "SELECT COUNT(*) FROM model_table WHERE has_bureau_history = 0 AND "
        "(bureau_total_overdue IS NOT NULL OR bureau_debt_to_credit IS NOT NULL)"
    ).fetchone()[0]
    assert n == 0
