-- Portfolio baseline: how many applications, how many had payment difficulties,
-- and the baseline payment-difficulty rate every segment is compared against.
SELECT
    COUNT(*)                         AS applications,
    SUM(TARGET)                      AS bads,
    SUM(TARGET) * 1.0 / COUNT(*)     AS baseline_rate
FROM app_clean;
