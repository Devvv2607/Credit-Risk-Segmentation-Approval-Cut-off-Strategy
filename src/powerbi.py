"""Phase 12 — Power BI handoff: copy the aggregated outputs the dashboard needs."""

import shutil

from src.common import path

FILES = [
    "segments.csv",
    "iv_summary.csv",
    "scorecard.csv",
    "score_distribution.csv",
    "cutoff_table.csv",
    "sensitivity.csv",
    "coefficients.csv",
]


def main() -> None:
    dest = path("powerbi")
    for f in FILES:
        shutil.copyfile(path("outputs") / f, dest / f)
        print(f"copied {f}")


if __name__ == "__main__":
    main()
