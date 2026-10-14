"""Phase 12 — Power BI handoff: write every file the dashboard needs into powerbi/.

All files are regenerated from outputs/ on every pipeline run, so the dashboard never
carries a stale or hand-typed number. Column names are made dashboard-ready here:
`bad_rate` becomes `payment_difficulty_rate`, the term used on every visual.
"""

from __future__ import annotations

import json

import pandas as pd

from src.common import path, read_json, write_csv

# outputs/ file -> powerbi/ file (same name), copied with display-ready column names.
TABLES = [
    "segments.csv",
    "iv_summary.csv",
    "scorecard.csv",
    "score_distribution.csv",
    "cutoff_table.csv",
    "sensitivity.csv",
    "coefficients.csv",
]
RENAME = {"bad_rate": "payment_difficulty_rate"}

THEME = {
    "name": "Dev Mittal Analysis",
    "dataColors": ["#1E4E79", "#2E6B4F", "#B4552D", "#5E7A72", "#8A5A00", "#0F3B33"],
    "background": "#FAF6F0",
    "foreground": "#0F3B33",
    "tableAccent": "#2E6B4F",
    "good": "#2E6B4F",
    "neutral": "#8A5A00",
    "bad": "#B4552D",
}


def metrics_table() -> pd.DataFrame:
    """One row per split plus the full population. AUC/Gini/KS are blank for the full
    population because the model was fitted on part of it (no honest single figure)."""
    m = read_json(path("outputs") / "metrics.json")
    split = read_json(path("outputs") / "split_summary.json")
    base = read_json(path("outputs") / "baseline.json")
    rows = []
    for k in ("train", "validation", "test"):
        rows.append(
            {
                "split": k,
                "applications": split["splits"][k]["n"],
                "payment_difficulty_rate": split["splits"][k]["rate"],
                "auc": m[k]["auc"],
                "gini": m[k]["gini"],
                "ks": m[k]["ks"],
            }
        )
    rows.append(
        {
            "split": "full_population",
            "applications": base["applications"],
            "payment_difficulty_rate": base["baseline_rate"],
            "auc": None,
            "gini": None,
            "ks": None,
        }
    )
    return pd.DataFrame(rows)


def recommendation_table() -> pd.DataFrame:
    r = read_json(path("outputs") / "recommendation.json")
    rule = r["rule"].replace("<= max_difficulty_rate", f"<= {r['max_difficulty_rate']:.1%}")
    return pd.DataFrame(
        [
            {
                "cutoff": r["cutoff"],
                "rule": rule,
                "val_approval_rate": r["validation"]["approval_rate"],
                "val_payment_difficulty_rate": r["validation"]["bad_rate"],
                "test_approval_rate": r["test"]["approval_rate"],
                "test_payment_difficulty_rate": r["test"]["bad_rate"],
                # approve-everyone rate on the validation split, the comparison the cut-off was chosen against
                "baseline_payment_difficulty_rate": r["validation"]["baseline_rate"],
            }
        ]
    )


def main() -> list[str]:
    dest = path("powerbi")
    written = []
    for f in TABLES:
        df = pd.read_csv(path("outputs") / f).rename(columns=RENAME)
        write_csv(df, dest / f)
        written.append(f)
    write_csv(metrics_table(), dest / "metrics.csv")
    write_csv(recommendation_table(), dest / "recommendation.csv")
    with open(dest / "theme.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(THEME, fh, indent=2)
        fh.write("\n")
    written += ["metrics.csv", "recommendation.csv", "theme.json"]
    for f in written:
        print(f"wrote powerbi/{f}")
    return written


if __name__ == "__main__":
    main()
