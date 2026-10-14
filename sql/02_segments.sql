-- Segment risk: payment-difficulty rate by borrower segment vs the portfolio baseline.
-- Expects the variable min_segment_size (SET VARIABLE) to be set by src/segments.py.
-- Nulls are kept as a 'Missing' segment so each dimension covers the full population.
WITH labelled AS (
    SELECT 'Age band' AS dimension,
        CASE WHEN age_years < 25 THEN '20-24' WHEN age_years < 35 THEN '25-34'
             WHEN age_years < 45 THEN '35-44' WHEN age_years < 55 THEN '45-54'
             WHEN age_years < 65 THEN '55-64' ELSE '65+' END AS segment,
        CASE WHEN age_years < 25 THEN 1 WHEN age_years < 35 THEN 2
             WHEN age_years < 45 THEN 3 WHEN age_years < 55 THEN 4
             WHEN age_years < 65 THEN 5 ELSE 6 END AS segment_order,
        TARGET
    FROM app_clean
    UNION ALL
    SELECT 'Income type', COALESCE(NAME_INCOME_TYPE, 'Missing'), 0, TARGET FROM app_clean
    UNION ALL
    SELECT 'Education', COALESCE(NAME_EDUCATION_TYPE, 'Missing'), 0, TARGET FROM app_clean
    UNION ALL
    SELECT 'Contract type', COALESCE(NAME_CONTRACT_TYPE, 'Missing'), 0, TARGET FROM app_clean
    UNION ALL
    SELECT 'Annuity-to-income band',
        CASE WHEN annuity_to_income IS NULL THEN 'Missing'
             WHEN annuity_to_income < 0.10 THEN '<10%'
             WHEN annuity_to_income < 0.20 THEN '10-20%'
             WHEN annuity_to_income < 0.30 THEN '20-30%'
             WHEN annuity_to_income < 0.40 THEN '30-40%'
             ELSE '40%+' END,
        CASE WHEN annuity_to_income IS NULL THEN 9
             WHEN annuity_to_income < 0.10 THEN 1
             WHEN annuity_to_income < 0.20 THEN 2
             WHEN annuity_to_income < 0.30 THEN 3
             WHEN annuity_to_income < 0.40 THEN 4
             ELSE 5 END,
        TARGET
    FROM app_clean
    UNION ALL
    SELECT 'Region rating', COALESCE('Rating ' || CAST(REGION_RATING_CLIENT AS VARCHAR), 'Missing'),
        COALESCE(REGION_RATING_CLIENT, 9), TARGET FROM app_clean
    UNION ALL
    SELECT ext.dimension,
        CASE WHEN ext.v IS NULL THEN 'Missing'
             WHEN ext.v < 0.2 THEN '0.0-0.2' WHEN ext.v < 0.4 THEN '0.2-0.4'
             WHEN ext.v < 0.6 THEN '0.4-0.6' WHEN ext.v < 0.8 THEN '0.6-0.8'
             ELSE '0.8-1.0' END,
        CASE WHEN ext.v IS NULL THEN 9 ELSE LEAST(FLOOR(ext.v * 5), 4) + 1 END,
        ext.TARGET
    FROM (
        SELECT 'EXT_SOURCE_1 band' AS dimension, EXT_SOURCE_1 AS v, TARGET FROM app_clean
        UNION ALL SELECT 'EXT_SOURCE_2 band', EXT_SOURCE_2, TARGET FROM app_clean
        UNION ALL SELECT 'EXT_SOURCE_3 band', EXT_SOURCE_3, TARGET FROM app_clean
    ) AS ext
),
baseline AS (
    SELECT SUM(TARGET) * 1.0 / COUNT(*) AS baseline_rate FROM app_clean
),
segment_stats AS (
    SELECT
        dimension,
        segment,
        MIN(segment_order)              AS segment_order,
        COUNT(*)                        AS n,
        SUM(TARGET)                     AS bads,
        SUM(TARGET) * 1.0 / COUNT(*)    AS bad_rate,
        -- dimension population before the size filter, so shares stay honest
        SUM(COUNT(*)) OVER (PARTITION BY dimension) AS dimension_population
    FROM labelled
    GROUP BY dimension, segment
),
filtered AS (
    SELECT * FROM segment_stats WHERE n >= getvariable('min_segment_size')
),
wilson AS (
    -- Wilson score interval, z = 1.96 (95%)
    SELECT
        *,
        (bad_rate + 1.96 * 1.96 / (2 * n)
            - 1.96 * SQRT(bad_rate * (1 - bad_rate) / n + 1.96 * 1.96 / (4 * n * n)))
            / (1 + 1.96 * 1.96 / n) AS ci_low,
        (bad_rate + 1.96 * 1.96 / (2 * n)
            + 1.96 * SQRT(bad_rate * (1 - bad_rate) / n + 1.96 * 1.96 / (4 * n * n)))
            / (1 + 1.96 * 1.96 / n) AS ci_high
    FROM filtered
)
SELECT
    w.dimension,
    w.segment,
    w.n,
    w.bads,
    w.bad_rate,
    w.ci_low,
    w.ci_high,
    w.bad_rate / b.baseline_rate                                   AS lift,
    w.n * 1.0 / w.dimension_population                              AS portfolio_share,
    RANK() OVER (PARTITION BY w.dimension ORDER BY w.bad_rate DESC) AS risk_rank,
    w.segment_order
FROM wilson AS w
CROSS JOIN baseline AS b
ORDER BY w.dimension, w.segment_order, w.bad_rate DESC;
