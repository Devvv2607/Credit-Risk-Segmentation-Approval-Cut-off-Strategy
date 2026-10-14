"""Phase 13 — Export the JSON the website reads (web/public/data/) and the CSV downloads.

The site renders every figure from these files; nothing numeric is typed into page copy.
Only aggregated outputs are exported — never applicant-level rows.
"""

from __future__ import annotations

import shutil

import pandas as pd
import yaml

from src.common import ROOT, load_assumptions, load_settings, path, read_json, write_json

CSV_TO_JSON = [
    "segments",
    "iv_summary",
    "bins",
    "scorecard",
    "score_distribution",
    "roc_points",
    "ks_curve",
    "cutoff_table",
    "sensitivity",
    "coefficients",
]
JSON_COPY = [
    "metrics",
    "recommendation",
    "claims_rendered",
    "validation_report",
    "split_summary",
    "baseline",
    "scorecard_summary",
]
DOWNLOADS = ["segments.csv", "iv_summary.csv", "scorecard.csv", "cutoff_table.csv", "sensitivity.csv",
             "score_distribution.csv", "metrics.json", "claims_rendered.json", "recommendation.json"]

SOURCES = [
    {
        "file": "application_train.csv",
        "title": "Application data (application_train)",
        "publisher": "Home Credit Group, via Kaggle",
        "url": "https://www.kaggle.com/competitions/home-credit-default-risk/data",
        "fields_used": [
            "TARGET", "EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3", "DAYS_BIRTH", "DAYS_EMPLOYED",
            "AMT_INCOME_TOTAL", "AMT_CREDIT", "AMT_ANNUITY", "AMT_GOODS_PRICE", "NAME_CONTRACT_TYPE",
            "NAME_INCOME_TYPE", "NAME_EDUCATION_TYPE", "OCCUPATION_TYPE", "ORGANIZATION_TYPE",
            "REGION_RATING_CLIENT", "REGION_RATING_CLIENT_W_CITY", "DAYS_LAST_PHONE_CHANGE",
        ],
        "fields_note": "Shown: fields used in segmentation or the final scorecard. Every other non-protected "
                       "column was evaluated as a binning candidate (see iv_summary.csv).",
        "licence": "Kaggle competition data; use subject to the competition rules (no redistribution of raw data)",
        "access": "Kaggle CLI: kaggle competitions download -c home-credit-default-risk",
        "limitations": "Only loans that were granted have outcomes (no rejected applicants); no application "
                       "dates; country not disclosed and not Indian lending data; TARGET is a payment-difficulty "
                       "flag, not a full default definition.",
    },
    {
        "file": "bureau.csv",
        "title": "Credit bureau records (bureau)",
        "publisher": "Home Credit Group, via Kaggle",
        "url": "https://www.kaggle.com/competitions/home-credit-default-risk/data",
        "fields_used": ["CREDIT_ACTIVE", "AMT_CREDIT_SUM", "AMT_CREDIT_SUM_DEBT", "AMT_CREDIT_SUM_OVERDUE",
                        "CREDIT_DAY_OVERDUE"],
        "fields_note": "Aggregated per applicant: credit counts, overdue amounts and debt-to-credit ratio.",
        "licence": "Kaggle competition data; use subject to the competition rules",
        "access": "Same Kaggle download",
        "limitations": "Covers only applicants with a bureau record; others are flagged as having no bureau "
                       "history rather than a clean one. Reporting completeness across institutions is unknown.",
    },
    {
        "file": "previous_application.csv",
        "title": "Previous Home Credit applications (previous_application)",
        "publisher": "Home Credit Group, via Kaggle",
        "url": "https://www.kaggle.com/competitions/home-credit-default-risk/data",
        "fields_used": ["NAME_CONTRACT_STATUS"],
        "fields_note": "Aggregated per applicant: count of previous applications, refusals and refusal rate.",
        "licence": "Kaggle competition data; use subject to the competition rules",
        "access": "Same Kaggle download",
        "limitations": "Only applications made to Home Credit itself; refusal reasons are not modelled.",
    },
]


def main() -> None:
    out, web = path("outputs"), path("web_data")
    for name in CSV_TO_JSON:
        df = pd.read_csv(out / f"{name}.csv")
        write_json(df.astype(object).where(df.notna(), None).to_dict(orient="records"), web / f"{name}.json")
    for name in JSON_COPY:
        write_json(read_json(out / f"{name}.json"), web / f"{name}.json")

    manifest = read_json(out / "data_manifest.json")
    write_json(manifest, web / "data_manifest.json")
    for src in SOURCES:
        f = next(x for x in manifest["files"] if x["file"] == src["file"])
        src.update({"rows": f["rows"], "columns": f["columns"], "sha256": f["sha256"],
                    "retrieved": manifest["loaded_at"][:10]})
    write_json(SOURCES, web / "sources.json")

    a = load_assumptions()
    write_json(a, web / "assumptions.json")

    s = load_settings()
    sel = read_json(out / "selected_features.json")
    write_json(
        {
            "seed": s["seed"],
            "split": s["split"],
            "min_segment_size": s["segments"]["min_segment_size"],
            "binning": s["binning"],
            "protected_attributes": s["protected_attributes"],
            "cutoff": s["cutoff"],
            "scorecard": s["scorecard"],
            "candidates_evaluated": sel["candidates_evaluated"],
            "selected_by_binning": len(sel["selected"]),
            "woe_convention": sel["woe_convention"],
            "sign_check": sel["sign_check"],
            "leak_flags": sel["leak_flags"],
            "python_version": "3.11",
        },
        web / "settings.json",
    )

    with open(ROOT / "config" / "site.yaml", encoding="utf-8") as f:
        site = yaml.safe_load(f)
    site["data_loaded"] = manifest["loaded_at"]
    write_json(site, web / "site.json")

    dl = ROOT / "web" / "public" / "downloads"
    dl.mkdir(parents=True, exist_ok=True)
    for f in DOWNLOADS:
        shutil.copyfile(out / f, dl / f)
    print(f"wrote {len(list(web.glob('*.json')))} JSON files to {web} and {len(DOWNLOADS)} downloads")


if __name__ == "__main__":
    main()
