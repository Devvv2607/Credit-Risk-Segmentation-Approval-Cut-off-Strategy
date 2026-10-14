"""Cross-platform task runner mirroring the Makefile, for machines without `make`.

Usage: python tasks.py <target> [<target> ...]   e.g. python tasks.py all
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = str(ROOT / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python"))
NPM = "npm.cmd" if os.name == "nt" else "npm"

STAGES = {
    "data-check": "src.data_check", "ingest": "src.ingest", "clean": "src.clean",
    "segments": "src.segments", "features": "src.features", "split": "src.split",
    "binning": "src.binning", "model": "src.model", "scorecard": "src.scorecard",
    "cutoff": "src.cutoff", "final-test": "src.final_test", "claims": "src.claims",
    "validate": "src.validate", "powerbi": "src.powerbi", "export-web": "src.export_web",
    "readme": "src.readme",
}
ALL = ["data-check", "ingest", "clean", "segments", "features", "split", "binning", "model",
       "scorecard", "cutoff", "final-test", "claims", "powerbi", "export-web", "validate",
       "claims", "export-web", "readme"]


def run(cmd: list[str], cwd: Path = ROOT) -> None:
    print("$", " ".join(cmd), flush=True)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    if subprocess.call(cmd, cwd=cwd, env=env) != 0:
        sys.exit(f"failed: {' '.join(cmd)}")


def target(name: str) -> None:
    web = ROOT / "web"
    if name in STAGES:
        run([PY, "-m", STAGES[name]])
    elif name == "all":
        for t in ALL:
            run([PY, "-m", STAGES[t]])
    elif name == "setup":
        if not Path(PY).exists():
            run(["py", "-3.11", "-m", "venv", ".venv"] if os.name == "nt" else ["python3.11", "-m", "venv", ".venv"])
        run([PY, "-m", "pip", "install", "-r", "requirements.txt"])
    elif name == "test":
        run([PY, "-m", "pytest", "-q"])
        for script in ("lint", "typecheck", "test", "check-data"):
            run([NPM, "run", script], cwd=web)
    elif name == "lint":
        run([PY, "-m", "ruff", "check", "src", "tests"])
        run([NPM, "run", "lint"], cwd=web)
    elif name == "web":
        run([NPM, "install"], cwd=web)
        run([NPM, "run", "build"], cwd=web)
    else:
        sys.exit(f"unknown target {name}")


if __name__ == "__main__":
    for t in sys.argv[1:] or ["all"]:
        target(t)
