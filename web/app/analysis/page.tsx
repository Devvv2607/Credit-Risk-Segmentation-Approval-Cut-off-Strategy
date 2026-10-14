import type { Metadata } from "next";
import ChartCard from "@/components/ChartCard";
import { IvChart, ProfitChart, RocChart, ScoreBandChart, SegmentChart, TradeoffChart } from "@/components/charts";
import { C } from "@/lib/colors";
import Toc from "@/components/Toc";
import { ClaimBlock, ExtLink, H2, PageHeader, Table, Warn } from "@/components/ui";
import {
  baseline,
  claim,
  claims,
  cutoffTable,
  featureLabel,
  ivSummary,
  metrics,
  recommendation,
  ruleText,
  rocPoints,
  scoreDistribution,
  scorecardSummary,
  segments,
  settings,
  splitSummary,
} from "@/lib/data";
import { int, num, pct, pp } from "@/lib/format";

export const metadata: Metadata = { title: "Analysis" };

const TOC = [
  { id: "abstract", label: "Abstract" },
  { id: "summary", label: "Executive summary" },
  { id: "scope", label: "Question and scope" },
  { id: "data", label: "Data and definitions" },
  { id: "baseline", label: "1. Portfolio baseline" },
  { id: "segments", label: "2. Segment risk" },
  { id: "iv", label: "3. Feature strength (IV)" },
  { id: "performance", label: "4. Scorecard performance" },
  { id: "cutoff", label: "5. Cut-off strategy" },
  { id: "interpretation", label: "Interpretation" },
  { id: "limitations", label: "Limitations" },
  { id: "conclusion", label: "Conclusion" },
  { id: "references", label: "References" },
];

export default function Analysis() {
  const dims = Array.from(new Set(segments.map((s) => s.dimension)));
  const seg2 = claim("SEG-002");
  const v = recommendation.validation;
  const t = recommendation.test;
  const top = ivSummary.filter((r) => r.decision === "selected").sort((a, b) => b.iv - a.iv);
  const sp = splitSummary.splits;
  const nonMono = [...scorecardSummary.non_monotonic_bands_validation, ...scorecardSummary.non_monotonic_bands_test];
  const um = recommendation.unconstrained_max_profit;

  return (
    <div className="grid max-w-wide gap-12 xl:grid-cols-[minmax(0,1100px)_220px]">
      <article className="min-w-0">
        <PageHeader title="Who to approve, and where to draw the line" subtitle="Segment risk, a points scorecard and an approval cut-off" />

        <section aria-labelledby="abstract">
          <H2 id="abstract">Abstract</H2>
          <p className="max-w-prose">
            Using {int(baseline.applications)} applications from the public Home Credit Default Risk dataset, this study measures
            how payment difficulty varies across borrower segments, builds a {metrics.features.length}-feature points scorecard
            from weight-of-evidence bins, and evaluates every possible approval cut-off. On held-out data the scorecard reaches a
            Gini of {num(metrics.test.gini)}. Under illustrative profit assumptions the recommended cut-off is{" "}
            {recommendation.cutoff}, approving {pct(t.approval_rate)} of test applicants with a payment-difficulty rate of{" "}
            {pct(t.bad_rate, 2)} against {pct(t.baseline_rate, 2)} if everyone were approved.
          </p>
        </section>

        <section aria-labelledby="summary">
          <H2 id="summary">Executive summary</H2>
          <p className="mb-6 max-w-prose text-muted">
            Each finding is a registered claim: its sentence is rendered from the pipeline outputs, and the test suite checks
            every number against its source file.
          </p>
          <div className="max-w-prose space-y-6">
            {claims.map((c) => (
              <ClaimBlock key={c.id} c={c} />
            ))}
          </div>
        </section>

        <section aria-labelledby="scope" className="max-w-prose">
          <H2 id="scope">Question and scope</H2>
          <p>
            The business question is the one a lender faces on every application: <strong>whom should we approve, and where
            should the approval cut-off sit?</strong> The study answers it in three parts — which segments carry elevated payment
            difficulty, how well an explainable scorecard ranks applicants, and what each cut-off would mean for approvals,
            payment difficulty and an illustrative profit.
          </p>
          <p className="mt-4">
            Out of scope: pricing, credit limits, collections, and the installment, POS and credit-card tables in the dataset.
            Protected attributes ({settings.protected_attributes.join(", ")}) are excluded from the model.
          </p>
        </section>

        <section aria-labelledby="data" className="max-w-prose">
          <H2 id="data">Data and definitions</H2>
          <p>
            Three tables are used: the main application table, applicants’ credits at other institutions (bureau) and their
            earlier Home Credit applications. The outcome, TARGET, flags a client with payment difficulties — a late payment
            beyond a threshold on at least one of the first instalments. The share of applications with TARGET = 1 is the{" "}
            <strong>payment-difficulty rate</strong>.
          </p>
          <p className="mt-4">
            Applications were split once, stratified on TARGET, into train ({int(sp.train.n)}), validation ({int(sp.validation.n)}
            ) and test ({int(sp.test.n)}). Binning, feature selection and model fitting used train only; validation chose the
            cut-off; test was used once at the end. Full definitions are on the <ExtLink href="/methodology/">Methodology</ExtLink>{" "}
            page.
          </p>
        </section>

        <section aria-labelledby="baseline" className="max-w-prose">
          <H2 id="baseline">1. Portfolio baseline</H2>
          <ClaimBlock c={claim("SEG-001")} />
          <p className="mt-5">
            Each split reproduces this rate closely: train {pct(sp.train.rate, 2)}, validation {pct(sp.validation.rate, 2)}, test{" "}
            {pct(sp.test.rate, 2)}. Every segment lift and cut-off figure below is measured against it.
          </p>
        </section>

        <section aria-labelledby="segments">
          <H2 id="segments">2. Segment risk</H2>
          <p className="mb-6 max-w-prose">
            Segments come from SQL over the full application table, with a 95% Wilson interval for each rate. Segments with
            fewer than {int(baseline.min_segment_size)} applicants are left out because their rates are too noisy to act on.
          </p>
          <ChartCard
            title="Payment-difficulty rate by segment"
            subtitle="All applications · choose a dimension · hover for the confidence interval"
            legend={[
              { label: "Above baseline", color: C.rust },
              { label: "At or below baseline", color: C.green },
              { label: "Portfolio baseline", color: C.ink, dashed: true },
            ]}
            caption={seg2.text}
            source="outputs/segments.csv"
            claims={["SEG-002", "SEG-003", "SEG-004", "SEG-005"]}
          >
            <SegmentChart segments={segments} dimensions={dims} initial={dims[0]} baseline={baseline.baseline_rate} />
          </ChartCard>
          <div className="mt-6 max-w-prose space-y-5">
            <ClaimBlock c={claim("SEG-003")} />
            <ClaimBlock c={claim("SEG-004")} />
            <ClaimBlock c={claim("SEG-005")} />
          </div>
        </section>

        <section aria-labelledby="iv">
          <H2 id="iv">3. Feature strength (IV)</H2>
          <p className="mb-6 max-w-prose">
            Each candidate feature was split into weight-of-evidence bins on the training data, with missing values as their own
            bin. Features with an information value below {num(settings.binning.iv_min, 2)} were dropped, and of any pair
            correlated above {num(settings.binning.corr_max, 1)} the weaker was dropped. No feature exceeded the leak flag of{" "}
            {num(settings.binning.iv_leak_flag, 1)}
            {settings.leak_flags.length ? ` except ${settings.leak_flags.join(", ")}` : ""}. The strongest is{" "}
            {featureLabel(top[0].feature)} (IV {num(top[0].iv)}).
          </p>
          <ChartCard
            title="Information value of the selected features"
            subtitle="Training split · grey bars were removed at the coefficient-sign review"
            legend={[
              { label: "In the scorecard", color: C.navy },
              { label: "Removed at sign review", color: C.muted },
            ]}
            caption={claim("MOD-001").text}
            source="outputs/iv_summary.csv"
            claims={["MOD-001"]}
          >
            <IvChart rows={ivSummary} modelFeatures={metrics.features} />
          </ChartCard>
          <p className="mt-6 max-w-prose">
            {metrics.removed_for_sign.length > 0 ? (
              <>
                {metrics.removed_for_sign.map(featureLabel).join(" and ")} ranked risk correctly on their own but took a reversed
                sign in the joint model because their information overlaps with other features. They were removed under a
                declared rule; validation Gini moved from {num(metrics.validation_gini_before_sign_fix, 4)} to{" "}
                {num(metrics.validation.gini, 4)}. The investigation is in <code>outputs/coefficient_diagnostics.md</code>.
              </>
            ) : (
              <>Every coefficient took the expected sign.</>
            )}
          </p>
        </section>

        <section aria-labelledby="performance">
          <H2 id="performance">4. Scorecard performance</H2>
          <div className="max-w-prose">
            <Table
              caption="Model performance by split"
              head={["Split", "Applicants", "AUC", "Gini", "KS"]}
              align={["l", "r", "r", "r", "r"]}
              rows={(["train", "validation", "test"] as const).map((k) => [
                k === "test" ? "Test (final)" : k.charAt(0).toUpperCase() + k.slice(1),
                int(metrics[k].n),
                num(metrics[k].auc),
                num(metrics[k].gini),
                num(metrics[k].ks),
              ])}
            />
            <div className="mt-6 space-y-5">
              <ClaimBlock c={claim("MOD-002")} />
              <ClaimBlock c={claim("MOD-003")} />
            </div>
          </div>
          <div className="mt-8 grid gap-6 lg:grid-cols-2">
            <ChartCard
              title="ROC curve"
              subtitle="Held-out test split"
              legend={[
                { label: "Scorecard", color: C.navy },
                { label: "Random ranking", color: C.muted, dashed: true },
              ]}
              caption={`Gini ${num(metrics.test.gini)} · AUC ${num(metrics.test.auc)}.`}
              source="outputs/roc_points.csv"
              claims={["MOD-002"]}
            >
              <RocChart points={rocPoints} />
            </ChartCard>
            <ChartCard
              title="Payment-difficulty rate by score band"
              subtitle="Validation and held-out test"
              legend={[
                { label: "Validation", color: C.navy },
                { label: "Test", color: C.green },
              ]}
              caption={
                nonMono.length === 0
                  ? "The rate falls in every successive score band on both splits."
                  : `The rate does not fall monotonically in: ${nonMono.join(", ")}.`
              }
              source="outputs/score_distribution.csv"
            >
              <ScoreBandChart bands={scoreDistribution} />
            </ChartCard>
          </div>
        </section>

        <section aria-labelledby="cutoff">
          <H2 id="cutoff">5. Cut-off strategy</H2>
          <p className="mb-6 max-w-prose">
            For every cut-off in steps of {settings.cutoff.step} points, the validation split gives the approval rate, the
            payment-difficulty rate among approved applicants and an illustrative profit. The recommendation rule was declared
            in configuration before anything was computed: <em>{ruleText()}</em>.
          </p>
          <div className="grid gap-6 lg:grid-cols-2">
            <ChartCard
              title="Approval vs payment difficulty"
              subtitle="Validation split"
              legend={[
                { label: "Approval rate", color: C.navy },
                { label: "Payment-difficulty rate", color: C.green },
                { label: "Recommended", color: C.ink, dashed: true },
              ]}
              caption={claim("CUT-001").text}
              source="outputs/cutoff_table.csv"
              claims={["CUT-001"]}
            >
              <TradeoffChart rows={cutoffTable} recommended={recommendation.cutoff} />
            </ChartCard>
            <ChartCard
              title="Illustrative profit"
              subtitle="Validation split · assumption-based"
              legend={[
                { label: "Illustrative profit", color: C.rust },
                { label: "Recommended", color: C.ink, dashed: true },
              ]}
              caption={`Without the payment-difficulty ceiling, profit would peak at a cut-off of ${um.cutoff}, where the rate among approved is ${pct(um.bad_rate, 2)} — above the ceiling, so the rule picks ${recommendation.cutoff}.`}
              source="outputs/cutoff_table.csv"
            >
              <ProfitChart rows={cutoffTable} recommended={recommendation.cutoff} />
            </ChartCard>
          </div>
          <div className="mt-6 max-w-prose space-y-5">
            <ClaimBlock c={claim("CUT-004")} />
            <ClaimBlock c={claim("CUT-002")} />
            <ClaimBlock c={claim("CUT-003")} />
          </div>
          <p className="mt-6 max-w-prose">
            <ExtLink href="/simulator/">Try other cut-offs in the simulator</ExtLink>
          </p>
        </section>

        <section aria-labelledby="interpretation" className="max-w-prose">
          <H2 id="interpretation">Interpretation</H2>
          <p>
            The external credit scores dominate: they carry the highest information value and the steepest segment gradients.
            Affordability and history add separation — the credit-to-goods ratio, outstanding bureau debt and earlier refusals
            all enter the scorecard — while age and income type, strongly predictive on their own, add little once employment
            length and employer type are known.
          </p>
          <p className="mt-4">
            The cut-off result is a trade-off, not a free gain. At {recommendation.cutoff} the payment-difficulty rate among
            approved applicants falls by {pp(-v.bad_rate_reduction_pp, 2)} relative to approving everyone, but{" "}
            {int(v.goods_rejected)} validation applicants who would have repaid are declined alongside the {int(v.bads_avoided)}{" "}
            with difficulties.{" "}
            {t.consistent_with_validation
              ? "The held-out test split confirms the validation figures"
              : "The held-out test figures differ from validation by more than the declared tolerance"}
            , and the recommended cut-off moves only
            between {recommendation.sensitivity.min_cutoff} and {recommendation.sensitivity.max_cutoff} across the assumption
            grid.
          </p>
          <p className="mt-4">
            {claim("MOD-004").text} For a decision that must be explained to applicants and regulators, that gap is the cost of
            transparency.
          </p>
        </section>

        <section aria-labelledby="limitations" className="max-w-prose">
          <H2 id="limitations">Limitations</H2>
          <ul className="list-disc space-y-3 pl-6 text-warn-ink marker:text-warn-ink">
            <li>
              <strong>Reject inference.</strong> Only loans that were granted have outcomes. Applicants Home Credit declined are
              absent, so the model has never seen the riskiest part of the through-the-door population, and approval rates here
              are rates among previously approved applicants.
            </li>
            <li>
              <strong>No application dates.</strong> The data has no timestamps, so there is no out-of-time validation; the test
              split is random, not later in time, and population drift is untested.
            </li>
            <li>
              <strong>Not Indian lending data.</strong> The country is not disclosed. The scorecard would need recalibration — and
              likely rebuilding — before use on any other market.
            </li>
            <li>
              <strong>Illustrative profit.</strong> The profit view rests on labelled assumptions and excludes funding cost,
              operating cost, fees, recovery timing and loan term. It shows the shape of the trade-off, not a P&amp;L.
            </li>
            <li>
              <strong>Payment difficulty is not default.</strong> TARGET flags late payment on early instalments; it is not a
              full default or loss definition.
            </li>
          </ul>
          <Warn className="mt-6">The recommended cut-off is the result under these assumptions, not a lending decision.</Warn>
        </section>

        <section aria-labelledby="conclusion" className="max-w-prose">
          <H2 id="conclusion">Conclusion</H2>
          <p>
            A transparent {metrics.features.length}-feature scorecard separates applicants well enough to support a cut-off
            strategy: at {recommendation.cutoff}, it approves {pct(t.approval_rate)} of held-out applicants with a
            payment-difficulty rate of {pct(t.bad_rate, 2)}, against {pct(t.baseline_rate, 2)} for the whole portfolio. The
            recommendation is stable across the assumption grid and confirmed on data used only once. Before any real use, it
            would need reject inference, out-of-time validation and a full cost model.
          </p>
        </section>

        <section aria-labelledby="references" className="max-w-prose">
          <H2 id="references">References</H2>
          <ul className="space-y-3 text-[17px]">
            <li>
              Home Credit Group. Home Credit Default Risk (Kaggle competition data).{" "}
              <ExtLink href="https://www.kaggle.com/competitions/home-credit-default-risk/data">kaggle.com</ExtLink>
            </li>
            <li>Siddiqi, N. Credit Risk Scorecards: Developing and Implementing Intelligent Credit Scoring. Wiley.</li>
            <li>Thomas, L., Crook, J., Edelman, D. Credit Scoring and Its Applications. SIAM.</li>
            <li>
              Navas-Palencia, G. OptBinning: optimal binning in Python.{" "}
              <ExtLink href="https://gnpalencia.org/optbinning/">gnpalencia.org/optbinning</ExtLink>
            </li>
            <li>Wilson, E. B. Probable inference, the law of succession, and statistical inference. JASA.</li>
          </ul>
        </section>
      </article>
      <aside>
        <Toc items={TOC} />
      </aside>
    </div>
  );
}
