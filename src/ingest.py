"""Phase 1 — Ingest.

Loads the three raw CSVs into DuckDB exactly as downloaded (raw_* tables) and writes
outputs/data_manifest.json with row/column counts and a sha256 per file, so anyone can
confirm they are analysing the same Kaggle snapshot.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from src.common import connect, load_settings, path, read_json, write_json


def sha256(p, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    s = load_settings()
    raw = path("raw_dir")
    con = connect()
    files = []
    for table, fname in s["raw_files"].items():
        fp = raw / fname
        print(f"loading {fname} ...")
        con.execute(
            f"CREATE OR REPLACE TABLE raw_{table} AS "
            f"SELECT * FROM read_csv('{fp.as_posix()}', header=true, sample_size=-1)"
        )
        rows = con.execute(f"SELECT COUNT(*) FROM raw_{table}").fetchone()[0]
        cols = len(con.execute(f"DESCRIBE raw_{table}").fetchall())
        files.append(
            {
                "file": fname,
                "table": f"raw_{table}",
                "rows": rows,
                "columns": cols,
                "bytes": fp.stat().st_size,
                "sha256": sha256(fp),
            }
        )
    con.close()
    # Keep the original load time when the raw files are byte-identical, so re-running the
    # pipeline on the same data produces an identical manifest (determinism rule).
    loaded_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    prev_path = path("outputs") / "data_manifest.json"
    if prev_path.exists():
        prev = read_json(prev_path)
        same = [(f["file"], f["sha256"]) for f in prev.get("files", [])] == [(f["file"], f["sha256"]) for f in files]
        if same:
            loaded_at = prev["loaded_at"]
    manifest = {
        "dataset": "Home Credit Default Risk (Kaggle competition)",
        "source_url": "https://www.kaggle.com/competitions/home-credit-default-risk/data",
        "loaded_at": loaded_at,
        "files": files,
    }
    write_json(manifest, path("outputs") / "data_manifest.json")
    for f in files:
        print(f"{f['file']}: {f['rows']:,} rows x {f['columns']} cols")


if __name__ == "__main__":
    main()
