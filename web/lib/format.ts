export const pct = (v: number | null | undefined, digits = 1) =>
  v === null || v === undefined || Number.isNaN(v) ? "—" : `${(v * 100).toFixed(digits)}%`;

export const pp = (v: number, digits = 1) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(digits)}pp`;

export const int = (v: number) => Math.round(v).toLocaleString("en-US");

export const num = (v: number, digits = 3) => v.toFixed(digits);

export const money = (v: number) => {
  const a = Math.abs(v);
  const sign = v < 0 ? "−" : "";
  if (a >= 1e9) return `${sign}${(a / 1e9).toFixed(2)}bn`;
  if (a >= 1e6) return `${sign}${(a / 1e6).toFixed(1)}m`;
  return `${sign}${Math.round(a).toLocaleString("en-US")}`;
};

export const date = (iso: string) =>
  new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });

/** Axis tick: whole percent when exact, otherwise one decimal. */
export const pctTick = (v: number) => `${Number((v * 100).toFixed(1))}%`;
