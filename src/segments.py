"""Phase 3 — SQL segmentation.

Runs sql/01_baseline.sql and sql/02_segments.sql against app_clean and writes
outputs/baseline.json and outputs/segments.csv. Segments smaller than
min_segment_size are dropped (their rates are too noisy to act on); the dimensions
affected are recorded so the weighted-average check is only applied to complete ones.
"""

from __future__ import annotations

from src.common import connect, load_settings, path, read_sql, write_csv, write_json


def main():
    s = load_settings()
    con = connect()
    applications, bads, baseline = con.execute(read_sql("01_baseline.sql")).fetchone()
    con.execute(f"SET VARIABLE min_segment_size = {int(s['segments']['min_segment_size'])}")
    seg = con.execute(read_sql("02_segments.sql")).df()
    con.close()

    complete = seg.groupby("dimension")["n"].sum().eq(applications)
    seg_out = seg.copy()
    seg_out["dimension_complete"] = seg_out["dimension"].map(complete)
    write_csv(seg_out, path("outputs") / "segments.csv")
    write_json(
        {
            "applications": int(applications),
            "bads": int(bads),
            "baseline_rate": float(baseline),
            "min_segment_size": s["segments"]["min_segment_size"],
            "dimensions": sorted(seg["dimension"].unique().tolist()),
            "dimensions_with_excluded_segments": sorted(complete[~complete].index.tolist()),
        },
        path("outputs") / "baseline.json",
    )
    print(f"baseline: {applications:,} applications, {bads:,} with difficulties, rate {baseline:.4%}")
    top = seg.sort_values("lift", ascending=False).head(8)
    print(top[["dimension", "segment", "n", "bad_rate", "lift"]].to_string(index=False))
    return seg


if __name__ == "__main__":
    main()
