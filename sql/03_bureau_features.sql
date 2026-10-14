-- Credit history at other institutions, one row per applicant (SK_ID_CURR).
-- Only applicants that appear in bureau get a row; the model table left-joins this.
CREATE OR REPLACE TABLE bureau_features AS
SELECT
    SK_ID_CURR,
    COUNT(*)                                                     AS bureau_credit_count,
    COUNT(*) FILTER (WHERE CREDIT_ACTIVE = 'Active')             AS bureau_active_count,
    SUM(COALESCE(AMT_CREDIT_SUM_OVERDUE, 0))                     AS bureau_total_overdue,
    MAX(COALESCE(AMT_CREDIT_SUM_OVERDUE, 0))                     AS bureau_max_overdue,
    MAX(COALESCE(CREDIT_DAY_OVERDUE, 0))                         AS bureau_max_days_overdue,
    -- outstanding debt as a share of total credit granted; null when no credit amount is known
    SUM(GREATEST(COALESCE(AMT_CREDIT_SUM_DEBT, 0), 0))
        / NULLIF(SUM(COALESCE(AMT_CREDIT_SUM, 0)), 0)            AS bureau_debt_to_credit
FROM raw_bureau
GROUP BY SK_ID_CURR;
