import type { Metadata } from "next";
import CodeBlock from "@/components/CodeBlock";
import { H2, PageHeader, Table } from "@/components/ui";
import { manifest, settings, validation } from "@/lib/data";
import { date, int } from "@/lib/format";

export const metadata: Metadata = { title: "Reproducibility" };

const COMMANDS = `# 1. Python ${"3.11"} environment and packages
make setup

# 2. Confirm the Kaggle CSVs are in data/raw/
make data-check

# 3. Full pipeline: raw CSVs -> outputs/ -> web/public/data/
make all

# 4. Python tests, web lint, typecheck, unit test and data check
make test

# 5. Install and build the static site (web/out/)
make web

# Windows without make: python tasks.py <target>, e.g.
python tasks.py all`;

export default function Reproducibility() {
  return (
    <div className="max-w-wide">
      <PageHeader title="Run it yourself" subtitle="Same data, same seed, same numbers" />
      <div className="max-w-prose">
        <p>
          The pipeline is deterministic: Python {settings.python_version}, random seed {settings.seed} everywhere, and file hashes
          recorded for the raw data. Running it twice produces byte-identical outputs. Download the data from Kaggle after
          accepting the competition rules (<code>kaggle competitions download -c home-credit-default-risk</code>) and unzip into{" "}
          <code>data/raw/</code>.
        </p>
      </div>

      <H2 id="commands">Commands</H2>
      <CodeBlock code={COMMANDS} label="commands" />

      <H2 id="manifest">Data manifest</H2>
      <p className="mb-5 max-w-prose">Loaded {date(manifest.loaded_at)}. Compare the hashes with your own download.</p>
      <Table
        caption="Raw files used"
        head={["File", "Rows", "Columns", "SHA-256"]}
        align={["l", "r", "r", "l"]}
        rows={manifest.files.map((f) => [
          f.file,
          int(f.rows),
          f.columns,
          <code key="h" className="break-all text-[13px]">
            {f.sha256}
          </code>,
        ])}
      />

      <H2 id="validation">Validation report</H2>
      <p className="mb-5 max-w-prose">
        <strong>
          {validation.passed} of {validation.total}
        </strong>{" "}
        cross-stage checks pass (<code>src/validate.py</code>, written to <code>outputs/validation_report.json</code>).
      </p>
      <Table
        caption="Validation checks"
        head={["Check", "Status", "Detail"]}
        rows={validation.checks.map((c) => [
          c.check,
          <span key="s" className={c.status === "pass" ? "font-semibold text-green" : "font-semibold text-rust"}>
            {c.status === "pass" ? "Pass" : "Fail"}
          </span>,
          <span key="d" className="break-all text-[14px] text-muted">
            {c.detail}
          </span>,
        ])}
      />
    </div>
  );
}
