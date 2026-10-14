import ChartCard from "@/components/ChartCard";
import { ScoreBandChart, SegmentChart, TradeoffChart } from "@/components/charts";
import { C } from "@/lib/colors";
import { ExtLink, MaybeLink, PageHeader, Panel, StatGrid, Warn } from "@/components/ui";
import {
  baseline,
  claim,
  cutoffTable,
  metrics,
  recommendation,
  scoreDistribution,
  segments,
  settings,
  site,
  validation,
} from "@/lib/data";
import { int, num, pct } from "@/lib/format";

export default function Home() {
  const seg = claim("SEG-002");
  const dims = Array.from(new Set(segments.map((s) => s.dimension)));
  return (
    <div>
      <PageHeader title="Credit Risk Scorecard & Cut-off Strategy" subtitle="Who to approve, and where to draw the line" />

      <div className="prose-block max-w-prose text-[19px] leading-[1.8]">
        <p>
          Every lender answers the same question on every application: approve or decline? This study takes the public Home Credit
          Default Risk data — {int(baseline.applications)} past applications, each with a flag for whether the borrower later had
          payment difficulties — and builds the answer step by step. SQL segmentation shows which borrowers are riskier than the
          portfolio as a whole; a points scorecard ranks every applicant; and a cut-off analysis shows what each possible approval
          threshold would mean for approvals, payment difficulty and an illustrative profit.
        </p>
        <p>
          Every figure on this site is produced by a reproducible pipeline and read from its output files. Choices were made on
          training and validation data, and the held-out test split was opened once, at the end. Where a number rests on an
          assumption — loan size, margin, loss — it is labelled as one.
        </p>
      </div>

      <p className="mt-8 flex max-w-prose flex-wrap gap-x-7 gap-y-3 text-[18px]">
        <ExtLink href="/analysis/">Read the analysis</ExtLink>
        <ExtLink href="/simulator/">Try the simulator</ExtLink>
        <ExtLink href="/methodology/">View methodology</ExtLink>
        <MaybeLink href={site.github_url} github>
          Source code
        </MaybeLink>
      </p>

      <Warn className="mt-10 max-w-prose">
        Independent analysis of the public Home Credit Default Risk dataset (Kaggle). Not affiliated with Home Credit or any
        lender. The data is not Indian lending data, and nothing here is a lending decision.
      </Warn>

      <section aria-labelledby="coverage" className="mt-16 max-w-wide">
        <h2 id="coverage" className="eyebrow mb-4">
          Analysis coverage
        </h2>
        <StatGrid
          items={[
            { value: int(baseline.applications), label: "Applications analysed" },
            { value: pct(baseline.baseline_rate, 2), label: "Baseline payment-difficulty rate" },
            { value: int(settings.candidates_evaluated), label: "Features evaluated" },
            { value: int(metrics.features.length), label: "Features in the scorecard" },
            { value: num(metrics.test.gini, 3), label: "Gini on the held-out test split" },
            { value: `${validation.passed}/${validation.total}`, label: "Automated validation checks passing" },
          ]}
          footnote={
            <>
              Counts come from <code>outputs/baseline.json</code>, <code>selected_features.json</code>, <code>metrics.json</code>{" "}
              and <code>validation_report.json</code>, regenerated on every pipeline run. Features evaluated excludes identifiers,
              the target and protected attributes.
            </>
          }
        />
      </section>

      <section aria-labelledby="report" className="mt-16 max-w-wide">
        <Panel className="p-7 sm:p-9">
          <p className="eyebrow">Report · Analysis sections</p>
          <h2 id="report" className="mt-3 text-[28px] font-bold leading-tight text-ink">
            Segment risk, a points scorecard and where to set the approval cut-off
          </h2>
          <p className="mt-2 text-[18px] text-muted">
            From the portfolio baseline to a recommended cut-off of {recommendation.cutoff}, with every claim traced to its source
            file.
          </p>
          <p className="mt-5 text-[18px]">
            <ExtLink href="/analysis/">Read the report</ExtLink>
          </p>
        </Panel>
      </section>

      <section aria-labelledby="featured" className="mt-16 max-w-wide">
        <h2 id="featured" className="eyebrow mb-4">
          Featured visualizations
        </h2>
        <div className="grid gap-6 xl:grid-cols-2">
          <ChartCard
            title="Payment-difficulty rate by segment"
            subtitle="All applications · bars above the dashed baseline are riskier than average"
            legend={[
              { label: "Above baseline", color: C.rust },
              { label: "At or below baseline", color: C.green },
              { label: "Portfolio baseline", color: C.ink, dashed: true },
            ]}
            caption={seg.text}
            source="outputs/segments.csv"
            claims={[seg.id]}
          >
            <SegmentChart
              segments={segments}
              dimensions={dims}
              initial={String(seg.values.dimension.raw)}
              baseline={baseline.baseline_rate}
            />
          </ChartCard>
          <ChartCard
            title="Approval vs payment difficulty"
            subtitle="Every possible cut-off · validation split"
            legend={[
              { label: "Approval rate", color: C.navy },
              { label: "Payment-difficulty rate among approved", color: C.green },
              { label: "Recommended cut-off", color: C.ink, dashed: true },
            ]}
            caption={claim("CUT-001").text}
            source="outputs/cutoff_table.csv"
            claims={["CUT-001"]}
          >
            <TradeoffChart rows={cutoffTable} recommended={recommendation.cutoff} />
          </ChartCard>
          <ChartCard
            title="Payment-difficulty rate by score band"
            subtitle="Validation and held-out test splits"
            legend={[
              { label: "Validation", color: C.navy },
              { label: "Test", color: C.green },
            ]}
            caption={claim("MOD-002").text}
            source="outputs/score_distribution.csv"
            claims={["MOD-002"]}
          >
            <ScoreBandChart bands={scoreDistribution} />
          </ChartCard>
        </div>
      </section>
    </div>
  );
}
