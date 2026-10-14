import type { Metadata } from "next";
import { ExtLink, H2, KV, MaybeLink, PageHeader, Panel } from "@/components/ui";
import { baseline, manifest, site, sources } from "@/lib/data";
import { int } from "@/lib/format";

export const metadata: Metadata = { title: "Data & Sources" };

const DOWNLOADS = [
  ["segments.csv", "Segment payment-difficulty rates, lift and intervals"],
  ["iv_summary.csv", "Information value and selection decision for every candidate feature"],
  ["scorecard.csv", "Points per bin"],
  ["cutoff_table.csv", "Approval, payment-difficulty rate and illustrative profit at every cut-off"],
  ["sensitivity.csv", "Recommended cut-off under each assumption scenario"],
  ["score_distribution.csv", "Score bands, validation and test"],
  ["metrics.json", "AUC, Gini and KS per split, plus the benchmark"],
  ["claims_rendered.json", "Every registered claim with its values and sources"],
];

export default function DataPage() {
  return (
    <div className="max-w-wide">
      <PageHeader title="What the study is built on" />
      <p className="-mt-6 mb-10 max-w-prose text-[22px] leading-snug text-muted">
        {manifest.files.length} tables from the {manifest.dataset}: {int(baseline.applications)} applications, linked to{" "}
        {int(manifest.files.find((f) => f.table === "raw_bureau")?.rows ?? 0)} bureau records and{" "}
        {int(manifest.files.find((f) => f.table === "raw_previous_application")?.rows ?? 0)} previous applications.
      </p>

      <div className="space-y-6">
        {sources.map((s) => (
          <Panel key={s.file}>
            <p className="eyebrow">Source · {s.file}</p>
            <h2 className="mb-2 mt-2 text-[22px] font-bold leading-snug text-ink">{s.title}</h2>
            <KV
              rows={[
                ["Publisher", s.publisher],
                [
                  "URL",
                  <ExtLink key="u" href={s.url} className="[overflow-wrap:anywhere]">
                    {s.url.replace(/^https?:\/\//, "")}
                  </ExtLink>,
                ],
                ["Retrieved", s.retrieved],
                ["Size", `${int(s.rows)} rows × ${s.columns} columns`],
                [
                  "Fields used",
                  <div key="f">
                    <ul className="flex flex-wrap gap-1.5" aria-label={`Fields used from ${s.file}`}>
                      {s.fields_used.map((f) => (
                        <li key={f}>
                          <code className="whitespace-nowrap rounded border border-border bg-bg px-1.5 py-0.5 font-mono text-sm text-ink">
                            {f}
                          </code>
                        </li>
                      ))}
                    </ul>
                    <p className="mt-2 text-[15px] text-muted">{s.fields_note}</p>
                  </div>,
                ],
                ["Licence / use", s.licence],
                ["Access method", <code key="a" className="text-[15px] [overflow-wrap:anywhere]">{s.access}</code>],
                ["Limitations", s.limitations, "warn"],
              ]}
            />
          </Panel>
        ))}
      </div>

      <H2 id="downloads">Downloads and source code</H2>
      <p className="mb-5 max-w-prose">
        Aggregated results only — no applicant-level rows, identifiers or scores are published, in line with the competition
        rules.
      </p>
      <ul className="max-w-prose space-y-2">
        {DOWNLOADS.map(([f, d]) => (
          <li key={f} className="flex flex-wrap items-baseline gap-x-3">
            <a href={`/downloads/${f}`} download className="font-mono text-[16px] text-accent underline underline-offset-4">
              {f}
            </a>
            <span className="text-[16px] text-muted">{d}</span>
          </li>
        ))}
      </ul>
      <p className="mt-6">
        <MaybeLink href={site.github_url} github>
          GitHub repository
        </MaybeLink>
      </p>
      <p className="mt-6 max-w-prose rounded-xl border border-border px-5 py-4 text-[17px]">
        {site.powerbi_url ? (
          <ExtLink href={site.powerbi_url}>Power BI dashboard</ExtLink>
        ) : (
          <>
            <strong>Not yet available:</strong> a Power BI dashboard. It will be linked here only when it exists.
          </>
        )}
      </p>
    </div>
  );
}
