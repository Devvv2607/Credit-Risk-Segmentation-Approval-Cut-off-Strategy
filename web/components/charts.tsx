"use client";

import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CutoffRow, IvRow, ScoreBand, Segment } from "@/lib/data";
import { featureLabel } from "@/lib/data";
import { C } from "@/lib/colors";
import { int, money, num, pct, pctTick } from "@/lib/format";


const tooltipStyle = {
  contentStyle: {
    background: "var(--tooltip-bg)",
    border: "1px solid var(--border)",
    borderRadius: 10,
    color: "var(--ink)",
    fontSize: 14,
    lineHeight: 1.5,
    boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
  },
  labelStyle: { color: "var(--ink)", fontWeight: 600 },
  itemStyle: { color: "var(--ink)" },
};

const axis = { stroke: C.grid, tickLine: false, tick: { fill: "var(--ink-muted)", fontSize: 13 } } as const;

/* ---------- Segment risk ---------- */

export function SegmentChart({
  segments,
  dimensions,
  initial,
  baseline,
}: {
  segments: Segment[];
  dimensions: string[];
  initial: string;
  baseline: number;
}) {
  const [dim, setDim] = useState(initial);
  const rows = segments
    .filter((s) => s.dimension === dim)
    .sort((a, b) => a.segment_order - b.segment_order || b.bad_rate - a.bad_rate)
    .map((s) => ({ ...s, label: s.segment, err: [s.bad_rate - s.ci_low, s.ci_high - s.bad_rate] }));
  const height = Math.max(200, rows.length * 44 + 50);
  return (
    <div>
      <label className="mb-3 flex flex-wrap items-center gap-3 text-[15px] text-muted">
        Dimension
        <select
          value={dim}
          onChange={(e) => setDim(e.target.value)}
          className="rounded-md border border-border bg-bg px-2 py-1 text-[15px] text-ink"
        >
          {dimensions.map((d) => (
            <option key={d}>{d}</option>
          ))}
        </select>
      </label>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 8 }}>
          <CartesianGrid horizontal={false} />
          <XAxis type="number" tickFormatter={pctTick} {...axis} />
          <YAxis type="category" dataKey="label" width={130} {...axis} />
          <Tooltip
            {...tooltipStyle}
            cursor={{ fill: "var(--border)", opacity: 0.4 }}
            formatter={(v: number, _n, p) => [
              `${pct(v)} (95% CI ${pct(p.payload.ci_low)}–${pct(p.payload.ci_high)}) · ${int(p.payload.n)} applicants`,
              "Payment-difficulty rate",
            ]}
          />
          <ReferenceLine x={baseline} stroke={C.ink} strokeDasharray="4 4" label={{ value: "Baseline", position: "top", fill: "var(--ink)", fontSize: 12 }} />
          <Bar dataKey="bad_rate" radius={[0, 4, 4, 0]} isAnimationActive={false}>
            {rows.map((r) => (
              <Cell key={r.segment} fill={r.bad_rate > baseline ? C.rust : C.green} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ---------- Cut-off trade-off ---------- */

export function TradeoffChart({
  rows,
  selected,
  recommended,
  height = 320,
}: {
  rows: CutoffRow[];
  selected?: number;
  recommended: number;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={rows} margin={{ top: 16, right: 12, bottom: 4, left: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="cutoff" type="number" domain={["dataMin", "dataMax"]} {...axis} />
        <YAxis yAxisId="a" tickFormatter={pctTick} domain={[0, 1]} width={48} {...axis} />
        <YAxis yAxisId="b" orientation="right" tickFormatter={pctTick} width={44} {...axis} />
        <Tooltip
          {...tooltipStyle}
          labelFormatter={(l) => `Cut-off ${l}`}
          formatter={(v: number, name) => [pct(v), name]}
        />
        <ReferenceLine
          yAxisId="a"
          x={recommended}
          stroke={C.ink}
          strokeDasharray="4 4"
          label={{ value: "Recommended", position: "insideTopLeft", fill: "var(--ink)", fontSize: 12 }}
        />
        {selected !== undefined && selected !== recommended && (
          <ReferenceLine yAxisId="a" x={selected} stroke={C.rust} strokeWidth={2} label={{ value: "Selected", position: "insideTopRight", fill: "var(--series-3)", fontSize: 12 }} />
        )}
        <Line yAxisId="a" type="linear" dataKey="approval_rate" name="Approval rate" stroke={C.navy} strokeWidth={2.5} dot={false} isAnimationActive={false} />
        <Line yAxisId="b" type="linear" dataKey="bad_rate" name="Payment-difficulty rate (approved)" stroke={C.green} strokeWidth={2.5} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function ProfitChart({ rows, selected, recommended }: { rows: CutoffRow[]; selected?: number; recommended: number }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={rows} margin={{ top: 16, right: 12, bottom: 4, left: 4 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="cutoff" type="number" domain={["dataMin", "dataMax"]} {...axis} />
        <YAxis tickFormatter={(v) => money(v)} width={64} {...axis} />
        <Tooltip {...tooltipStyle} labelFormatter={(l) => `Cut-off ${l}`} formatter={(v: number) => [money(v), "Illustrative profit"]} />
        <ReferenceLine y={0} stroke={C.muted} />
        <ReferenceLine x={recommended} stroke={C.ink} strokeDasharray="4 4" label={{ value: "Recommended", position: "insideTopLeft", fill: "var(--ink)", fontSize: 12 }} />
        {selected !== undefined && selected !== recommended && <ReferenceLine x={selected} stroke={C.rust} strokeWidth={2} />}
        <Line type="linear" dataKey="profit" name="Illustrative profit" stroke={C.rust} strokeWidth={2.5} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

/* ---------- Score bands ---------- */

export function ScoreBandChart({ bands }: { bands: ScoreBand[] }) {
  const order = Array.from(new Set(bands.map((b) => b.band_order))).sort((a, b) => a - b);
  const rows = order.map((o) => {
    const v = bands.find((b) => b.band_order === o && b.split === "validation");
    const t = bands.find((b) => b.band_order === o && b.split === "test");
    return { band: v?.score_band ?? t?.score_band, validation: v?.bad_rate, test: t?.bad_rate, vn: v?.count, tn: t?.count };
  });
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="band" {...axis} interval={0} tick={{ fill: "var(--ink-muted)", fontSize: 12 }} />
        <YAxis tickFormatter={pctTick} width={48} {...axis} />
        <Tooltip
          {...tooltipStyle}
          cursor={{ fill: "var(--border)", opacity: 0.4 }}
          labelFormatter={(l) => `Score ${l}`}
          formatter={(v: number, name, p) => [`${pct(v)} · ${int(name === "Validation" ? p.payload.vn : p.payload.tn)} applicants`, name]}
        />
        <Bar dataKey="validation" name="Validation" fill={C.navy} radius={[4, 4, 0, 0]} isAnimationActive={false} />
        <Bar dataKey="test" name="Test" fill={C.green} radius={[4, 4, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ---------- IV ---------- */

const IV_BANDS = [
  { from: 0.02, to: 0.1, label: "Weak" },
  { from: 0.1, to: 0.3, label: "Medium" },
  { from: 0.3, to: 0.5, label: "Strong" },
];

export function IvChart({ rows, modelFeatures }: { rows: IvRow[]; modelFeatures: string[] }) {
  const data = rows
    .filter((r) => r.decision === "selected")
    .sort((a, b) => b.iv - a.iv)
    .map((r) => ({ ...r, label: featureLabel(r.feature), inModel: modelFeatures.includes(r.feature) }));
  const max = Math.max(...data.map((d) => d.iv));
  return (
    <ResponsiveContainer width="100%" height={data.length * 34 + 60}>
      <BarChart data={data} layout="vertical" margin={{ top: 20, right: 24, bottom: 4, left: 8 }}>
        {IV_BANDS.filter((b) => b.from < max).map((b, i) => (
          <ReferenceArea
            key={b.label}
            x1={b.from}
            x2={Math.min(b.to, max * 1.08)}
            fill={i % 2 ? "var(--border)" : "transparent"}
            fillOpacity={0.5}
            label={{ value: b.label, position: "insideTop", fill: "var(--ink-muted)", fontSize: 12, dy: -18 }}
          />
        ))}
        <CartesianGrid horizontal={false} />
        <XAxis type="number" domain={[0, max * 1.08]} tickFormatter={(v) => num(v, 2)} {...axis} />
        <YAxis type="category" dataKey="label" width={190} {...axis} />
        <Tooltip
          {...tooltipStyle}
          cursor={{ fill: "var(--border)", opacity: 0.4 }}
          formatter={(v: number, _n, p) => [`${num(v)}${p.payload.inModel ? "" : " · removed at the coefficient-sign review"}`, "Information value"]}
        />
        <Bar dataKey="iv" radius={[0, 4, 4, 0]} isAnimationActive={false}>
          {data.map((d) => (
            <Cell key={d.feature} fill={d.inModel ? C.navy : C.muted} fillOpacity={d.inModel ? 1 : 0.5} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ---------- ROC and KS ---------- */

export function RocChart({ points }: { points: { fpr: number; tpr: number }[] }) {
  const data = points.map((p) => ({ fpr: p.fpr, tpr: p.tpr, chance: p.fpr }));
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 16, left: 0 }}>
        <CartesianGrid />
        <XAxis
          dataKey="fpr"
          type="number"
          domain={[0, 1]}
          tickFormatter={pctTick}
          label={{ value: "False positive rate", position: "insideBottom", dy: 14, fill: "var(--ink-muted)", fontSize: 13 }}
          {...axis}
        />
        <YAxis domain={[0, 1]} tickFormatter={pctTick} width={48} {...axis} />
        <Tooltip {...tooltipStyle} labelFormatter={(l) => `FPR ${pct(Number(l))}`} formatter={(v: number, n) => [pct(v), n]} />
        <Line dataKey="chance" name="Random" stroke={C.muted} strokeDasharray="4 4" dot={false} isAnimationActive={false} />
        <Line dataKey="tpr" name="True positive rate" stroke={C.navy} strokeWidth={2.5} dot={false} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

export function KsChart({ rows }: { rows: { score_threshold: number; cum_bad_share: number; cum_good_share: number; ks: number }[] }) {
  const best = rows.reduce((a, b) => (b.ks > a.ks ? b : a), rows[0]);
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 16, left: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="score_threshold"
          type="number"
          domain={["dataMin", "dataMax"]}
          label={{ value: "Score", position: "insideBottom", dy: 14, fill: "var(--ink-muted)", fontSize: 13 }}
          {...axis}
        />
        <YAxis domain={[0, 1]} tickFormatter={pctTick} width={48} {...axis} />
        <Tooltip {...tooltipStyle} labelFormatter={(l) => `Score below ${l}`} formatter={(v: number, n) => [pct(v), n]} />
        <ReferenceLine x={best.score_threshold} stroke={C.ink} strokeDasharray="4 4" label={{ value: "Max gap", position: "insideTopLeft", fill: "var(--ink)", fontSize: 12 }} />
        <Line dataKey="cum_bad_share" name="Cumulative share with difficulties" stroke={C.rust} strokeWidth={2.5} dot={false} isAnimationActive={false} />
        <Line dataKey="cum_good_share" name="Cumulative share without" stroke={C.navy} strokeWidth={2.5} dot={false} isAnimationActive={false} />
        <Scatter data={[best]} dataKey="cum_bad_share" fill={C.ink} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
