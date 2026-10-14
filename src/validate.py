"""Phase 11 — End-to-end consistency checks.

Re-derives key facts from the local data and checks that every stage agrees with every
other: manifest vs tables, split integrity, one baseline everywhere, model and scorecard
arithmetic, cut-off rules, claims vs metrics, and that no applicant-level data leaked
into outputs/ or web/public/data/. Prints a pass/fail table and writes
outputs/validation_report.json (the count of passing checks is shown on the site).
"""

from __future__ import annotations

import json
import sys

import pandas as pd
from scipy.stats import spearmanr

from src.common import connect, json_keys, load_settings, path, read_json, write_json

# An aggregated output never needs anywhere near this many rows; applicant-level tables would.
MAX_AGGREGATE_ROWS = 5000
ID_COLUMNS = {"SK_ID_CURR", "SK_ID_PREV", "SK_ID_BUREAU"}


class Report:
    def __init__(self):
        self.rows = []

    def check(self, name: str, fn):
        try:
            ok, detail = fn()
        except Exception as e:  # a crashing check is a failing check
            ok, detail = False, f"{type(e).__name__}: {e}"
        self.rows.append({"check": name, "status": "pass" if ok else "fail", "detail": str(detail)})


def scan_for_applicant_data(folder) -> list[str]:
    problems = []
    for p in sorted(folder.rglob("*")):
        if p.suffix == ".csv":
            df = pd.read_csv(p, nrows=MAX_AGGREGATE_ROWS + 1)
            if ID_COLUMNS & set(df.columns):
                problems.append(f"{p.name}: id column")
            if len(df) > MAX_AGGREGATE_ROWS:
                problems.append(f"{p.name}: > {MAX_AGGREGATE_ROWS} rows")
        elif p.suffix == ".json":
            data = json.loads(p.read_text(encoding="utf-8"))
            if json_keys(data) & ID_COLUMNS:
                problems.append(f"{p.name}: id field")
            rows = data if isinstance(data, list) else next((v for v in data.values() if isinstance(v, list) and len(v) > MAX_AGGREGATE_ROWS), [])
            if isinstance(rows, list) and len(rows) > MAX_AGGREGATE_ROWS:
                problems.append(f"{p.name}: > {MAX_AGGREGATE_ROWS} records")
        elif p.suffix == ".parquet":
            problems.append(f"{p.name}: parquet file in published folder")
    return problems


def main() -> int:
    s = load_settings()
    out = path("outputs")
    con = connect(read_only=True)
    q = lambda sql: con.execute(sql).fetchone()[0]  # noqa: E731
    R = Report()

    manifest = read_json(out / "data_manifest.json")
    baseline = read_json(out / "baseline.json")
    metrics = read_json(out / "metrics.json")
    rec = read_json(out / "recommendation.json")
    split_summary = read_json(out / "split_summary.json")
    sel = read_json(out / "selected_features.json")
    seg = pd.read_csv(out / "segments.csv")
    cut = pd.read_csv(out / "cutoff_table.csv")
    iv = pd.read_csv(out / "iv_summary.csv")
    coefs = pd.read_csv(out / "coefficients.csv")
    sc_sum = read_json(out / "scorecard_summary.json")
    ids = pd.read_parquet(path("clean_dir") / "split_ids.parquet")
    scores = pd.read_parquet(path("clean_dir") / "scores.parquet")

    # --- ingest / features
    for f in manifest["files"]:
        R.check(f"manifest rows match table {f['table']}",
                lambda f=f: (q(f"SELECT COUNT(*) FROM {f['table']}") == f["rows"], f["rows"]))
    R.check("SK_ID_CURR unique in application_train",
            lambda: (q("SELECT COUNT(*) - COUNT(DISTINCT SK_ID_CURR) FROM raw_application_train") == 0, "unique"))
    R.check("model table rows equal application rows",
            lambda: (q("SELECT COUNT(*) FROM model_table") == q("SELECT COUNT(*) FROM raw_application_train"),
                     q("SELECT COUNT(*) FROM model_table")))
    R.check("TARGET only contains 0 and 1",
            lambda: (q("SELECT COUNT(*) FROM model_table WHERE TARGET NOT IN (0, 1)") == 0, "{0,1}"))

    # --- split
    def split_integrity():
        sets = {k: set(g["SK_ID_CURR"]) for k, g in ids.groupby("split")}
        pop = set(con.execute("SELECT SK_ID_CURR FROM model_table").df()["SK_ID_CURR"])
        exclusive = all(not (sets[a] & sets[b]) for a in sets for b in sets if a < b)
        return exclusive and set().union(*sets.values()) == pop, f"{len(pop):,} ids in 3 exclusive splits"
    R.check("split ids exclusive and cover the population", split_integrity)
    R.check("split rates within tolerance of baseline",
            lambda: (all(abs(v["gap_pp_vs_baseline"]) < s["split"]["max_rate_gap_pp"]
                         for v in split_summary["splits"].values()), "all within limit"))
    R.check("split summary sizes match split ids",
            lambda: (all(split_summary["splits"][k]["n"] == int((ids["split"] == k).sum())
                         for k in ("train", "validation", "test")), "sizes agree"))

    # --- one baseline everywhere
    true_rate = q("SELECT AVG(TARGET) FROM model_table")
    R.check("baseline.json matches recomputed rate", lambda: (abs(baseline["baseline_rate"] - true_rate) < 1e-12, true_rate))
    R.check("metrics.json baseline matches", lambda: (abs(metrics["baseline_rate"] - true_rate) < 1e-12, "agree"))
    R.check("split summary baseline matches", lambda: (abs(split_summary["baseline_rate"] - true_rate) < 1e-12, "agree"))
    R.check("cut-off table minimum equals validation baseline",
            lambda: (cut.iloc[0]["approval_rate"] == 1.0
                     and abs(cut.iloc[0]["bad_rate"] - split_summary["splits"]["validation"]["rate"]) < 1e-9,
                     cut.iloc[0]["bad_rate"]))

    # --- segments
    def seg_weighted():
        comp = seg[seg["dimension_complete"]]
        w = (comp["bad_rate"] * comp["n"]).groupby(comp["dimension"]).sum() / comp.groupby("dimension")["n"].sum()
        return bool((w - true_rate).abs().max() < 1e-9), f"{len(w)} complete dimensions"
    R.check("segment weighted rate equals baseline (complete dimensions)", seg_weighted)
    R.check("segments meet minimum size", lambda: (bool((seg["n"] >= s["segments"]["min_segment_size"]).all()), seg["n"].min()))
    R.check("Wilson intervals contain the estimate",
            lambda: (bool(((seg["ci_low"] <= seg["bad_rate"]) & (seg["bad_rate"] <= seg["ci_high"])).all()), "ok"))

    # --- binning / model
    R.check("binning fit on train only",
            lambda: (sel["fit_n"] == split_summary["splits"]["train"]["n"], sel["fit_n"]))
    R.check("no protected attribute selected",
            lambda: (not set(sel["selected"]) & set(s["protected_attributes"]), s["protected_attributes"]))
    R.check("selected features meet IV threshold",
            lambda: (bool((iv.loc[iv["decision"] == "selected", "iv"] >= s["binning"]["iv_min"]).all()), "ok"))
    R.check("model features are a subset of selected features",
            lambda: (set(metrics["features"]) <= set(sel["selected"]), len(metrics["features"])))

    def signs():
        diag_text = (out / "coefficient_diagnostics.md").read_text(encoding="utf-8")
        wrong = coefs[(coefs["feature"] != "(intercept)") & (coefs["coefficient"] >= 0)]["feature"].tolist()
        return all(w in diag_text for w in wrong) and wrong == metrics["unexpected_signs_remaining"], wrong or "all negative"
    R.check("unexpected coefficient signs documented", signs)
    for split in ("train", "validation", "test"):
        R.check(f"Gini = 2*AUC - 1 ({split})",
                lambda split=split: (abs(metrics[split]["gini"] - (2 * metrics[split]["auc"] - 1)) < 1e-12,
                                     round(metrics[split]["gini"], 4)))
    R.check("train-validation Gini gap below 0.05",
            lambda: (abs(metrics["train_validation_gini_gap"]) < 0.05, round(metrics["train_validation_gini_gap"], 4)))
    R.check("test metrics present and labelled final",
            lambda: (metrics["test"] is not None and "final" in metrics["test"]["label"], "present"))

    # --- scorecard
    R.check("points reproduce scores", lambda: (sc_sum["max_abs_score_vs_points_difference"] < 1e-8,
                                                sc_sum["max_abs_score_vs_points_difference"]))
    for split in ("validation", "test"):
        d = scores[scores["split"] == split]
        R.check(f"score strictly decreasing in probability ({split})",
                lambda d=d: (spearmanr(d["score"], d["p_bad"]).statistic <= -1 + 1e-12, "Spearman = -1"))

    # --- cut-off
    R.check("approval rate non-increasing with cut-off",
            lambda: (bool((cut["approval_rate"].diff().dropna() <= 0).all()), "monotonic"))
    def rule():
        ok = cut[(cut["approved"] > 0) & (cut["bad_rate"] <= s["cutoff"]["max_difficulty_rate"])]
        best = ok.sort_values(["profit", "cutoff"], ascending=[False, True]).iloc[0]
        return int(best["cutoff"]) == rec["cutoff"] and rec["validation"]["bad_rate"] <= s["cutoff"]["max_difficulty_rate"], rec["cutoff"]
    R.check("recommendation satisfies declared rule", rule)
    R.check("recommendation has validation and test figures",
            lambda: (rec.get("validation") is not None and rec.get("test") is not None, "both present"))
    def test_fig():
        d = scores[scores["split"] == "test"]
        a = d["score"] >= rec["cutoff"]
        return abs(a.mean() - rec["test"]["approval_rate"]) < 1e-12 and abs(d.loc[a, "TARGET"].mean() - rec["test"]["bad_rate"]) < 1e-12, "recomputed"
    R.check("test cut-off figures recompute", test_fig)

    # --- claims
    def claims_ok():
        from src import claims as C
        C._load.cache_clear()
        reg = C.load_registry()
        rendered = {c["id"]: c for c in read_json(out / "claims_rendered.json")["claims"]}
        for c in reg["claims"]:
            text, values = C.render(c["template"], c["metrics"])
            if rendered[c["id"]]["text"] != text:
                return False, f"{c['id']} differs"
            for v in values.values():
                if v["formatted"] not in text:
                    return False, f"{c['id']} missing value"
        return len(rendered) == len(reg["claims"]), f"{len(rendered)} claims"
    R.check("rendered claims match metrics", claims_ok)

    # --- privacy
    R.check("no applicant-level data in outputs/", lambda: (not (p := scan_for_applicant_data(out)), p or "clean"))
    web = path("web_data")
    R.check("no applicant-level data in web/public/data/", lambda: (not (p := scan_for_applicant_data(web)), p or "clean"))
    con.close()

    passed = sum(r["status"] == "pass" for r in R.rows)
    write_json({"passed": passed, "total": len(R.rows), "all_passed": passed == len(R.rows), "checks": R.rows},
               out / "validation_report.json")
    w = max(len(r["check"]) for r in R.rows)
    for r in R.rows:
        print(f"{r['status'].upper():<5} {r['check']:<{w}}  {r['detail']}")
    print(f"\n{passed}/{len(R.rows)} checks passed")
    return 0 if passed == len(R.rows) else 1


if __name__ == "__main__":
    sys.exit(main())
