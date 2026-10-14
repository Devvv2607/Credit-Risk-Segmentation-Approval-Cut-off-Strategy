import type { CutoffRow } from "./data";

/** Snap any slider value to the nearest cut-off step present in the table. */
export function snapCutoff(rows: CutoffRow[], value: number): number {
  if (rows.length === 0) throw new Error("empty cut-off table");
  let best = rows[0].cutoff;
  for (const r of rows) {
    if (Math.abs(r.cutoff - value) < Math.abs(best - value)) best = r.cutoff;
  }
  return best;
}

/** The cut-off table row for a slider value (snapped to the table's steps). */
export function lookupCutoff(rows: CutoffRow[], value: number): CutoffRow {
  const c = snapCutoff(rows, value);
  const row = rows.find((r) => r.cutoff === c);
  if (!row) throw new Error(`no row for cut-off ${c}`);
  return row;
}

export function cutoffStep(rows: CutoffRow[]): number {
  return rows.length > 1 ? rows[1].cutoff - rows[0].cutoff : 1;
}
