import type { Metadata } from "next";
import Simulator from "@/components/Simulator";
import { ClaimBlock, H2, PageHeader, Panel, Table, Warn } from "@/components/ui";
import { assumptions, claim, cutoffTable, recommendation, ruleText, sensitivity } from "@/lib/data";
import { int, money, pct, pp } from "@/lib/format";

export const metadata: Metadata = { title: "Simulator" };

const LEVEL = (l: string) => l.charAt(0).toUpperCase() + l.slice(1);

export default function SimulatorPage() {
  const t = recommendation.test;
  const v = recommendation.validation;
  const oneAtATime = sensitivity.filter((s) => s.n_changed <= 1);
  const a = assumptions;
  return (
    <div className="max-w-wide">
      <PageHeader title="Cut-off simulator" subtitle="Move the line and see who gets approved" />
      <p className="mb-8 max-w-prose text-[18px] text-muted">
        The simulator reads the cut-off table computed on the <strong className="text-ink">validation split</strong>{" "}
        ({int(v.n)} applicants the model never trained on). It starts at the
        recommended cut-off of {recommendation.cutoff}, chosen by a rule declared before any cut-off was computed:{" "}
        <em>{ruleText()}</em>.
      </p>

      <Simulator rows={cutoffTable} recommended={recommendation.cutoff} baselineRate={v.baseline_rate} validationN={v.n} />

      <H2 id="test-check">Held-out test check</H2>
      <Panel>
        <p className="eyebrow">Recommended cut-off {recommendation.cutoff} · applied once to the test split</p>
        <div className="mt-4 grid gap-6 sm:grid-cols-3">
          <div>
            <p className="text-[15px] text-muted">Approval rate</p>
            <p className="num text-[28px] font-bold text-ink">{pct(t.approval_rate)}</p>
            <p className="text-[14px] text-muted">validation {pct(v.approval_rate)} ({pp(t.approval_rate_diff_pp_vs_validation, 2)})</p>
          </div>
          <div>
            <p className="text-[15px] text-muted">Payment-difficulty rate among approved</p>
            <p className="num text-[28px] font-bold text-ink">{pct(t.bad_rate, 2)}</p>
            <p className="text-[14px] text-muted">validation {pct(v.bad_rate, 2)} ({pp(t.bad_rate_diff_pp_vs_validation, 2)})</p>
          </div>
          <div>
            <p className="text-[15px] text-muted">Test baseline (approve everyone)</p>
            <p className="num text-[28px] font-bold text-ink">{pct(t.baseline_rate, 2)}</p>
            <p className="text-[14px] text-muted">{pp(-t.bad_rate_reduction_pp, 2)} at the cut-off</p>
          </div>
        </div>
        <p className="mt-5 text-[16px] text-ink">
          {t.consistent_with_validation
            ? `The test figures agree with validation (${t.consistency_rule}).`
            : `The test figures differ from validation by more than the declared tolerance (${t.consistency_rule}); treat the recommendation with caution.`}
        </p>
        <div className="mt-4">
          <ClaimBlock c={claim("CUT-002")} />
        </div>
      </Panel>

      <H2 id="sensitivity">Sensitivity to the assumptions</H2>
      <p className="mb-5 max-w-prose">
        The recommended cut-off was recomputed under every combination of low, base and high values for the three assumptions.
        The table shows each assumption moved on its own; the full grid is in <code>outputs/sensitivity.csv</code>.
      </p>
      <Table
        caption="Recommended cut-off when one assumption moves"
        head={["Average loan", "Margin", "Loss given difficulty", "Recommended cut-off", "Shift", "Payment-difficulty rate"]}
        align={["l", "l", "l", "r", "r", "r"]}
        rows={oneAtATime.map((s) => [
          `${LEVEL(s.avg_loan_level)} (${money(s.avg_loan)})`,
          `${LEVEL(s.margin_level)} (${pct(s.margin, 0)})`,
          `${LEVEL(s.loss_given_bad_level)} (${pct(s.loss_given_bad, 0)})`,
          s.recommended_cutoff,
          s.shift_vs_base === 0 ? "—" : `${s.shift_vs_base > 0 ? "+" : ""}${s.shift_vs_base}`,
          pct(s.bad_rate, 2),
        ])}
      />
      <div className="mt-5 max-w-prose">
        <ClaimBlock c={claim("CUT-003")} />
      </div>
      <p className="mt-4 max-w-prose text-[17px] text-muted">
        The average loan size scales every profit figure by the same factor, so on its own it never moves the cut-off; margin and
        loss move it because they change the value of an extra approval relative to an extra case of payment difficulty.
      </p>

      <H2 id="assumptions">Assumptions</H2>
      <Warn className="mb-5 max-w-prose">
        These values are illustrative assumptions chosen by the analyst, not Home Credit figures. The profit view ignores{" "}
        {a.excluded.join(", ")}. Read the recommendation as “the result under these assumptions”, not as a lending decision.
      </Warn>
      <Table
        caption="Profit assumptions from config/assumptions.yaml"
        head={["Assumption", "Base", "Low", "High", "Note"]}
        align={["l", "r", "r", "r", "l"]}
        rows={[
          ["Average loan", money(a.avg_loan.value), money(a.avg_loan.low), money(a.avg_loan.high), a.avg_loan.note],
          ["Margin on repaid loans", pct(a.margin.value, 0), pct(a.margin.low, 0), pct(a.margin.high, 0), a.margin.note],
          [
            "Loss given payment difficulty",
            pct(a.loss_given_bad.value, 0),
            pct(a.loss_given_bad.low, 0),
            pct(a.loss_given_bad.high, 0),
            a.loss_given_bad.note,
          ],
        ]}
      />
      <p className="mt-3 text-[14px] text-muted">Units: {a.currency}. Source: config/assumptions.yaml.</p>
    </div>
  );
}
