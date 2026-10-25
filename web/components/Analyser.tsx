"use client";

import { useEffect, useId, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Analysis, Example, Health, Language } from "@/lib/types";
import { ErrorBox, Loading, VerdictChip } from "@/components/ui";

const MAX = 4000;

/** Wrap each evidence quote found in the user's text in <mark>; quotes come from the normalised text, so a quote
 *  that no longer matches the original (e.g. after removing hidden characters) is simply listed, not highlighted. */
function highlight(text: string, quotes: string[]) {
  const ranges: [number, number][] = [];
  const lower = text.toLowerCase();
  for (const q of quotes) {
    const i = q.length > 2 ? lower.indexOf(q.toLowerCase()) : -1;
    if (i >= 0) ranges.push([i, i + q.length]);
  }
  ranges.sort((a, b) => a[0] - b[0]);
  const out: React.ReactNode[] = [];
  let last = 0;
  ranges.forEach(([s, e], k) => {
    if (s < last) return;
    out.push(text.slice(last, s), <mark key={k}>{text.slice(s, e)}</mark>);
    last = e;
  });
  out.push(text.slice(last));
  return out;
}

export default function Analyser() {
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [language, setLanguage] = useState<Language>("english");
  const [optIn, setOptIn] = useState(false);
  const [examples, setExamples] = useState<Example[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [result, setResult] = useState<Analysis | null>(null);
  const [submitted, setSubmitted] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const resultRef = useRef<HTMLDivElement>(null);
  const ids = { text: useId(), url: useId(), ex: useId(), opt: useId() };

  useEffect(() => {
    api<Example[]>("/api/examples").then(setExamples).catch(() => setExamples([]));
    api<Health>("/api/health").then(setHealth).catch(() => setHealth(null));
  }, []);

  async function submit(e?: React.FormEvent) {
    e?.preventDefault();
    if (!text.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const body = { text, url: url.trim() || null, language, llm_opt_in: optIn && !!health?.llm_configured };
      const res = await api<Analysis>("/api/analyse", { method: "POST", body: JSON.stringify(body) });
      setResult(res);
      setSubmitted(text);
      requestAnimationFrame(() => resultRef.current?.focus());
    } catch (err) {
      setResult(null);
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  function loadExample(id: string) {
    const ex = examples.find((x) => x.id === id);
    if (!ex) return;
    setText(ex.text);
    setLanguage(ex.language);
    setUrl("");
    setResult(null);
    setError(null);
  }

  return (
    <div className="analyse-grid">
      <form className="panel" onSubmit={submit} aria-describedby="privacy-note">
        <h1 className="h1">Analyse a message</h1>
        <p className="lede">
          Paste an SMS, WhatsApp or email text. The engine reports the evidence it found — and what it could not check.
        </p>

        <label htmlFor={ids.ex} className="label">
          Load a synthetic example
        </label>
        <select id={ids.ex} className="input" defaultValue="" onChange={(e) => loadExample(e.target.value)}>
          <option value="" disabled>
            {examples.length ? "Choose an example…" : "Examples unavailable (API offline)"}
          </option>
          <optgroup label="Synthetic examples — not real messages">
            {examples.map((x) => (
              <option key={x.id} value={x.id}>
                {x.title} ({x.language})
              </option>
            ))}
          </optgroup>
        </select>

        <label htmlFor={ids.text} className="label">
          Message text
        </label>
        <textarea
          id={ids.text}
          className="input textarea"
          value={text}
          maxLength={MAX}
          rows={7}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submit();
          }}
          placeholder="e.g. Aapka account aaj block ho jayega, KYC update karein…"
          aria-describedby={`${ids.text}-count`}
          required
        />
        <div id={`${ids.text}-count`} className="hint">
          {text.length}/{MAX} characters · Ctrl+Enter to analyse
        </div>

        <label htmlFor={ids.url} className="label">
          Link to check <span className="muted">(optional, never opened)</span>
        </label>
        <input
          id={ids.url}
          className="input mono"
          value={url}
          maxLength={2000}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="hxxps://example[.]com/login"
          spellCheck={false}
        />

        <fieldset className="fieldset">
          <legend className="label">Explanation language</legend>
          <div className="segmented">
            {(["english", "hinglish"] as Language[]).map((l) => (
              <label key={l} className={language === l ? "seg seg-on" : "seg"}>
                <input type="radio" name="language" value={l} checked={language === l} onChange={() => setLanguage(l)} />
                {l === "english" ? "English" : "Hinglish"}
              </label>
            ))}
          </div>
        </fieldset>

        <div className="optin">
          <input
            id={ids.opt}
            type="checkbox"
            checked={optIn}
            disabled={!health?.llm_configured}
            onChange={(e) => setOptIn(e.target.checked)}
          />
          <label htmlFor={ids.opt}>
            {health?.llm_configured ? (
              <>
                Also ask the language model <code>{health.llm_model_id}</code>. Identifiers are replaced with
                placeholders first, but redaction is imperfect: names and addresses may still be sent.
              </>
            ) : (
              <>Language model analysis is off (no model configured). The engine runs in rule-only mode.</>
            )}
          </label>
        </div>

        <button className="btn" type="submit" disabled={!text.trim() || loading}>
          {loading ? "Analysing…" : "Analyse"}
        </button>
        <p id="privacy-note" className="hint">
          Your text is analysed in memory and not stored or logged. Links are inspected as text only — never fetched.
        </p>
      </form>

      <section className="panel result" aria-labelledby="result-heading" aria-busy={loading}>
        <h2 id="result-heading" className="h2">
          Result
        </h2>
        {loading && <Loading label="Checking rules and link structure…" />}
        {!loading && error && <ErrorBox message={error} onRetry={() => submit()} />}
        {!loading && !error && !result && (
          <div className="empty">
            <p>No analysis yet.</p>
            <p className="muted">
              Verdicts are one of <VerdictChip v="LIKELY_SCAM" />, <VerdictChip v="UNCLEAR" /> or{" "}
              <VerdictChip v="NO_STRONG_SIGNALS" />. There is no “safe” verdict: an absence of signals is not proof.
            </p>
          </div>
        )}
        {!loading && !error && result && (
          <div ref={resultRef} tabIndex={-1} className="result-body" aria-live="polite">
            <div className={`verdict verdict-${result.verdict}`}>
              <VerdictChip v={result.verdict} />
              <p className="verdict-headline">{result.headline}</p>
            </div>

            <h3 className="h3">What to do</h3>
            <ul className="guidance">
              {result.guidance.map((g) => (
                <li key={g}>{g}</li>
              ))}
            </ul>

            <h3 className="h3">Evidence found ({result.signals.length})</h3>
            {result.signals.length === 0 ? (
              <p className="muted">No rule or link signal fired.</p>
            ) : (
              <>
                <blockquote className="message">{highlight(submitted, result.signals.map((s) => s.quote))}</blockquote>
                <ol className="signals">
                  {result.signals.map((s) => (
                    <li key={s.id} className={`signal sev-${s.severity}`}>
                      <div className="signal-head">
                        <span className={`sev sev-${s.severity}`}>{s.severity}</span>
                        <strong>{s.title}</strong>
                        <code className="signal-id">{s.id}</code>
                      </div>
                      <p>{s.detail}</p>
                      {s.quote && <q className="quote mono">{s.quote}</q>}
                    </li>
                  ))}
                </ol>
              </>
            )}

            {result.urls.length > 0 && (
              <>
                <h3 className="h3">Links (structure only)</h3>
                <ul className="urls">
                  {result.urls.map((u) => (
                    <li key={u.display}>
                      <code className="mono">{u.display}</code>
                      <span className="muted"> · domain {u.registered_domain ?? "unreadable"}</span>
                      <div className="hint">
                        Signals: {u.signal_ids.length ? u.signal_ids.join(", ") : "none"} · Not checked:{" "}
                        {u.not_checked.join(", ")}
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            )}

            <details className="details">
              <summary>Not checked, privacy and versions</summary>
              <p>
                <strong>Not checked:</strong> {result.not_checked.join(", ")}.
              </p>
              {result.pii_detected.length > 0 && (
                <p>
                  <strong>Personal identifiers seen in your input:</strong> {result.pii_detected.join(", ")}. They were
                  not stored.
                </p>
              )}
              <p>
                <strong>Model:</strong> {result.model.status.replaceAll("_", " ")}
                {result.model.model_id ? ` (${result.model.model_id})` : ""}
                {result.model.dropped_evidence > 0 &&
                  ` · ${result.model.dropped_evidence} model quote(s) discarded because they were not in the message`}
              </p>
              <p>
                <strong>Reason codes:</strong> <code>{result.reasons.join(", ")}</code>
              </p>
              <p className="mono hint">
                {Object.entries(result.versions)
                  .map(([k, v]) => `${k}=${v}`)
                  .join(" · ")}
              </p>
            </details>
          </div>
        )}
      </section>
    </div>
  );
}
