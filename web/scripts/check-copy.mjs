// Fails if rendered page text says "default rate" or "bad rate". The site's term is
// "payment-difficulty rate". The Methodology page may mention the industry term once,
// inside the single paragraph marked data-terminology-note.
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "out");
if (!existsSync(root)) {
  console.error("out/ not found — run next build first");
  process.exit(1);
}
const walk = (d) => readdirSync(d).flatMap((f) => (statSync(join(d, f)).isDirectory() ? walk(join(d, f)) : [join(d, f)]));
const banned = /\b(default|bad)[\s-]+rates?\b/gi;
let problems = 0;
let notes = 0;
for (const file of walk(root).filter((f) => f.endsWith(".html"))) {
  let html = readFileSync(file, "utf8");
  html = html.replace(/<p[^>]*data-terminology-note[^>]*>[\s\S]*?<\/p>/g, () => {
    notes++;
    return "";
  });
  const visible = html
    .replace(/<script[\s\S]*?<\/script>/g, " ")
    .replace(/<style[\s\S]*?<\/style>/g, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&[a-z#0-9]+;/gi, " ");
  const hits = visible.match(banned);
  if (hits) {
    console.error(`${relative(root, file)}: ${[...new Set(hits)].join(", ")}`);
    problems++;
  }
}
if (notes > 1) {
  console.error(`terminology note appears ${notes} times; only one is allowed`);
  problems++;
}
if (problems) process.exit(1);
console.log("copy check passed: no 'default rate' or 'bad rate' in rendered text");
