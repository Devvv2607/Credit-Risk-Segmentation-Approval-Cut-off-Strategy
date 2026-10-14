-- Earlier applications at Home Credit, one row per applicant (SK_ID_CURR).
CREATE OR REPLACE TABLE previous_app_features AS
SELECT
    SK_ID_CURR,
    COUNT(*)                                                     AS prev_app_count,
    COUNT(*) FILTER (WHERE NAME_CONTRACT_STATUS = 'Refused')     AS prev_refused_count,
    COUNT(*) FILTER (WHERE NAME_CONTRACT_STATUS = 'Refused') * 1.0 / COUNT(*) AS prev_refusal_rate
FROM raw_previous_application
GROUP BY SK_ID_CURR;
