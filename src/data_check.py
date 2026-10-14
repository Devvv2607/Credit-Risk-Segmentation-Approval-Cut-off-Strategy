"""Phase 0 preflight: confirm the three raw CSVs are present before anything runs."""

import sys

from src.common import load_settings, path


def main() -> int:
    s = load_settings()
    raw = path("raw_dir")
    missing = [f for f in s["raw_files"].values() if not (raw / f).exists()]
    if missing:
        print("Missing raw files in", raw, ":", ", ".join(missing))
        print("Accept the competition rules on Kaggle, then run:")
        print("  kaggle competitions download -c home-credit-default-risk")
        print("and unzip into data/raw/.")
        return 1
    for f in s["raw_files"].values():
        print(f"OK  {f}  {(raw / f).stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
