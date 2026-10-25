import type { Rate, Verdict } from "@/lib/types";
import { pct } from "@/lib/api";

const VERDICT_LABEL: Record<Verdict, string> = {
  LIKELY_SCAM: "Likely scam",
  UNCLEAR: "Unclear",
  NO_STRONG_SIGNALS: "No strong signals",
};
const VERDICT_ICON: Record<Verdict, string> = { LIKELY_SCAM: "▲", UNCLEAR: "◐", NO_STRONG_SIGNALS: "○" };

export function VerdictChip({ v }: { v: Verdict | null | undefined }) {
  if (!v) return <span className="chip">—</span>;
  return (
    <span className={`chip chip-${v}`}>
      <span aria-hidden="true">{VERDICT_ICON[v]}</span> {VERDICT_LABEL[v]}
    </span>
  );
}

/** A rate with its Wilson interval drawn as a bar; the numbers are always printed, colour is never the only cue. */
export function RateBar({ r, goodLow = false }: { r: Rate | undefined; goodLow?: boolean }) {
  if (!r || r.rate === null) return <span className="muted">n/a (n=0)</span>;
  const lo = (r.lo ?? 0) * 100;
  const hi = (r.hi ?? 0) * 100;
  return (
    <span className="rate">
      <span className="rate-num">{pct(r.rate)}</span>
      <span className="rate-track" aria-hidden="true">
        <span className={`rate-ci ${goodLow ? "low-good" : "high-good"}`} style={{ left: `${lo}%`, width: `${Math.max(hi - lo, 1)}%` }} />
        <span className="rate-point" style={{ left: `${r.rate * 100}%` }} />
      </span>
      <span className="rate-meta">
        [{pct(r.lo, 0)}–{pct(r.hi, 0)}] · {r.k}/{r.n}
      </span>
    </span>
  );
}

export function SyntheticBanner({ text }: { text: string }) {
  return (
    <div className="banner" role="note">
      <strong>Synthetic data.</strong> {text}
    </div>
  );
}

export function Loading({ label }: { label: string }) {
  return (
    <div className="loading" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" /> {label}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="error" role="alert">
      <p>{message}</p>
      <p className="muted">
        Start the API from the repository root with <code>uvicorn scamcheck.api:app --port 8000</code>.
      </p>
      {onRetry && (
        <button type="button" className="btn btn-quiet" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

/** Show invisible characters so a reader can see what a zero-width mutation did. */
export function Visible({ text }: { text: string }) {
  const parts = text.split(/([​-‏⁠-⁤﻿­])/);
  return (
    <>
      {parts.map((p, i) =>
        /^[​-‏⁠-⁤﻿­]$/.test(p) ? (
          <span key={i} className="invisible-mark" title={`U+${p.codePointAt(0)!.toString(16).toUpperCase().padStart(4, "0")}`}>
            ⟨U+{p.codePointAt(0)!.toString(16).toUpperCase().padStart(4, "0")}⟩
          </span>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </>
  );
}
