"""The Power BI guide must only reference files and columns that exist in powerbi/."""

import json
import re

import pandas as pd
import pytest

from src.common import path, read_json
from src.powerbi import THEME

GUIDE = path("powerbi") / "POWERBI_GUIDE.md"
# Tables created inside Power BI by the guide itself, not loaded from files.
CREATED_IN_PBI = {"Cutoff", "_Measures"}


def guide_text() -> str:
    return GUIDE.read_text(encoding="utf-8")


def referenced_files() -> set[str]:
    return set(re.findall(r"`([\w-]+\.(?:csv|json))`", guide_text()))


def referenced_columns() -> set[tuple[str, str]]:
    """Every Table[column] reference, e.g. cutoff_table[approval_rate]."""
    return set(re.findall(r"\b([A-Za-z_]\w*)\[(\w+)\]", guide_text()))


def test_every_referenced_file_exists():
    files = referenced_files()
    assert files, "guide references no files"
    for f in files:
        assert (path("powerbi") / f).exists(), f"guide references missing powerbi/{f}"


def test_every_column_reference_exists():
    refs = referenced_columns()
    assert refs
    for table, col in refs:
        if table in CREATED_IN_PBI:
            continue
        f = path("powerbi") / f"{table}.csv"
        assert f.exists(), f"guide uses table {table} but powerbi/{table}.csv does not exist"
        assert col in pd.read_csv(f, nrows=0).columns, f"{table}.csv has no column {col}"


def test_files_table_lists_exact_columns():
    """The column list in the guide's Files table matches each CSV header exactly."""
    for line in guide_text().splitlines():
        m = re.match(r"\| `([\w-]+\.csv)` \|[^|]*\| (.*) \|$", line)
        if not m:
            continue
        listed = re.findall(r"`(\w+)`", m.group(2))
        actual = list(pd.read_csv(path("powerbi") / m.group(1), nrows=0).columns)
        assert listed == actual, m.group(1)


def test_metrics_csv_shape():
    df = pd.read_csv(path("powerbi") / "metrics.csv")
    assert list(df.columns) == ["split", "applications", "payment_difficulty_rate", "auc", "gini", "ks"]
    assert df["split"].tolist() == ["train", "validation", "test", "full_population"]
    full = df.set_index("split").loc["full_population"]
    assert pd.isna(full["auc"]) and pd.isna(full["gini"]) and pd.isna(full["ks"])
    m = read_json(path("outputs") / "metrics.json")
    for k in ("train", "validation", "test"):
        row = df.set_index("split").loc[k]
        assert row["applications"] == m[k]["n"]
        assert row["gini"] == pytest.approx(m[k]["gini"], abs=1e-9)
    assert full["payment_difficulty_rate"] == pytest.approx(m["baseline_rate"], abs=1e-9)


def test_recommendation_csv_shape():
    df = pd.read_csv(path("powerbi") / "recommendation.csv")
    assert list(df.columns) == [
        "cutoff", "rule", "val_approval_rate", "val_payment_difficulty_rate",
        "test_approval_rate", "test_payment_difficulty_rate", "baseline_payment_difficulty_rate",
    ]
    assert len(df) == 1
    r = read_json(path("outputs") / "recommendation.json")
    assert df.loc[0, "cutoff"] == r["cutoff"]
    assert df.loc[0, "test_payment_difficulty_rate"] == pytest.approx(r["test"]["bad_rate"], abs=1e-9)


def test_theme_is_exact():
    with open(path("powerbi") / "theme.json", encoding="utf-8") as f:
        assert json.load(f) == THEME
    assert THEME == {
        "name": "Dev Mittal Analysis",
        "dataColors": ["#1E4E79", "#2E6B4F", "#B4552D", "#5E7A72", "#8A5A00", "#0F3B33"],
        "background": "#FAF6F0", "foreground": "#0F3B33", "tableAccent": "#2E6B4F",
        "good": "#2E6B4F", "neutral": "#8A5A00", "bad": "#B4552D",
    }


def test_no_internal_rate_name_in_powerbi_files():
    for f in path("powerbi").glob("*.csv"):
        assert "bad_rate" not in pd.read_csv(f, nrows=0).columns, f.name
