"use client";

import { useMemo, useState } from "react";
import ChartCard from "./ChartCard";
import { ProfitChart, TradeoffChart } from "./charts";
import { C } from "@/lib/colors";
import type { CutoffRow } from "@/lib/data";
import { cutoffStep, lookupCutoff } from "@/lib/simulator";
import { int, money, pct, pp } from "@/lib/format";

function Kpi({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "warn" }) {
  return (
    <div className="rounded-xl border border-border bg-panel px-5 py-5">
      <p className="overline">{label}</p>
      <p className="num mt-2 text-[34px] font-bold leading-none tracking-[-0.02em] text-ink">{value}</p>
      {sub && <p className={`mt-2 text-[14px] leading-snug ${tone === "warn" ? "text-warn-ink" : "text-muted"}`}>{sub}</p>}
    </div>
  );
}

export default function Simulator({
  rows,
  recommended,
  baselineRate,
  validationN,
}: {
  rows: CutoffRow[];
  recommended: number;
  baselineRate: number;
  validationN: number;
}) {
  const [value, setValue] = useState(recommended);
  const row = useMemo(() => lookupCutoff(rows, value), [rows, value]);
  const step = cutoffStep(rows);
  const min = rows[0].cutoff;
  const max = rows[rows.length - 1].cutoff;
  const delta = (row.bad_rate - baselineRate) * 100;

  return (
    <div className="space-y-8">
      <section aria-labelledby="slider-label" className="rounded-xl border border-border bg-panel p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <label id="slider-label" htmlFor="cutoff" className="text-[20px] font-bold text-ink">
            Approval cut-off: <span className="num">{row.cutoff}</span>
          </label>
          <button
            type="button"
            onClick={() => setValue(recommended)}
            disabled={row.cutoff === recommended}
            className="rounded-full border border-border bg-bg px-4 py-1 text-[15px] text-ink disabled:opacity-50"
          >
            Reset to recommended ({recommended})
          </button>
        </div>
        <p className="mt-1 text-[15px] text-muted">Applicants scoring at or above the cut-off are approved.</p>
        <input
          id="cutoff"
          type="range"
          className="cutoff-slider mt-5"
          min={min}
          max={max}
          step={step}
          value={row.cutoff}
          onChange={(e) => setValue(Number(e.target.value))}
          aria-valuetext={`Cut-off ${row.cutoff}: approval ${pct(row.approval_rate)}, payment-difficulty rate ${pct(row.bad_rate, 2)}`}
        />
        <div className="num mt-1 flex justify-between text-[13px] text-muted">
          <span>{min} · approve everyone</span>
          <span>{max}</span>
        </div>
        <p className="mt-5 text-[19px] leading-relaxed text-ink" aria-live="polite">
          At {row.cutoff}, you approve {pct(row.approval_rate)} of applicants; {pct(row.bad_rate, 2)} of them have payment
          difficulties, versus {pct(baselineRate, 2)} if you approved everyone.
        </p>
      </section>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Approval rate" value={pct(row.approval_rate)} sub={`${int(row.approved)} of ${int(validationN)} validation applicants`} />
        <Kpi
          label="Payment-difficulty rate"
          value={pct(row.bad_rate, 2)}
          sub={`${pp(delta, 2)} vs the ${pct(baselineRate, 2)} baseline · among approved`}
        />
        <Kpi
          label="Applicants approved"
          value={int(row.approved)}
          sub={`${int(row.bads_avoided)} with difficulties declined · ${int(row.goods_rejected)} who would repay declined`}
        />
        <Kpi label="Expected profit" value={money(row.profit)} sub="Illustrative, assumption-based" tone="warn" />
      </div>

      <ChartCard
        title="The trade-off"
        subtitle="Approval rate and payment-difficulty rate among approved, at every cut-off · validation split"
        legend={[
          { label: "Approval rate (left axis)", color: C.navy },
          { label: "Payment-difficulty rate (right axis)", color: C.green },
          { label: "Recommended", color: C.ink, dashed: true },
          { label: "Selected", color: C.rust },
        ]}
        caption={`Raising the cut-off from ${min} to ${row.cutoff} lowers approval to ${pct(row.approval_rate)} and the payment-difficulty rate to ${pct(row.bad_rate, 2)}.`}
        source="outputs/cutoff_table.csv"
        claims={["CUT-001"]}
      >
        <TradeoffChart rows={rows} selected={row.cutoff} recommended={recommended} />
      </ChartCard>

      <ChartCard
        title="Illustrative profit by cut-off"
        subtitle="Goods approved × loan × margin − cases with difficulties approved × loan × loss · validation split"
        legend={[
          { label: "Illustrative profit", color: C.rust },
          { label: "Recommended", color: C.ink, dashed: true },
        ]}
        caption={`At ${row.cutoff} the illustrative profit is ${money(row.profit)} under the assumptions below.`}
        source="outputs/cutoff_table.csv, config/assumptions.yaml"
        claims={["CUT-001", "CUT-003"]}
      >
        <ProfitChart rows={rows} selected={row.cutoff} recommended={recommended} />
      </ChartCard>
    </div>
  );
}
