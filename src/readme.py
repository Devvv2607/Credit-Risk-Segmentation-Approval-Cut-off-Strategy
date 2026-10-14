"""Render README.md from docs/README.template.md, filling every result from the outputs.

No figure in the README is typed by hand: claims come from claims_rendered.json and the
tables from metrics.json and recommendation.json.
"""

from __future__ import annotations

import yaml

from src.common import ROOT, path, read_json


def pct(v: float, d: int = 2) -> str:
    return f"{v * 100:.{d}f}%"


def main() -> None:
    out = path("outputs")
    m = read_json(out / "metrics.json")
    rec = read_json(out / "recommendation.json")
    base = read_json(out / "baseline.json")
    man = read_json(out / "data_manifest.json")
    val = read_json(out / "validation_report.json")
    claims = read_json(out / "claims_rendered.json")["claims"]
    site = yaml.safe_load((ROOT / "config" / "site.yaml").read_text(encoding="utf-8"))
    rows = {f["table"]: f["rows"] for f in man["files"]}

    metrics_rows = "\n".join(
        f"| {label} | {m[k]['auc']:.3f} | {m[k]['gini']:.3f} | {m[k]['ks']:.3f} |"
        for k, label in (("train", "Train"), ("validation", "Validation"), ("test", "Test (final)"))
    )
    metrics_rows += (
        f"\n| Benchmark (gradient boosting, test) | {m['benchmark']['test']['auc']:.3f} | "
        f"{m['benchmark']['test']['gini']:.3f} | {m['benchmark']['test']['ks']:.3f} |"
    )
    values = {
        "site_link": f"[{site['site_url']}]({site['site_url']})" if site.get("site_url") else "not yet deployed — add the Vercel URL to `config/site.yaml`",
        "applications": f"{base['applications']:,}",
        "bureau_rows": f"{rows['raw_bureau']:,}",
        "prev_rows": f"{rows['raw_previous_application']:,}",
        "min_segment": f"{base['min_segment_size']:,}",
        "claims": "\n".join(f"- {c['text']} <sub>`{c['id']}`</sub>" for c in claims),
        "metrics_rows": metrics_rows,
        "cutoff": str(rec["cutoff"]),
        "rule": rec["rule"].replace("<= max_difficulty_rate", f"≤ {pct(rec['max_difficulty_rate'], 1)}"),
        "val_approval": pct(rec["validation"]["approval_rate"], 1),
        "test_approval": pct(rec["test"]["approval_rate"], 1),
        "val_rate": pct(rec["validation"]["bad_rate"]),
        "test_rate": pct(rec["test"]["bad_rate"]),
        "val_base": pct(rec["validation"]["baseline_rate"]),
        "test_base": pct(rec["test"]["baseline_rate"]),
        "checks": f"{val['passed']}/{val['total']}",
    }
    text = (ROOT / "docs" / "README.template.md").read_text(encoding="utf-8")
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    assert "{{" not in text, "unfilled README placeholder"
    (ROOT / "README.md").write_text(text, encoding="utf-8", newline="\n")
    print("README.md rendered")


if __name__ == "__main__":
    main()
