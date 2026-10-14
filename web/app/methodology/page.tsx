import type { Metadata } from "next";
import CodeBlock from "@/components/CodeBlock";
import { H2, PageHeader, Table } from "@/components/ui";
import { metrics, recommendation,
  ruleText, scorecardSummary, settings } from "@/lib/data";
import { num, pct } from "@/lib/format";

export const metadata: Metadata = { title: "Methodology" };

const PIPELINE = `src/ingest.py       -> data/clean/       raw CSVs loaded as-is (never edited), manifest with sha256
src/clean.py        -> data/clean/       conversions, anomaly flags, ratio features
sql/01-02_*.sql     -> outputs/          portfolio baseline and segment risk (DuckDB)
sql/03-05_*.sql     -> data/clean/       bureau, previous-application and model tables
src/split.py        -> data/clean/       stratified train / validation / test split
src/binning.py      -> outputs/          WoE bins and IV, fit on train only
src/model.py        -> outputs/          logistic regression, coefficient diagnostics
src/scorecard.py    -> outputs/          points scorecard
src/cutoff.py       -> outputs/          cut-off table, sensitivity and recommendation (validation)
src/final_test.py   -> outputs/          test metrics and cut-off check, run once
src/claims.py       -> outputs/          registered claims rendered from metrics
src/validate.py     ->                   checks every stage agrees
src/export_web.py   -> web/public/data   the JSON this website reads`;

export default function Methodology() {
  const sp = settings.split;
  const rules: [string, string][] = [
    ["No invented data.", "Every number on this site is computed by the pipeline and read from an output file. Page copy contains no typed-in figures."],
    [
      "No leakage.",
      `A stratified ${pct(sp.train, 0)} / ${pct(sp.validation, 0)} / ${pct(sp.test, 0)} split with seed ${settings.seed}. Bins, feature selection and the model use train only; validation chooses the cut-off; tests confirm that changing validation or test outcomes changes no bin, coefficient or cut-off.`,
    ],
    [
      "Protected attributes excluded.",
      `${settings.protected_attributes.join(" and ")} are never offered to the model. Fairness testing beyond exclusion — checking proxies such as occupation or income type — was not performed and would be required before any real use.`,
    ],
    ["Every metric is defined.", "Each metric below has a numerator, denominator, filter and source file."],
    [
      "Assumptions are labelled.",
      "Profit inputs live in config/assumptions.yaml, are shown on the Simulator page as assumptions, and are never presented as Home Credit facts.",
    ],
    [
      "Test set used once.",
      "Test metrics and the test check of the cut-off are computed by a separate final step after every modelling and cut-off choice was frozen.",
    ],
    ["Every claim is tested.", "Findings are registered claims rendered from metrics; the test suite re-derives every number."],
  ];

  const defs: string[][] = [
    ["Payment-difficulty rate", "Share of applications with TARGET = 1", "Applications with TARGET = 1", "Applications", "Group or split stated", "baseline.json, segments.csv"],
    ["Lift", "Segment rate ÷ portfolio baseline", "Segment payment-difficulty rate", "Baseline rate", `Segments of ≥ ${settings.min_segment_size} applicants`, "segments.csv"],
    ["Wilson 95% interval", "Confidence interval for a segment rate", "—", "—", "z = 1.96", "segments.csv"],
    ["Weight of evidence (WoE)", "ln(%good in bin ÷ %bad in bin); positive = safer", "Bin share of applicants without difficulties", "Bin share with difficulties", "Train split", "bins.csv, scorecard.csv"],
    ["Information value (IV)", "Σ (%good − %bad) × WoE over bins", "—", "—", "Train split", "iv_summary.csv"],
    ["AUC", "Probability a random applicant with difficulties scores riskier than one without", "—", "—", "Per split", "metrics.json"],
    ["Gini", "2 × AUC − 1", "—", "—", "Per split", "metrics.json"],
    ["KS", "max(TPR − FPR) over all thresholds", "—", "—", "Per split", "metrics.json, ks_curve.csv"],
    ["Approval rate", "Share of applicants scoring at or above the cut-off", "Applicants approved", "Applicants in split", "Validation (test for the check)", "cutoff_table.csv"],
    ["Payment-difficulty rate among approved", "Rate within the approved group", "Approved with TARGET = 1", "Applicants approved", "Validation (test for the check)", "cutoff_table.csv"],
    ["Illustrative profit", "goods approved × loan × margin − difficulties approved × loan × loss", "—", "—", "Validation; assumptions labelled", "cutoff_table.csv"],
  ];

  return (
    <div className="max-w-wide">
      <PageHeader title="How the numbers are produced" subtitle="Pipeline, rules and definitions" />

      <H2 id="pipeline">Pipeline</H2>
      <p className="mb-5 max-w-prose">
        Each stage reads the previous stage’s output and writes its own. Applicant-level tables stay in the local, git-ignored{" "}
        <code>data/</code> folder; only aggregates reach <code>outputs/</code> and this site.
      </p>
      <CodeBlock code={PIPELINE} label="pipeline stages" />

      <H2 id="rules">Rules the study follows</H2>
      <ol className="max-w-prose list-decimal space-y-3 pl-6">
        {rules.map(([lead, body]) => (
          <li key={lead}>
            <strong>{lead}</strong> {body}
          </li>
        ))}
      </ol>

      <H2 id="model">Modelling choices</H2>
      <div className="max-w-prose space-y-4">
        <p>
          <strong>Cleaning.</strong> Day counts were converted to years. The employment placeholder value (mostly pensioners)
          was flagged and set to missing; the dataset’s “XNA” code became a true missing value. Ratios divide safely, returning
          missing rather than infinity.
        </p>
        <p>
          <strong>Binning.</strong> optbinning on the training split, at most {settings.binning.max_n_bins} bins of at least{" "}
          {pct(settings.binning.min_bin_size, 0)} of applicants each, with a monotonic trend for numeric features and missing
          values as their own bin. {settings.woe_convention}. This was verified at run time: the riskiest bin of external score
          3 has a negative WoE. Missing values are scored with their own bin’s WoE, not zero.
        </p>
        <p>
          <strong>Selection.</strong> IV of at least {num(settings.binning.iv_min, 2)}; a leak flag above{" "}
          {num(settings.binning.iv_leak_flag, 1)}; the weaker of any pair with |correlation| above{" "}
          {num(settings.binning.corr_max, 1)}; then the strongest {settings.binning.max_features}. Of{" "}
          {settings.candidates_evaluated} candidates, {settings.selected_by_binning} were selected.
        </p>
        <p>
          <strong>Coefficient signs.</strong> Every coefficient should be negative under this WoE convention.{" "}
          {metrics.removed_for_sign.length > 0
            ? `${metrics.removed_for_sign.join(" and ")} took reversed signs from overlap with other features and were removed under a declared rule, one at a time, with validation Gini recorded before (${num(metrics.validation_gini_before_sign_fix, 4)}) and after (${num(metrics.validation.gini, 4)}).`
            : "All took the expected sign."}{" "}
          {metrics.unexpected_signs_remaining.length === 0
            ? "No unexpected sign remains."
            : `Signs still unexpected: ${metrics.unexpected_signs_remaining.join(", ")}.`}
        </p>
        <p>
          <strong>Scaling.</strong> {scorecardSummary.base_score} points at {scorecardSummary.base_odds}:1 odds,{" "}
          {scorecardSummary.pdo} points to double the odds; points per bin = −(β × WoE + intercept ÷ n) × factor + offset ÷ n.
        </p>
        <p>
          <strong>Cut-off.</strong> Steps of {settings.cutoff.step} points on the validation split. Rule, declared before
          computing: {ruleText()}.
        </p>
      </div>

      <H2 id="definitions">Metric definitions</H2>
      <p className="mb-5 max-w-prose" data-terminology-note>
        Terminology: this site says “payment-difficulty rate” throughout. Credit teams commonly call the same quantity the
        “bad rate”; the internal column name <code>bad_rate</code> holds it.
      </p>
      <Table
        caption="Metric definitions"
        head={["Metric", "Definition", "Numerator", "Denominator", "Filters", "Source file"]}
        rows={defs}
      />
    </div>
  );
}
