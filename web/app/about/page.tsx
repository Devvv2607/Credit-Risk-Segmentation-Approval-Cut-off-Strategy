import type { Metadata } from "next";
import { MaybeLink, PageHeader, Panel } from "@/components/ui";
import { site } from "@/lib/data";

export const metadata: Metadata = { title: "About" };

export default function About() {
  return (
    <div className="max-w-prose">
      <PageHeader title={site.author} subtitle="About the analyst" />
      <Panel>
        <p className="overline">Bio · to be written</p>
        <p className="mt-3 text-muted">
          A short bio will go here. Edit <code>web/app/about/page.tsx</code> to add it.
        </p>
      </Panel>
      <p className="mt-8 flex flex-wrap gap-x-8 gap-y-3">
        <MaybeLink href={site.github_url} github>
          GitHub
        </MaybeLink>
        <MaybeLink href={site.linkedin_url}>LinkedIn</MaybeLink>
      </p>
    </div>
  );
}
