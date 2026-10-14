import Link from "next/link";
import { AlertTriangle, ArrowUpRight, Github } from "lucide-react";
import type { Claim } from "@/lib/data";

/** Underlined dark-green link with a ↗ arrow. External links open in a new tab. */
export function ExtLink({
  href,
  children,
  github = false,
  className = "",
}: {
  href: string;
  children: React.ReactNode;
  github?: boolean;
  className?: string;
}) {
  const external = /^https?:\/\//.test(href);
  const cls = `inline text-accent underline decoration-1 underline-offset-[5px] hover:decoration-2 ${className}`;
  const inner = (
    <>
      {github && <Github size={17} aria-hidden className="mr-1 inline-block align-[-0.15em]" />}
      {children}
      <ArrowUpRight size={16} aria-hidden className="ml-0.5 inline-block align-[-0.1em]" />
    </>
  );
  if (external) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className={cls}>
        {inner}
        <span className="sr-only">(opens in a new tab)</span>
      </a>
    );
  }
  return (
    <Link href={href} className={cls}>
      {inner}
    </Link>
  );
}

/** A link to something that may not exist yet. Renders plain text when the URL is empty. */
export function MaybeLink({ href, children, github = false }: { href: string; children: React.ReactNode; github?: boolean }) {
  if (!href) {
    return (
      <span className="inline-flex items-center gap-1 text-muted">
        {github && <Github size={17} aria-hidden className="mr-0.5" />}
        {children} <span className="text-[15px]">(link not yet available)</span>
      </span>
    );
  }
  return (
    <ExtLink href={href} github={github}>
      {children}
    </ExtLink>
  );
}

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="mb-12 max-w-prose">
      <h1 className="text-[44px] font-bold leading-[1.08] tracking-[-0.03em] text-ink sm:text-[64px]">{title}</h1>
      {subtitle && <p className="mt-4 text-[24px] font-medium leading-snug text-muted sm:text-[32px]">{subtitle}</p>}
    </header>
  );
}

export function Warn({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div role="note" className={`flex gap-3 rounded-xl bg-warn-bg px-5 py-4 text-[17px] leading-relaxed text-warn-ink ${className}`}>
      <AlertTriangle size={20} aria-hidden className="mt-1 shrink-0" />
      <div>{children}</div>
    </div>
  );
}

export function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl border border-border bg-panel p-6 ${className}`}>{children}</div>;
}

export function H2({ id, children }: { id?: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="mb-5 mt-16 scroll-mt-24 text-[32px] font-bold leading-tight tracking-[-0.02em] text-ink">
      {children}
    </h2>
  );
}

export function H3({ children, id }: { children: React.ReactNode; id?: string }) {
  return (
    <h3 id={id} className="mb-3 mt-10 scroll-mt-24 text-[23px] font-bold leading-snug text-ink">
      {children}
    </h3>
  );
}

/** A registered claim: rendered sentence, left border, provenance footer. */
export function ClaimBlock({ c }: { c: Claim }) {
  return (
    <blockquote className="border-l-[3px] border-ink py-1 pl-5">
      <p className="text-ink">{c.text}</p>
      <footer className="mt-1 text-[14px] text-muted">
        <span className="font-semibold">{c.id}</span> · {c.sources.join(", ")} · checked against the data on every test run
      </footer>
    </blockquote>
  );
}

export function StatGrid({ items, footnote }: { items: { value: string; label: string }[]; footnote?: React.ReactNode }) {
  return (
    <div>
      <dl className="grid grid-cols-1 overflow-hidden rounded-xl border border-border sm:grid-cols-2 lg:grid-cols-3">
        {items.map((it) => (
          <div key={it.label} className="-mb-px -mr-px border-b border-r border-border px-6 py-6">
            <dd className="num text-[38px] font-bold leading-none tracking-[-0.02em] text-ink">{it.value}</dd>
            <dt className="mt-2 text-[15px] leading-snug text-muted">{it.label}</dt>
          </div>
        ))}
      </dl>
      {footnote && <p className="mt-3 text-[14px] leading-relaxed text-muted">{footnote}</p>}
    </div>
  );
}

export function KV({ rows }: { rows: [string, React.ReactNode, ("warn" | undefined)?][] }) {
  return (
    <dl className="divide-y divide-border">
      {rows.map(([k, v, tone]) => (
        <div key={k} className="grid grid-cols-1 gap-1 py-3 sm:grid-cols-[160px_minmax(0,1fr)] sm:gap-6">
          <dt className="eyebrow pt-1">{k}</dt>
          <dd className={`min-w-0 text-[17px] leading-relaxed ${tone === "warn" ? "text-warn-ink" : "text-ink"}`}>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Table({
  head,
  rows,
  caption,
  align,
}: {
  head: string[];
  rows: React.ReactNode[][];
  caption?: string;
  align?: ("l" | "r")[];
}) {
  return (
    <div className="max-w-full overflow-x-auto rounded-xl border border-border">
      <table className="w-full border-collapse text-[16px]">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead className="bg-panel">
          <tr>
            {head.map((h, i) => (
              <th
                key={h}
                scope="col"
                className={`whitespace-nowrap px-4 py-3 text-[13px] font-semibold uppercase tracking-[0.08em] text-muted ${
                  align?.[i] === "r" ? "text-right" : "text-left"
                }`}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-border">
              {r.map((cell, j) => (
                <td key={j} className={`num px-4 py-2.5 align-top ${align?.[j] === "r" ? "text-right" : "text-left"}`}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
