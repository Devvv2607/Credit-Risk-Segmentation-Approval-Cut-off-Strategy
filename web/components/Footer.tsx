import { date } from "@/lib/format";
import { manifest, site } from "@/lib/data";
import { ExtLink, MaybeLink } from "./ui";

export default function Footer() {
  return (
    <footer className="border-t border-border px-4 py-10 text-[15px] leading-relaxed text-muted min-[900px]:px-[60px]">
      <div className="max-w-prose space-y-3">
        <p>
          Independent analysis of the public Home Credit Default Risk dataset. Not affiliated with Home Credit or any lender, and
          not Indian lending data. Profit figures rest on labelled, illustrative assumptions.
        </p>
        <p>
          Analysis by {site.author} · Published {date(site.published)} · Last updated {date(manifest.loaded_at)}
        </p>
        <p className="flex flex-wrap gap-x-6 gap-y-2">
          <ExtLink href="/methodology/">Methodology</ExtLink>
          <ExtLink href="/reproducibility/">Reproducibility</ExtLink>
          <MaybeLink href={site.github_url} github>
            Source code
          </MaybeLink>
        </p>
      </div>
    </footer>
  );
}
