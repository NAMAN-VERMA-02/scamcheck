"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import { api, ApiError, pct } from "@/lib/api";
import type { BenchmarkReport, CoreMetrics, Verdict } from "@/lib/types";
import { ErrorBox, Loading, RateBar, SyntheticBanner } from "@/components/ui";

const VERDICTS: Verdict[] = ["LIKELY_SCAM", "UNCLEAR", "NO_STRONG_SIGNALS"];
type Scope = "overall" | "english" | "hinglish";

export default function BenchmarkLab() {
  const [data, setData] = useState<BenchmarkReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scope, setScope] = useState<Scope>("overall");
  const [system, setSystem] = useState("B4-engine");

  // State is only set in promise callbacks, never synchronously inside the effect.
  const load = useCallback(() => {
    api<BenchmarkReport>("/api/reports/benchmark")
      .then((r) => {
        setData(r);
        setError(null);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not load the report."));
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  if (error) return <ErrorBox message={error} onRetry={() => {
    setError(null);
    load();
  }} />;
  if (!data) return <Loading label="Loading benchmark report…" />;

  const systems = Object.entries(data.systems);
  const pick = (m: BenchmarkReport["systems"][string]): CoreMetrics =>
    scope === "overall" ? m.metrics.overall : m.metrics.by_language[scope];
  const sel = data.systems[system] ?? systems[0][1];
  const categories = Object.keys(sel.metrics.false_alarm_by_legit_category);
  const scamCats = Object.keys(sel.metrics.scam_recall_by_category);
  const conf = scope === "overall" ? sel.metrics.confusion.overall : sel.metrics.confusion.by_language[scope];

  return (
    <div className="stack">
      <header>
        <h1 className="h1">Benchmark Lab</h1>
        <p className="lede">
          Five comparable systems on the frozen <code>{data.meta.split}</code> split ({data.meta.n_evaluated} items;
          B2 trained on {data.meta.n_train} train items). Every rate shows its Wilson 95% interval and count.
        </p>
      </header>
      {data.meta.synthetic_only && <SyntheticBanner text={data.meta.data_label} />}

      <div className="toolbar" role="group" aria-label="Language slice">
        {(["overall", "english", "hinglish"] as Scope[]).map((s) => (
          <button key={s} type="button" className={scope === s ? "tab tab-on" : "tab"} aria-pressed={scope === s}
            onClick={() => setScope(s)}>
            {s === "overall" ? "All languages" : s[0].toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      <div className="table-wrap">
        <table className="table">
          <caption>Headline metrics — {scope === "overall" ? "all languages" : scope}</caption>
          <thead>
            <tr>
              <th scope="col">System</th>
              <th scope="col">Scam recall ↑</th>
              <th scope="col">Dangerous misses ↓</th>
              <th scope="col">False alarms (legitimate) ↓</th>
              <th scope="col">Unclear (non-ambiguous) ↓</th>
            </tr>
          </thead>
          <tbody>
            {systems.map(([name, s]) => {
              const m = pick(s);
              return (
                <tr key={name}>
                  <th scope="row">
                    <div>{name}</div>
                    <div className="hint">{s.description}</div>
                  </th>
                  <td><RateBar r={m?.scam_recall} /></td>
                  <td><RateBar r={m?.dangerous_miss_rate} goodLow /></td>
                  <td><RateBar r={m?.false_alarm_rate_legitimate} goodLow /></td>
                  <td><RateBar r={m?.unclear_rate_non_ambiguous} goodLow /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="table-wrap">
        <table className="table compact">
          <caption>Hinglish − English gap (percentage points)</caption>
          <thead>
            <tr>
              <th scope="col">System</th><th scope="col">Recall</th><th scope="col">Dangerous misses</th>
              <th scope="col">False alarms</th><th scope="col">Unclear</th>
            </tr>
          </thead>
          <tbody>
            {systems.map(([name, s]) => {
              const g = s.metrics.language_gap_hinglish_minus_english;
              const f = (k: string) => (g[k] === null || g[k] === undefined ? "n/a" : `${(g[k]! * 100).toFixed(1)}`);
              return (
                <tr key={name}>
                  <th scope="row">{name}</th>
                  <td>{f("scam_recall")}</td><td>{f("dangerous_miss_rate")}</td>
                  <td>{f("false_alarm_rate_legitimate")}</td><td>{f("unclear_rate_non_ambiguous")}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {(() => {
          const n = Math.min(...["english", "hinglish"].map((l) => sel.metrics.by_language[l]?.scam_recall.n ?? 0));
          return n > 0 && n < 50 ? (
            <p className="hint">
              Only {n} scams per language in this split: one item moves a rate by about {Math.round(100 / n)} points.
              Gaps this size are not evidence of a real difference.
            </p>
          ) : null;
        })()}
      </div>

      <section className="stack">
        <div className="row-between">
          <h2 className="h2">Per-category detail</h2>
          <label className="inline">
            System{" "}
            <select className="input input-inline" value={system} onChange={(e) => setSystem(e.target.value)}>
              {systems.map(([n]) => <option key={n}>{n}</option>)}
            </select>
          </label>
        </div>
        {sel.ranking_auc && (
          <p className="note">
            {system}: threshold-free ROC-AUC {sel.ranking_auc.auc} ({sel.ranking_auc.n_pos} scam vs{" "}
            {sel.ranking_auc.n_neg} other). Verdict thresholds were fixed before evaluation, so informative scores can
            still map to UNCLEAR.
          </p>
        )}
        <div className="two-col">
          <div className="table-wrap">
            <table className="table compact">
              <caption>False alarms by legitimate category</caption>
              <thead><tr><th scope="col">Category</th><th scope="col">LIKELY_SCAM rate</th></tr></thead>
              <tbody>
                {categories.map((c) => (
                  <tr key={c}><th scope="row">{c}</th><td><RateBar r={sel.metrics.false_alarm_by_legit_category[c]} goodLow /></td></tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="table-wrap">
            <table className="table compact">
              <caption>Scam recall by category</caption>
              <thead><tr><th scope="col">Category</th><th scope="col">LIKELY_SCAM rate</th></tr></thead>
              <tbody>
                {scamCats.map((c) => (
                  <tr key={c}><th scope="row">{c}</th><td><RateBar r={sel.metrics.scam_recall_by_category[c]} /></td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="table-wrap">
          <table className="table compact confusion">
            <caption>Confusion matrix — {system}, {scope === "overall" ? "all languages" : scope}</caption>
            <thead>
              <tr><th scope="col">Gold label</th>{VERDICTS.map((v) => <th scope="col" key={v}>{v}</th>)}</tr>
            </thead>
            <tbody>
              {Object.entries(conf ?? {}).map(([lab, row]) => (
                <tr key={lab}>
                  <th scope="row">{lab}</th>
                  {VERDICTS.map((v) => {
                    const bad = (lab === "scam" && v === "NO_STRONG_SIGNALS") ||
                      ((lab === "legitimate" || lab === "promotional") && v === "LIKELY_SCAM");
                    return <td key={v} className={bad && row[v] ? "cell-bad" : undefined}>{row[v]}{bad && row[v] ? " ⚠" : ""}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <details className="details">
        <summary>Run configuration</summary>
        <dl className="kv">
          <dt>Seed</dt><dd>{data.meta.seed}</dd>
          <dt>Split counts</dt><dd>{JSON.stringify(data.meta.manifest.counts)}</dd>
          <dt>Dataset sha256</dt><dd className="mono">{data.meta.dataset.sha256.slice(0, 16)}…</dd>
          <dt>Manifest sha256</dt><dd className="mono">{data.meta.manifest.sha256.slice(0, 16)}…</dd>
          <dt>Model</dt><dd>{data.meta.model.model_id ?? data.meta.model.note}</dd>
          {Object.entries(data.meta.versions).map(([k, v]) => (
            <Fragment key={k}><dt>{k}</dt><dd className="mono">{v}</dd></Fragment>
          ))}
        </dl>
        <p className="hint">Unclear rate for B4 on legitimate items: {pct(sel.metrics.overall.unclear_rate_by_label.legitimate?.rate)} — rule-only mode abstains rather than reassure.</p>
      </details>
    </div>
  );
}
