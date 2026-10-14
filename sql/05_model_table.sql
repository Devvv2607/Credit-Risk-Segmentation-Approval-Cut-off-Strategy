-- Model table: one row per application. Applicants with no bureau / previous-application
-- record get a count of 0 (a true statement: no credits on file) but NULL for amounts and
-- ratios, where 0 would wrongly suggest a clean, observed history. Flags make the
-- "no history" state explicit for binning.
CREATE OR REPLACE TABLE model_table AS
SELECT
    a.*,
    CASE WHEN b.SK_ID_CURR IS NULL THEN 0 ELSE 1 END             AS has_bureau_history,
    COALESCE(b.bureau_credit_count, 0)                           AS bureau_credit_count,
    COALESCE(b.bureau_active_count, 0)                           AS bureau_active_count,
    b.bureau_total_overdue,
    b.bureau_max_overdue,
    b.bureau_max_days_overdue,
    b.bureau_debt_to_credit,
    CASE WHEN p.SK_ID_CURR IS NULL THEN 0 ELSE 1 END             AS has_previous_application,
    COALESCE(p.prev_app_count, 0)                                AS prev_app_count,
    COALESCE(p.prev_refused_count, 0)                            AS prev_refused_count,
    p.prev_refusal_rate
FROM app_clean AS a
LEFT JOIN bureau_features AS b USING (SK_ID_CURR)
LEFT JOIN previous_app_features AS p USING (SK_ID_CURR);
