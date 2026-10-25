# Project summary

**ScamCheck Research Workbench** — an evidence-first English/Hinglish scam checker with a reproducible benchmark lab
and a seeded adversarial robustness lab. Python (FastAPI, pydantic, scikit-learn, Hypothesis), Next.js/TypeScript,
uv, GitHub Actions.

## What was built

- One deterministic analysis engine shared by the web API and the offline benchmark: Unicode normalisation with
  hidden-character and lookalike detection, a versioned negation-aware English/Hinglish rule pack, static URL
  structure analysis that never fetches, an optional provider-agnostic LLM adapter (opt-in, redacted input,
  quote-grounded evidence), and a pure verdict combiner whose invariants are property-tested.
- Three verdicts only (`LIKELY_SCAM`, `UNCLEAR`, `NO_STRONG_SIGNALS`), no "safe" label and no uncalibrated
  confidence. Rule-only mode abstains instead of reassuring.
- Benchmark harness with five baselines (controls, rules, char-n-gram logistic regression, zero-shot LLM, full engine),
  per-category and per-language metrics, Wilson and campaign-bootstrap intervals, and byte-identical reports.
- Mutation lab with 14 seeded transforms, meaning-preserving vs. needs-human-review separation, full lineage and exact
  hash-verified replay.
- Privacy controls verified by tests: no message text in logs, responses or disk; validation errors don't echo input.
- 398 automated tests (252 pre-existing pipeline tests plus 146 new), lint, schema check and frontend build in CI.

## What the evidence does and does not show

All results come from a 114-item synthetic set written by the same person who wrote the rules. They show that the
measurement and robustness pipeline works. They do not show real-world accuracy. No real messages have been
collected; the consent form awaits legal review.

## Resume bullet (accurate to current evidence)

> Built ScamCheck Research Workbench, an evidence-first English/Hinglish scam-analysis engine (FastAPI, Next.js) with
> a reproducible benchmark lab (five baselines, Wilson and campaign-bootstrap intervals) and a seeded mutation lab
> (14 transforms, hash-verified replay); 398 tests, including Hypothesis property tests that caught a verdict-logic
> bug. Evaluated so far only on synthetic fixtures; real-data evaluation is pending consent review.
