"""Shared helpers: config loading, paths, duckdb connection and JSON writing.

Every stage reads paths and parameters from config/ so that nothing is hardcoded.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import duckdb
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_settings() -> dict:
    with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_assumptions(path: Path | None = None) -> dict:
    with open(path or ROOT / "config" / "assumptions.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def path(key: str) -> Path:
    p = ROOT / load_settings()["paths"][key]
    if key in ("outputs", "web_data", "powerbi", "clean_dir"):
        p.mkdir(parents=True, exist_ok=True)
    return p


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    db = path("duckdb")
    db.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db), read_only=read_only)


def read_sql(name: str) -> str:
    return (ROOT / "sql" / name).read_text(encoding="utf-8")


def _clean(o):
    """Make numpy / NaN values JSON-safe (NaN and inf become null)."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def write_json(obj, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(_clean(obj), f, indent=2, sort_keys=False)
        f.write("\n")


def read_json(p: Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def write_csv(df, p: Path, float_format: str = "%.10g") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, float_format=float_format, lineterminator="\n")


def json_keys(o) -> set[str]:
    """All dictionary keys anywhere in a JSON structure (used to scan for ID fields)."""
    if isinstance(o, dict):
        return set(o) | set().union(*(json_keys(v) for v in o.values())) if o else set()
    if isinstance(o, list):
        return set().union(*(json_keys(v) for v in o)) if o else set()
    return set()
