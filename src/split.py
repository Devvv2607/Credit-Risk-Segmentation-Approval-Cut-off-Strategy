"""Phase 5 — Stratified 60/20/20 train / validation / test split (seed 42).

Train fits bins and the model; validation chooses the cut-off; test is opened once at
the end. Stratifying on TARGET keeps the payment-difficulty rate equal across splits.
Applicant IDs and split labels are written to data/clean only (never to outputs/).
"""

from __future__ import annotations

import pandas as pd
from sklearn.model_selection import train_test_split

from src.common import connect, load_settings, path, write_json


def main() -> dict:
    s = load_settings()
    seed = s["seed"]
    r = s["split"]
    con = connect()
    df = con.execute("SELECT SK_ID_CURR, TARGET FROM model_table ORDER BY SK_ID_CURR").df()

    train, rest = train_test_split(
        df, train_size=r["train"], stratify=df["TARGET"], random_state=seed
    )
    val_share = r["validation"] / (r["validation"] + r["test"])
    val, test = train_test_split(
        rest, train_size=val_share, stratify=rest["TARGET"], random_state=seed
    )
    ids = pd.concat(
        [train.assign(split="train"), val.assign(split="validation"), test.assign(split="test")]
    )[["SK_ID_CURR", "split"]].sort_values("SK_ID_CURR").reset_index(drop=True)
    ids.to_parquet(path("clean_dir") / "split_ids.parquet", index=False)
    con.register("split_df", ids)
    con.execute("CREATE OR REPLACE TABLE split_ids AS SELECT * FROM split_df")
    con.close()

    baseline = df["TARGET"].mean()
    summary = {"population": len(df), "baseline_rate": baseline, "splits": {}}
    for name, part in (("train", train), ("validation", val), ("test", test)):
        summary["splits"][name] = {
            "n": len(part),
            "share": len(part) / len(df),
            "bads": int(part["TARGET"].sum()),
            "rate": part["TARGET"].mean(),
            "gap_pp_vs_baseline": (part["TARGET"].mean() - baseline) * 100,
        }
    for name, v in summary["splits"].items():
        assert abs(v["gap_pp_vs_baseline"]) < r["max_rate_gap_pp"], f"{name} rate drifts from baseline"
    write_json(summary, path("outputs") / "split_summary.json")
    for name, v in summary["splits"].items():
        print(f"{name:<10} n={v['n']:>7,}  rate={v['rate']:.4%}")
    return summary


if __name__ == "__main__":
    main()
