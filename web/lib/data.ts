/**
 * Every figure on the site is read from the JSON files in public/data, which are
 * written by src/export_web.py. Nothing numeric is typed into page copy.
 */
import assumptionsJson from "@/public/data/assumptions.json";
import baselineJson from "@/public/data/baseline.json";
import claimsJson from "@/public/data/claims_rendered.json";
import cutoffJson from "@/public/data/cutoff_table.json";
import ivJson from "@/public/data/iv_summary.json";
import ksJson from "@/public/data/ks_curve.json";
import manifestJson from "@/public/data/data_manifest.json";
import metricsJson from "@/public/data/metrics.json";
import recommendationJson from "@/public/data/recommendation.json";
import rocJson from "@/public/data/roc_points.json";
import scoreDistJson from "@/public/data/score_distribution.json";
import scorecardJson from "@/public/data/scorecard.json";
import scorecardSummaryJson from "@/public/data/scorecard_summary.json";
import segmentsJson from "@/public/data/segments.json";
import sensitivityJson from "@/public/data/sensitivity.json";
import settingsJson from "@/public/data/settings.json";
import siteJson from "@/public/data/site.json";
import sourcesJson from "@/public/data/sources.json";
import splitJson from "@/public/data/split_summary.json";
import validationJson from "@/public/data/validation_report.json";

export type Segment = {
  dimension: string;
  segment: string;
  n: number;
  bads: number;
  bad_rate: number;
  ci_low: number;
  ci_high: number;
  lift: number;
  portfolio_share: number;
  risk_rank: number;
  segment_order: number;
  dimension_complete: boolean;
};
export type CutoffRow = {
  cutoff: number;
  approved: number;
  approval_rate: number;
  goods_approved: number;
  bads_approved: number;
  bad_rate: number;
  bads_avoided: number;
  goods_rejected: number;
  profit: number;
};
export type IvRow = { feature: string; dtype: string; iv: number; n_bins: number; leak_flag: boolean; decision: string; reason: string };
export type ScorecardRow = {
  feature: string;
  bin_index: number;
  bin: string;
  count: number;
  bad_rate: number | null;
  woe: number;
  coefficient: number;
  points_exact: number;
  points: number;
};
export type ScoreBand = {
  split: string;
  band_order: number;
  score_band: string;
  band_low: number | null;
  band_high: number | null;
  count: number;
  bads: number;
  bad_rate: number | null;
  share: number;
};
export type SplitMetrics = { n: number; auc: number; gini: number; ks: number; label?: string };
export type ClaimValue = { raw: number | string; formatted: string; format: string; source: string };
export type Claim = { id: string; group: string; title: string; text: string; sources: string[]; values: Record<string, ClaimValue> };
export type SensitivityRow = {
  avg_loan_level: string;
  margin_level: string;
  loss_given_bad_level: string;
  avg_loan: number;
  margin: number;
  loss_given_bad: number;
  n_changed: number;
  recommended_cutoff: number;
  approval_rate: number;
  bad_rate: number;
  profit: number;
  shift_vs_base: number;
};
export type Assumption = { value: number; low: number; high: number; label: string; note: string };

export const assumptions = assumptionsJson as unknown as {
  currency: string;
  avg_loan: Assumption;
  margin: Assumption;
  loss_given_bad: Assumption;
  excluded: string[];
};
export const baseline = baselineJson as {
  applications: number;
  bads: number;
  baseline_rate: number;
  min_segment_size: number;
  dimensions: string[];
  dimensions_with_excluded_segments: string[];
};
export const claims = (claimsJson as unknown as { claims: Claim[] }).claims;
export const cutoffTable = cutoffJson as unknown as CutoffRow[];
export const ivSummary = ivJson as unknown as IvRow[];
export const ksCurve = ksJson as unknown as { score_threshold: number; cum_bad_share: number; cum_good_share: number; ks: number }[];
export const manifest = manifestJson as {
  dataset: string;
  source_url: string;
  loaded_at: string;
  files: { file: string; table: string; rows: number; columns: number; bytes: number; sha256: string }[];
};
export const metrics = metricsJson as unknown as {
  model: string;
  features: string[];
  features_selected_by_binning: string[];
  removed_for_sign: string[];
  validation_gini_before_sign_fix: number;
  train: SplitMetrics;
  validation: SplitMetrics;
  test: SplitMetrics;
  benchmark: { model: string; n_features: number; trained_on: string; validation: SplitMetrics; test: SplitMetrics };
  train_validation_gini_gap: number;
  validation_test_gini_gap: number;
  benchmark_test_gini_gap: number;
  baseline_rate: number;
  unexpected_signs_remaining: string[];
};
export const recommendation = recommendationJson as unknown as {
  cutoff: number;
  rule: string;
  max_difficulty_rate: number;
  selected_on: string;
  label: string;
  validation: {
    n: number;
    approved: number;
    approval_rate: number;
    bad_rate: number;
    bads_avoided: number;
    goods_rejected: number;
    profit: number;
    baseline_rate: number;
    profit_approve_all: number;
    bad_rate_reduction_pp: number;
    bad_rate_relative_reduction: number;
  };
  unconstrained_max_profit: { cutoff: number; approval_rate: number; bad_rate: number; profit: number };
  sensitivity: {
    scenarios: number;
    min_cutoff: number;
    max_cutoff: number;
    max_abs_shift: number;
    one_at_a_time_min_cutoff: number;
    one_at_a_time_max_cutoff: number;
  };
  test: {
    n: number;
    approved: number;
    approval_rate: number;
    bad_rate: number;
    baseline_rate: number;
    bad_rate_reduction_pp: number;
    approval_rate_diff_pp_vs_validation: number;
    bad_rate_diff_pp_vs_validation: number;
    consistent_with_validation: boolean;
    consistency_rule: string;
  };
};
export const rocPoints = rocJson as unknown as { fpr: number; tpr: number; score_threshold: number | null }[];
export const scoreDistribution = scoreDistJson as unknown as ScoreBand[];
export const scorecard = scorecardJson as unknown as ScorecardRow[];
export const scorecardSummary = scorecardSummaryJson as unknown as {
  base_score: number;
  base_odds: number;
  pdo: number;
  factor: number;
  offset: number;
  n_features: number;
  max_abs_score_vs_points_difference: number;
  non_monotonic_bands_validation: string[];
  non_monotonic_bands_test: string[];
  optbinning_crosscheck: { ran: boolean; comparable?: boolean; rows_compared?: number; max_abs_point_difference?: number; note?: string };
};
export const segments = segmentsJson as unknown as Segment[];
export const sensitivity = sensitivityJson as unknown as SensitivityRow[];
export const settings = settingsJson as unknown as {
  seed: number;
  split: { train: number; validation: number; test: number; max_rate_gap_pp: number };
  min_segment_size: number;
  binning: { iv_min: number; iv_leak_flag: number; corr_max: number; max_features: number; min_bin_size: number; max_n_bins: number };
  protected_attributes: string[];
  cutoff: { step: number; rule: string; max_difficulty_rate: number };
  scorecard: { base_score: number; base_odds: number; pdo: number };
  candidates_evaluated: number;
  selected_by_binning: number;
  woe_convention: string;
  leak_flags: string[];
  python_version: string;
};
export const site = siteJson as {
  author: string;
  published: string;
  site_url: string;
  github_url: string;
  linkedin_url: string;
  powerbi_url: string;
  data_loaded: string;
};
export const sources = sourcesJson as unknown as {
  file: string;
  title: string;
  publisher: string;
  url: string;
  fields_used: string[];
  fields_note: string;
  licence: string;
  access: string;
  limitations: string;
  rows: number;
  columns: number;
  sha256: string;
  retrieved: string;
}[];
export const splitSummary = splitJson as unknown as {
  population: number;
  baseline_rate: number;
  splits: Record<"train" | "validation" | "test", { n: number; share: number; bads: number; rate: number; gap_pp_vs_baseline: number }>;
};
export const validation = validationJson as unknown as {
  passed: number;
  total: number;
  all_passed: boolean;
  checks: { check: string; status: string; detail: string }[];
};

export function claim(id: string): Claim {
  const c = claims.find((x) => x.id === id);
  if (!c) throw new Error(`claim ${id} not found in claims_rendered.json`);
  return c;
}

/** Display names for internal feature identifiers. */
export const FEATURE_LABELS: Record<string, string> = {
  EXT_SOURCE_1: "External score 1",
  EXT_SOURCE_2: "External score 2",
  EXT_SOURCE_3: "External score 3",
  years_employed: "Years employed",
  bureau_debt_to_credit: "Bureau debt-to-credit",
  OCCUPATION_TYPE: "Occupation",
  ORGANIZATION_TYPE: "Employer type",
  credit_to_goods: "Credit-to-goods ratio",
  prev_refusal_rate: "Previous refusal rate",
  REGION_RATING_CLIENT_W_CITY: "Region rating (with city)",
  AMT_GOODS_PRICE: "Goods price",
  NAME_EDUCATION_TYPE: "Education",
  DAYS_LAST_PHONE_CHANGE: "Days since phone change",
  age_years: "Age",
  NAME_INCOME_TYPE: "Income type",
};
export const featureLabel = (f: string) => FEATURE_LABELS[f] ?? f;

/** The declared recommendation rule as a readable sentence (the ceiling comes from settings). */
export const ruleText = () =>
  recommendation.rule.replace(
    "<= max_difficulty_rate",
    `is at most ${(recommendation.max_difficulty_rate * 100).toFixed(1)}%`,
  );
