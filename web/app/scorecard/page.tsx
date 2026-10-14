import type { Metadata } from "next";
import ChartCard from "@/components/ChartCard";
import { IvChart, KsChart, RocChart, ScoreBandChart } from "@/components/charts";
import { C } from "@/lib/colors";
import { ClaimBlock, H2, PageHeader, Panel, Table } from "@/components/ui";
import {
  claim,
  featureLabel,
  ivSummary,
  ksCurve,
  metrics,
  rocPoints,
  scoreDistribution,
  scorecard,
  scorecardSummary,
  settings,
} from "@/lib/data";
import { int, num, pct } from "@/lib/format";

export const metadata: Metadata = { title: "Scorecard" };

export default function ScorecardPage() {
  const s = scorecardSummary;
  const iv = Object.fromEntries(ivSummary.map((r) => [r.feature, r.iv]));
  const features = [...metrics.features].sort((a, b) => (iv[b] ?? 0) - (iv[a] ?? 0));
  const nonMono = [...s.non_monotonic_bands_validation, ...s.non_monotonic_bands_test];
  return (
    <div className="max-w-wide">
      <PageHeader title="The points scorecard" subtitle="Every bin, its weight of evidence and its points" />

      <div className="max-w-prose">
        <p>
          A score of {s.base_score} corresponds to good-to-difficulty odds of {s.base_odds}:1, and every {s.pdo} points doubles
          those odds. An applicant’s score is the sum of the points for the bin they fall into on each of the{" "}
          {metrics.features.length} features. Higher scores mean lower risk. Points are shown rounded; scores are computed from
          the unrounded values.
        </p>
      </div>

      <H2 id="iv">Feature strength</H2>
      <ChartCard
        title="Information value by feature"
        subtitle="Training split · shaded bands mark weak, medium and strong predictive strength"
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

      <H2 id="points">Points table</H2>
      <p className="mb-5 max-w-prose">
        Open a feature to see its bins. WoE is ln(%good / %bad): positive bins are safer than average and earn more points.
        “Missing” is its own bin; a bin with no training applicants carries a WoE of zero.
      </p>
      <div className="space-y-3">
        {features.map((f) => {
          const rows = scorecard.filter((r) => r.feature === f).sort((a, b) => a.bin_index - b.bin_index);
          const pts = rows.filter((r) => r.count > 0).map((r) => r.points);
          return (
            <details key={f} className="group rounded-xl border border-border bg-panel">
              <summary className="flex cursor-pointer flex-wrap items-baseline justify-between gap-2 px-5 py-4 text-[18px] font-semibold text-ink">
                <span>{featureLabel(f)}</span>
                <span className="num text-[15px] font-normal text-muted">
                  IV {num(iv[f] ?? 0)} · points {Math.min(...pts)} to {Math.max(...pts)}
                </span>
              </summary>
              <div className="px-5 pb-5">
                <Table
                  caption={`Scorecard bins for ${featureLabel(f)}`}
                  head={["Bin", "Applicants (train)", "Payment-difficulty rate", "WoE", "Points"]}
                  align={["l", "r", "r", "r", "r"]}
                  rows={rows.map((r) => [
                    <span key="b" className="break-all">
                      {r.bin}
                    </span>,
                    int(r.count),
                    r.count > 0 ? pct(r.bad_rate, 1) : "—",
                    num(r.woe),
                    <strong key="p">{r.points}</strong>,
                  ])}
                />
                <p className="mt-2 text-[13px] text-muted">
                  Source: outputs/scorecard.csv · internal name <code>{f}</code>
                </p>
              </div>
            </details>
          );
        })}
      </div>

      <H2 id="bands">Score bands</H2>
      <ChartCard
        title="Payment-difficulty rate by score band"
        subtitle="Validation and held-out test"
        legend={[
          { label: "Validation", color: C.navy },
          { label: "Test", color: C.green },
        ]}
        caption={
          nonMono.length === 0
            ? "The payment-difficulty rate falls in every successive score band, on both splits."
            : `Bands where the rate does not fall: ${nonMono.join(", ")}.`
        }
        source="outputs/score_distribution.csv"
      >
        <ScoreBandChart bands={scoreDistribution} />
      </ChartCard>

      <H2 id="performance">Discrimination</H2>
      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard
          title="ROC curve"
          subtitle="Held-out test split"
          legend={[
            { label: "Scorecard", color: C.navy },
            { label: "Random ranking", color: C.muted, dashed: true },
          ]}
          caption={`Test Gini ${num(metrics.test.gini)} (AUC ${num(metrics.test.auc)}).`}
          source="outputs/roc_points.csv"
          claims={["MOD-002"]}
        >
          <RocChart points={rocPoints} />
        </ChartCard>
        <ChartCard
          title="KS curve"
          subtitle="Held-out test split · cumulative share below each score"
          legend={[
            { label: "With payment difficulties", color: C.rust },
            { label: "Without", color: C.navy },
          ]}
          caption={`Test KS ${num(metrics.test.ks)}: the largest gap between the two cumulative distributions.`}
          source="outputs/ks_curve.csv"
          claims={["MOD-002"]}
        >
          <KsChart rows={ksCurve} />
        </ChartCard>
      </div>
      <div className="mt-6 max-w-prose">
        <Table
          caption="Train, validation and test metrics"
          head={["Metric", "Train", "Validation", "Test (final)"]}
          align={["l", "r", "r", "r"]}
          rows={[
            ["Applicants", int(metrics.train.n), int(metrics.validation.n), int(metrics.test.n)],
            ["AUC", num(metrics.train.auc), num(metrics.validation.auc), num(metrics.test.auc)],
            ["Gini", num(metrics.train.gini), num(metrics.validation.gini), num(metrics.test.gini)],
            ["KS", num(metrics.train.ks), num(metrics.validation.ks), num(metrics.test.ks)],
          ]}
        />
        <p className="mt-3 text-[15px] text-muted">
          Train–validation Gini gap {num(metrics.train_validation_gini_gap)}. Source: outputs/metrics.json.
        </p>
      </div>

      <H2 id="why-lr">Why logistic regression, not gradient boosting</H2>
      <Panel className="max-w-prose">
        <ClaimBlock c={claim("MOD-004")} />
        <p className="mt-5">
          A points scorecard lets a credit officer see exactly why an applicant scored as they did, check that every safer bin
          earns more points, and explain a decline. The benchmark ({metrics.benchmark.model.toLowerCase()}) used{" "}
          {metrics.benchmark.n_features} features against the scorecard’s {metrics.features.length} and reached a test Gini of{" "}
          {num(metrics.benchmark.test.gini)} against {num(metrics.test.gini)}. It is reported only to size the trade-off; it is not
          used for any decision here.
        </p>
      </Panel>

      <H2 id="checks">Scorecard checks</H2>
      <ul className="max-w-prose list-disc space-y-2 pl-6">
        <li>
          Summing bin points reproduces every applicant’s score to within{" "}
          {s.max_abs_score_vs_points_difference.toExponential(1)} points.
        </li>
        <li>Score is a strictly decreasing function of predicted probability on validation and test (Spearman = −1).</li>
        {s.optbinning_crosscheck.ran && s.optbinning_crosscheck.comparable && (
          <li>
            Cross-check against optbinning’s Scorecard over {s.optbinning_crosscheck.rows_compared} bins: largest difference{" "}
            {(s.optbinning_crosscheck.max_abs_point_difference ?? 0).toExponential(1)} points.
          </li>
        )}
        <li>
          Scaling: factor {num(s.factor, 4)}, offset {num(s.offset, 4)} ({settings.scorecard.pdo} points to double the odds).
        </li>
      </ul>
    </div>
  );
}
