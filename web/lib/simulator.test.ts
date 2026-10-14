import { describe, expect, it } from "vitest";
import { cutoffTable, recommendation } from "./data";
import { cutoffStep, lookupCutoff, snapCutoff } from "./simulator";

describe("simulator lookup", () => {
  it("returns the exact row for a value on a step", () => {
    for (const r of cutoffTable) expect(lookupCutoff(cutoffTable, r.cutoff)).toBe(r);
  });

  it("snaps values between steps to the nearest step", () => {
    const step = cutoffStep(cutoffTable);
    const r = cutoffTable[Math.floor(cutoffTable.length / 2)];
    expect(snapCutoff(cutoffTable, r.cutoff + step / 2 - 0.01)).toBe(r.cutoff);
    expect(snapCutoff(cutoffTable, r.cutoff - step / 2 + 0.01)).toBe(r.cutoff);
  });

  it("clamps values outside the table to its ends", () => {
    const first = cutoffTable[0];
    const last = cutoffTable[cutoffTable.length - 1];
    expect(lookupCutoff(cutoffTable, first.cutoff - 1000)).toBe(first);
    expect(lookupCutoff(cutoffTable, last.cutoff + 1000)).toBe(last);
  });

  it("finds the recommended cut-off row", () => {
    const row = lookupCutoff(cutoffTable, recommendation.cutoff);
    expect(row.cutoff).toBe(recommendation.cutoff);
    expect(row.approval_rate).toBeCloseTo(recommendation.validation.approval_rate, 9);
  });
});
