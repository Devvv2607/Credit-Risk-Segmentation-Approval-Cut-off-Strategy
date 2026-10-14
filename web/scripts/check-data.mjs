// Fails if any JSON file the site imports is missing or empty.
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const text = readFileSync(join(root, "lib", "data.ts"), "utf8");
const imported = new Set([...text.matchAll(/from\s+"@\/public\/data\/([\w.-]+\.json)"/g)].map((m) => m[1]));

let failed = imported.size === 0 ? 1 : 0;
for (const f of [...imported].sort()) {
  const p = join(root, "public", "data", f);
  if (!existsSync(p)) {
    console.error(`MISSING ${f}`);
    failed++;
    continue;
  }
  const data = JSON.parse(readFileSync(p, "utf8"));
  const empty = data === null || (Array.isArray(data) ? data.length === 0 : Object.keys(data).length === 0);
  if (empty) {
    console.error(`EMPTY   ${f}`);
    failed++;
  } else {
    console.log(`ok      ${f}`);
  }
}
for (const f of readdirSync(join(root, "public", "data")).filter((x) => x.endsWith(".json"))) {
  if (!imported.has(f)) console.log(`unused  ${f}`);
}
if (failed) {
  console.error(`${failed} data file problem(s)`);
  process.exit(1);
}
console.log(`${imported.size} data files present and non-empty`);
