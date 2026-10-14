"""Phase 4 — Feature tables.

Runs the bureau, previous-application and model-table SQL and checks that the join did
not duplicate or drop applications.
"""

from __future__ import annotations

from src.common import connect, path, read_sql, write_json


def main() -> dict:
    con = connect()
    for f in ("03_bureau_features.sql", "04_previous_app_features.sql", "05_model_table.sql"):
        con.execute(read_sql(f))
    q = lambda sql: con.execute(sql).fetchone()[0]  # noqa: E731
    summary = {
        "model_table_rows": q("SELECT COUNT(*) FROM model_table"),
        "application_rows": q("SELECT COUNT(*) FROM app_clean"),
        "unique_ids": q("SELECT COUNT(DISTINCT SK_ID_CURR) FROM model_table"),
        "with_bureau_history": q("SELECT SUM(has_bureau_history) FROM model_table"),
        "with_previous_application": q("SELECT SUM(has_previous_application) FROM model_table"),
        "no_history_with_nonnull_amounts": q(
            "SELECT COUNT(*) FROM model_table WHERE has_bureau_history = 0 "
            "AND (bureau_total_overdue IS NOT NULL OR bureau_debt_to_credit IS NOT NULL)"
        ),
        "columns": len(con.execute("DESCRIBE model_table").fetchall()),
    }
    con.close()
    assert summary["model_table_rows"] == summary["application_rows"], "join changed row count"
    assert summary["unique_ids"] == summary["model_table_rows"], "SK_ID_CURR not unique"
    assert summary["no_history_with_nonnull_amounts"] == 0
    write_json(summary, path("outputs") / "features_summary.json")
    print(summary)
    return summary


if __name__ == "__main__":
    main()
