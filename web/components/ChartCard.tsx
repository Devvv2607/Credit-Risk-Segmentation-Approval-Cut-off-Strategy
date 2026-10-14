export type LegendItem = { label: string; color: string; dashed?: boolean };

export function LegendPills({ items }: { items: LegendItem[] }) {
  return (
    <ul className="flex flex-wrap gap-2" aria-label="Legend">
      {items.map((l) => (
        <li
          key={l.label}
          className="inline-flex items-center gap-2 rounded-full border border-border bg-bg px-3 py-0.5 text-[14px] text-ink"
        >
          {l.dashed ? (
            <span aria-hidden className="inline-block w-4 border-t-2 border-dashed" style={{ borderColor: l.color }} />
          ) : (
            <span aria-hidden className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: l.color }} />
          )}
          {l.label}
        </li>
      ))}
    </ul>
  );
}

/** Panel with title, subtitle, legend pills, the chart, a one-sentence takeaway and a source line. */
export default function ChartCard({
  title,
  subtitle,
  legend,
  caption,
  source,
  claims,
  children,
  controls,
}: {
  title: string;
  subtitle?: string;
  legend?: LegendItem[];
  caption?: React.ReactNode;
  source: string;
  claims?: string[];
  children: React.ReactNode;
  controls?: React.ReactNode;
}) {
  return (
    <figure className="min-w-0 rounded-xl border border-border bg-panel p-5 sm:p-6">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-[20px] font-bold leading-snug text-ink">{title}</h3>
          {subtitle && <p className="text-[15px] leading-snug text-muted">{subtitle}</p>}
        </div>
        {controls}
      </div>
      {legend && (
        <div className="mb-3">
          <LegendPills items={legend} />
        </div>
      )}
      <div className="min-w-0">{children}</div>
      <figcaption className="mt-4 space-y-1">
        {caption && <p className="text-[16px] leading-relaxed text-ink">{caption}</p>}
        <p className="text-[13px] text-muted">
          Source: {source}
          {claims && claims.length > 0 && <> · Claims: {claims.join(", ")}</>}
        </p>
      </figcaption>
    </figure>
  );
}
