"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { RobustnessReport } from "@/lib/types";
import { ErrorBox, Loading, RateBar, SyntheticBanner, VerdictChip, Visible } from "@/components/ui";

export default function RobustnessLab() {
  const [data, setData] = useState<RobustnessReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [system, setSystem] = useState("B4-engine");
  const [transform, setTransform] = useState("zero_width");

  // State is only set in promise callbacks, never synchronously inside the effect.
  const load = useCallback(() => {
    api<RobustnessReport>("/api/reports/robustness")
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
  if (!data) return <Loading label="Loading robustness report…" />;

  const systems = Object.entries(data.systems);
  const sel = data.systems[system] ?? systems[0][1];
  const examples = data.examples.filter((e) => e.transform === transform);
  const tmeta = data.meta.transforms.find((t) => t.name === transform);
  const c = data.meta.counts;

  return (
    <div className="stack">
      <header>
        <h1 className="h1">Robustness Lab</h1>
        <p className="lede">
          Seeded mutations of {data.meta.n_parents} dev/test messages (generator <code>{data.meta.generator_version}</code>,
          seeds {data.meta.seeds.join(", ")}). Each variant records its parent, seed, transform and output hash, and
          can be replayed exactly.
        </p>
      </header>
      <SyntheticBanner text={data.meta.data_label} />

      <dl className="tiles">
        <div><dt>Generated</dt><dd>{c.generated}</dd></div>
        <div><dt>Excluded (no change)</dt><dd>{c.excluded_no_change}</dd></div>
        <div><dt>Unvalidated family (no label)</dt><dd>{c.unvalidated_family ?? 0}</dd></div>
        <div><dt>Label inherited</dt><dd>{c.label_inherited}</dd></div>
        <div><dt>Needs human review</dt><dd>{c.needs_human_review}</dd></div>
        <div><dt>Human reviewed</dt><dd>{c.human_reviewed}</dd></div>
      </dl>

      {systems.some(([, s]) => s.consistency_provisional) && (
        <p className="note" role="note">
          <strong>Provisional.</strong> No mutation family has been validated by human review yet
          (guideline <code>{data.meta.review_guideline}</code>: at least {data.meta.min_family_reviews} reviewed
          variants, all judged meaning-preserving). Consistency below is label-free but may include variants whose
          meaning changed; label-based rows stay n/a until reviews exist.
        </p>
      )}

      <div className="table-wrap">
        <table className="table">
          <caption>Meaning-preserving transforms</caption>
          <thead>
            <tr>
              <th scope="col">System</th>
              <th scope="col">Verdict consistency ↑</th>
              <th scope="col">Scam → NO_STRONG_SIGNALS ↓ (confirmed labels)</th>
              <th scope="col">Parent-scam variants → NO_STRONG_SIGNALS ↓ (provisional)</th>
              <th scope="col">Parent-scam detections lost ↓ (provisional)</th>
              <th scope="col">Seed spread</th>
            </tr>
          </thead>
          <tbody>
            {systems.map(([name, s]) => (
              <tr key={name}>
                <th scope="row">
                  <div>{name}</div>
                  {s.constant_verdict && <div className="hint warn">Constant verdict — trivially consistent</div>}
                </th>
                <td><RateBar r={s.consistency_preserving} /></td>
                <td><RateBar r={s.scam_flip_to_no_strong_signals} goodLow /></td>
                <td><RateBar r={s.parent_scam_moved_to_no_strong_signals} goodLow /></td>
                <td><RateBar r={s.parent_scam_detection_lost} goodLow /></td>
                <td>{s.seed_variation ? `${(s.seed_variation.min * 100).toFixed(1)}–${(s.seed_variation.max * 100).toFixed(1)}%` : "n/a"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="table-wrap">
        <table className="table compact">
          <caption>Mutation families: human review status</caption>
          <thead>
            <tr>
              <th scope="col">Family</th><th scope="col">Preserving by design</th><th scope="col">Status</th>
              <th scope="col">Reviewed (yes / no / unsure)</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(data.meta.families ?? {}).map(([name, f]) => (
              <tr key={name}>
                <th scope="row">{name}</th>
                <td>{f.preserving_by_design ? "yes" : "no"}</td>
                <td>{f.status.replaceAll("_", " ")}</td>
                <td>{f.reviewed} ({f.yes} / {f.no} / {f.unsure})</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <section className="stack">
        <div className="row-between">
          <h2 className="h2">By transform</h2>
          <label className="inline">
            System{" "}
            <select className="input input-inline" value={system} onChange={(e) => setSystem(e.target.value)}>
              {systems.map(([n]) => <option key={n}>{n}</option>)}
            </select>
          </label>
        </div>
        <div className="table-wrap">
          <table className="table compact">
            <caption>Consistency by transform — {system}</caption>
            <thead><tr><th scope="col">Transform</th><th scope="col">Consistency</th></tr></thead>
            <tbody>
              {Object.entries(sel.consistency_by_transform).map(([t, r]) => (
                <tr key={t}><th scope="row">{t}</th><td><RateBar r={r} /></td></tr>
              ))}
              {Object.entries(sel.consistency_by_language).map(([l, r]) => (
                <tr key={l} className="row-sub"><th scope="row">all transforms · {l}</th><td><RateBar r={r} /></td></tr>
              ))}
            </tbody>
          </table>
        </div>
        {Object.keys(sel.needs_review_verdicts).length > 0 && (
          <p className="note">
            Meaning-changing transforms are reported as verdict counts only until a human confirms their labels:{" "}
            {Object.entries(sel.needs_review_verdicts)
              .map(([t, v]) => `${t} (${Object.entries(v).map(([k, n]) => `${k} ${n}`).join(", ")})`)
              .join("; ")}.
          </p>
        )}
      </section>

      <section className="stack" aria-labelledby="side-by-side">
        <div className="row-between">
          <h2 id="side-by-side" className="h2">Original vs. variant (B4 engine)</h2>
          <label className="inline">
            Transform{" "}
            <select className="input input-inline" value={transform} onChange={(e) => setTransform(e.target.value)}>
              {data.meta.transforms.map((t) => (
                <option key={t.name} value={t.name}>{t.name}{t.preserving ? "" : " (needs review)"}</option>
              ))}
            </select>
          </label>
        </div>
        {tmeta && (
          <p className="hint">
            {tmeta.preserving
              ? "Meaning-preserving: the parent's label is inherited and verdict changes count as inconsistencies."
              : "Meaning-changing or ambiguous: no label is inherited until a human reviews the variant."}
          </p>
        )}
        {examples.length === 0 ? (
          <p className="muted">No variants for this transform.</p>
        ) : (
          examples.map((e) => (
            <article key={e.variant_id} className="pair">
              <div className="pair-col">
                <div className="pair-head"><span>Original · {e.parent_id}</span><VerdictChip v={e.parent_verdict} /></div>
                <p className="pair-text"><Visible text={e.parent_text} /></p>
              </div>
              <div className="pair-col">
                <div className="pair-head">
                  <span>Variant · seed {e.seed}</span>
                  <VerdictChip v={e.variant_verdict} />
                </div>
                <p className="pair-text"><Visible text={e.variant_text} /></p>
              </div>
              <footer className="pair-foot hint mono">
                {e.variant_id} · {e.language} · {e.status.replaceAll("_", " ")}
                {e.parent_verdict !== e.variant_verdict && <strong className="warn"> · verdict changed</strong>}
              </footer>
            </article>
          ))
        )}
      </section>
    </div>
  );
}
