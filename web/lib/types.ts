export type Verdict = "LIKELY_SCAM" | "UNCLEAR" | "NO_STRONG_SIGNALS";
export type Severity = "HIGH" | "MEDIUM" | "LOW";
export type Language = "english" | "hinglish";

export interface ExplainedSignal {
  id: string;
  severity: Severity;
  source: string;
  title: string;
  detail: string;
  quote: string;
}

export interface UrlReport {
  display: string;
  host: string | null;
  registered_domain: string | null;
  signal_ids: string[];
  not_checked: string[];
}

export interface Analysis {
  verdict: Verdict;
  reasons: string[];
  headline: string;
  signals: ExplainedSignal[];
  urls: UrlReport[];
  guidance: string[];
  not_checked: string[];
  pii_detected: string[];
  model: { status: string; label: string | null; model_id: string | null; dropped_evidence: number };
  language: Language;
  versions: Record<string, string>;
}

export interface Example {
  id: string;
  title: string;
  language: Language;
  text: string;
  note: string;
}

export interface Health {
  status: string;
  versions: Record<string, string>;
  llm_configured: boolean;
  llm_model_id: string | null;
}

export interface Rate {
  k: number;
  n: number;
  rate: number | null;
  lo: number | null;
  hi: number | null;
}

export interface CoreMetrics {
  scam_recall: Rate;
  dangerous_miss_rate: Rate;
  false_alarm_rate_legitimate: Rate;
  unclear_rate_non_ambiguous: Rate;
  false_alarm_rate_promotional: Rate;
  unclear_rate_by_label: Record<string, Rate>;
}

export type Confusion = Record<string, Record<Verdict, number>>;

export interface SystemResult {
  description: string;
  config: Record<string, unknown>;
  ranking_auc?: { auc: number | null; n_pos: number; n_neg: number };
  metrics: {
    n: number;
    overall: CoreMetrics;
    by_language: Record<string, CoreMetrics>;
    language_gap_hinglish_minus_english: Record<string, number | null>;
    false_alarm_by_legit_category: Record<string, Rate>;
    scam_recall_by_category: Record<string, Rate>;
    confusion: { overall: Confusion; by_language: Record<string, Confusion>; by_category: Record<string, Confusion> };
    bootstrap: Record<string, unknown>;
  };
}

export interface BenchmarkReport {
  meta: {
    data_label: string;
    synthetic_only: boolean;
    split: string;
    seed: number;
    n_train: number;
    n_evaluated: number;
    versions: Record<string, string>;
    manifest: { sha256: string; counts: Record<string, number> };
    dataset: { sha256: string };
    model: { model_id: string | null; note?: string };
  };
  systems: Record<string, SystemResult>;
}

export interface RobustnessSystem {
  description: string;
  constant_verdict: boolean;
  consistency_preserving: Rate;
  consistency_by_transform: Record<string, Rate>;
  consistency_by_language: Record<string, Rate>;
  consistency_by_seed: Record<string, Rate>;
  seed_variation: { min: number; max: number; stdev: number } | null;
  scam_flip_to_no_strong_signals: Rate;
  scam_lost_detection: Rate;
  needs_review_verdicts: Record<string, Partial<Record<Verdict, number>>>;
}

export interface RobustnessExample {
  transform: string;
  preserving: boolean;
  seed: number;
  variant_id: string;
  parent_id: string;
  status: string;
  language: Language;
  label: string | null;
  parent_text: string;
  variant_text: string;
  parent_verdict: Verdict;
  variant_verdict: Verdict;
}

export interface RobustnessReport {
  meta: {
    data_label: string;
    generator_version: string;
    seeds: number[];
    parent_splits: string[];
    n_parents: number;
    transforms: { name: string; preserving: boolean; languages: string[] }[];
    counts: Record<string, number>;
  };
  systems: Record<string, RobustnessSystem>;
  examples: RobustnessExample[];
}
