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
- 423 automated tests (252 original pipeline tests, 146 from the workbench build, 25 from the evaluation-rigour work), lint, schema check and frontend build in CI.

## What the evidence does and does not show

- **Data:** all evidence is synthetic.
  - 114 messages were written by the rule author.
  - One pre-registered, run-once check used 38 Hinglish messages written by another author
    (`bolewara/hinglish-scam-text-dataset`). Its row selection deviated from the plan, and the deviation is
    recorded.
  - No real messages have been collected; the consent form awaits legal review.
- **Findings, as counts at small n:**
  - The rule engine's scam recall fell from 9/12 on its author's messages to 4/16 on the other author's. The drop is
    large, but the intervals overlap slightly, so by the pre-registered criterion it is not yet conclusive.
  - A small local LLM (qwen2.5:3b), run as B3 and inside the engine, caught 12/12 and 16/16 scams. It also flagged
    4/12 legitimate OTP, payment and bank messages, and the engine inherited those false alarms.
  - Reading rule silence as reassurance missed 10/16 external scams dangerously.
  - None of this is real-world accuracy.

## Resume bullet (accurate to current evidence)

> Built ScamCheck, an evidence-first English/Hinglish scam-analysis engine (FastAPI, Next.js) with a reproducible
> benchmark lab (five baselines including a local LLM, paired campaign-bootstrap comparisons) and a seeded mutation
> lab. In a pre-registered check on another author's Hinglish messages, rule-based recall fell from 9/12 to 4/16. A
> 3B local LLM caught every scam in both synthetic sets but falsely flagged a third of legitimate OTP and bank
> messages; that trade-off now drives the next design. 450+ tests; real-data evaluation is pending consent review.
