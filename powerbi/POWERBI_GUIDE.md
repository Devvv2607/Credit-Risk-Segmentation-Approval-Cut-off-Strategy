# Power BI build guide

This folder holds the aggregated CSVs the dashboard needs. They are copies of files in
`outputs/`, refreshed by `make all` (step `src/powerbi.py`). **No `.pbix` file exists yet**;
the website lists the dashboard as "not yet available" until you publish one and add its
link to `config/site.yaml` (`powerbi_url`).

Terminology: in every title and label, say **payment-difficulty rate**. The column `bad_rate`
in the CSVs holds that rate; rename it in Power Query (step 0) so it never appears on a visual.

## 0. Load and shape the data

1. **Home → Get data → Text/CSV**, load each file: `segments.csv`, `iv_summary.csv`,
   `scorecard.csv`, `score_distribution.csv`, `cutoff_table.csv`, `sensitivity.csv`.
2. In **Power Query**, for each table:
   - Set percentages/rates (`bad_rate`, `ci_low`, `ci_high`, `lift`, `portfolio_share`,
     `approval_rate`, `share`) to **Decimal number**; counts to **Whole number**.
   - Rename `bad_rate` → `payment_difficulty_rate`.
   - `segments`: filter nothing; `dimension_complete` → True/False.
   - `score_distribution`: keep both `split` values; you will filter on visuals.
3. No relationships are needed: each page reads one or two tables independently.
4. Create a **Measures** table: Home → Enter data → one column, one row, name it `_Measures`.

## Page 1 — Portfolio risk

Measures (on `_Measures`):

```DAX
Applications = SUMX ( FILTER ( segments, segments[dimension] = "Contract type" ), segments[n] )

Applications with difficulties =
    SUMX ( FILTER ( segments, segments[dimension] = "Contract type" ), segments[bads] )

Baseline payment-difficulty rate = DIVIDE ( [Applications with difficulties], [Applications] )

Segment rate = DIVIDE ( SUM ( segments[bads] ), SUM ( segments[n] ) )

Segment lift = DIVIDE ( [Segment rate], [Baseline payment-difficulty rate] )
```

`Contract type` covers every application (it has no missing values or excluded segments), so
summing it gives the portfolio totals. Check that `[Applications]` equals the applications
figure in `outputs/baseline.json`.

Visuals:

1. **KPI cards** (Card visual): `[Applications]`, `[Baseline payment-difficulty rate]` (format as %).
2. **Slicer**: `segments[dimension]`, single select, style *Dropdown*.
3. **Segment lift bar chart** (Clustered bar): Y-axis `segments[segment]` (sort by
   `segments[segment_order]` via *Sort by column*), X-axis `[Segment lift]`. Add a constant
   line at 1.0 (Analytics pane → Constant line) labelled "Portfolio baseline". Conditional
   colour: rust `#B4552D` when lift > 1, green `#2E6B4F` otherwise.
4. **Portfolio share vs rate scatter**: X `segments[portfolio_share]` (Don't summarize),
   Y `segments[payment_difficulty_rate]` (Don't summarize), Legend `segments[dimension]`,
   Details `segments[segment]`, Size `segments[n]`. Add an average line on Y labelled baseline.
5. Tooltip on both charts: `n`, `ci_low`, `ci_high`.

## Page 2 — Scorecard

1. **IV by feature** (Clustered bar): Y `iv_summary[feature]`, X `iv_summary[iv]`. Visual
   filter `iv_summary[decision] = "selected"`, sort descending by IV. Add constant lines at
   0.02 (weak), 0.1 (medium) and 0.3 (strong) — the usual IV strength bands.
2. **Points table** (Matrix): Rows `scorecard[feature]` then `scorecard[bin]` (sort bins by
   `scorecard[bin_index]`), Values `scorecard[woe]`, `scorecard[points]`, `scorecard[count]`.
   Turn off totals for `woe` and `points` (Format → Subtotals off).
3. **Score-band payment-difficulty rate** (Clustered column): X `score_distribution[score_band]`
   (sort by `band_order`), Y `score_distribution[payment_difficulty_rate]` (Average), Legend
   `score_distribution[split]`. Subtitle: "Validation and held-out test".

## Page 3 — Cut-off strategy

1. **What-if parameter** (Modeling → New parameter → Numeric range):
   name `Cutoff`, data type Whole number, minimum = the smallest `cutoff_table[cutoff]`,
   maximum = the largest, increment = 5 (the pipeline's step), default = the recommended
   cut-off from `outputs/recommendation.json`. Tick *Add slicer to this page*. This creates
   the table `Cutoff` with column `Cutoff` and measure `Cutoff Value`.
2. Measures:

```DAX
Approval rate at cut-off =
    LOOKUPVALUE ( cutoff_table[approval_rate], cutoff_table[cutoff], [Cutoff Value] )

Payment-difficulty rate at cut-off =
    LOOKUPVALUE ( cutoff_table[payment_difficulty_rate], cutoff_table[cutoff], [Cutoff Value] )

Applicants approved at cut-off =
    LOOKUPVALUE ( cutoff_table[approved], cutoff_table[cutoff], [Cutoff Value] )

Illustrative profit at cut-off =
    LOOKUPVALUE ( cutoff_table[profit], cutoff_table[cutoff], [Cutoff Value] )

Validation baseline rate =
    LOOKUPVALUE ( cutoff_table[payment_difficulty_rate], cutoff_table[cutoff], MIN ( cutoff_table[cutoff] ) )

Rate change vs baseline (pp) =
    ( [Payment-difficulty rate at cut-off] - [Validation baseline rate] ) * 100

Is selected cut-off = IF ( MAX ( cutoff_table[cutoff] ) = [Cutoff Value], 1, 0 )
```

3. **KPI cards**: approval rate, payment-difficulty rate (with `[Rate change vs baseline (pp)]`
   as a subtitle or second card), applicants approved, illustrative profit. Title the profit
   card "Expected profit — illustrative, assumption-based".
4. **Trade-off line chart**: X `cutoff_table[cutoff]` (continuous), Y `approval_rate` and
   `payment_difficulty_rate` (secondary axis). Add an X-axis constant line bound to
   `[Cutoff Value]` (Analytics → X-axis constant line → fx) labelled "Selected", and a
   second constant line at the recommended cut-off labelled "Recommended".
5. **Profit line chart**: X `cutoff_table[cutoff]`, Y `cutoff_table[profit]`; same two lines.
6. **Sensitivity table**: `sensitivity` columns `avg_loan_level`, `margin_level`,
   `loss_given_bad_level`, `recommended_cutoff`, `shift_vs_base`.
7. **Text box** (amber background `#F5EBD7`, text `#8A5A00`): "Profit uses illustrative
   assumptions (average loan, margin, loss given payment difficulty) from
   `config/assumptions.yaml`. They are not Home Credit figures and exclude funding cost,
   operating cost, fees, recovery timing and loan term. The cut-off table is computed on the
   validation split."

## Theme

Background `#FAF6F0`, panels `#F3EEE7`, text `#0F3B33`, muted `#5E7A72`, series navy
`#1E4E79`, green `#2E6B4F`, rust `#B4552D`. Font: Space Grotesk if installed, else Segoe UI.

## Publishing

Publish to the Power BI service, copy the public link, put it in `config/site.yaml`
(`powerbi_url`) and re-run `make export-web`. Until then the site says the dashboard is not
yet available.
