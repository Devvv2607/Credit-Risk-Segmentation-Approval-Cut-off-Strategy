"""Phase 2 — Clean and engineer.

Builds app_clean from raw_application_train:
- DAYS_* are negative day counts before the application; age and employment length are
  converted to positive years so they read naturally on a scorecard.
- DAYS_EMPLOYED = 365243 is a placeholder (mostly pensioners / unemployed), not a real
  tenure of ~1000 years. It is flagged, then set to null so it cannot distort binning.
- 'XNA' is the dataset's "not available" code and becomes a true null.
- Affordability ratios: a borrower's repayment burden matters more than raw amounts.
  Division by zero returns null (NULLIF), never inf.
"""

from __future__ import annotations

from src.common import connect, path, write_json

XNA_COLUMNS = ["CODE_GENDER", "ORGANIZATION_TYPE"]

CLEAN_SQL = f"""
CREATE OR REPLACE TABLE app_clean AS
WITH base AS (
    SELECT
        * REPLACE (
            {", ".join(f"NULLIF({c}, 'XNA') AS {c}" for c in XNA_COLUMNS)},
            CASE WHEN DAYS_EMPLOYED = 365243 THEN NULL ELSE DAYS_EMPLOYED END AS DAYS_EMPLOYED
        ),
        CASE WHEN DAYS_EMPLOYED = 365243 THEN 1 ELSE 0 END AS flag_days_employed_anomaly
    FROM raw_application_train
)
SELECT
    *,
    -DAYS_BIRTH / 365.25                                   AS age_years,
    -DAYS_EMPLOYED / 365.25                                AS years_employed,
    AMT_ANNUITY / NULLIF(AMT_INCOME_TOTAL, 0)              AS annuity_to_income,
    AMT_CREDIT  / NULLIF(AMT_INCOME_TOTAL, 0)              AS credit_to_income,
    AMT_CREDIT  / NULLIF(AMT_GOODS_PRICE, 0)               AS credit_to_goods,
    (-DAYS_EMPLOYED / 365.25) / NULLIF(-DAYS_BIRTH / 365.25, 0) AS employed_to_age
FROM base
"""

RATIOS = ["annuity_to_income", "credit_to_income", "credit_to_goods", "employed_to_age"]


def main() -> dict:
    con = connect()
    con.execute(CLEAN_SQL)
    checks = {}
    checks["rows"] = con.execute("SELECT COUNT(*) FROM app_clean").fetchone()[0]
    checks["anomaly_flag_count"] = con.execute(
        "SELECT SUM(flag_days_employed_anomaly) FROM app_clean"
    ).fetchone()[0]
    checks["infinite_values"] = con.execute(
        "SELECT " + " + ".join(f"COUNT(*) FILTER (WHERE isinf({c}))" for c in RATIOS) + " FROM app_clean"
    ).fetchone()[0]
    checks["negative_ages"] = con.execute(
        "SELECT COUNT(*) FROM app_clean WHERE age_years < 0 OR age_years IS NULL"
    ).fetchone()[0]
    checks["negative_years_employed"] = con.execute(
        "SELECT COUNT(*) FROM app_clean WHERE years_employed < 0"
    ).fetchone()[0]
    checks["target_values"] = sorted(
        r[0] for r in con.execute("SELECT DISTINCT TARGET FROM app_clean").fetchall()
    )
    checks["xna_remaining"] = con.execute(
        "SELECT " + " + ".join(f"COUNT(*) FILTER (WHERE {c} = 'XNA')" for c in XNA_COLUMNS) + " FROM app_clean"
    ).fetchone()[0]
    con.close()

    assert checks["infinite_values"] == 0, "infinite ratio values"
    assert checks["negative_ages"] == 0, "negative or missing ages"
    assert checks["negative_years_employed"] == 0, "negative employment length"
    assert checks["target_values"] == [0, 1], f"unexpected TARGET values {checks['target_values']}"
    assert checks["xna_remaining"] == 0
    write_json(checks, path("outputs") / "clean_summary.json")
    print(checks)
    return checks


if __name__ == "__main__":
    main()
