# ScamCheck Research Workbench — architecture

Research question: **can a transparent, evidence-first checker for English and Hinglish messages be measured
honestly — false alarms per legitimate category, dangerous misses, abstention, language gap and robustness to
obfuscation — and how does it compare with simple baselines?**

Everything in this document is a design decision, not a result. Numbers below are subjective design scores.

## 1. Bounded design search

Five candidate directions, scored 1–5 by the maintainer on each criterion. These are judgement calls made before
building, not measurements; there is no market validation, user count or accuracy figure behind them.

| Direction | Research fit | Differentiation | Technical depth | Measurable outcomes | Solo buildability | Resume value | Privacy & safety | Total /35 |
|---|---|---|---|---|---|---|---|---|
| 1. Generic LLM-only chatbot | 2 | 1 | 2 | 2 | 5 | 2 | 1 | 15 |
| 2. Fine-tuned multilingual classifier | 3 | 2 | 4 | 4 | 2 | 4 | 4 | 23 |
| 3. Scam campaign intelligence graph | 3 | 4 | 4 | 2 | 2 | 4 | 2 | 21 |
| 4. English/Hinglish benchmark + scorecard | 5 | 4 | 4 | 5 | 4 | 4 | 4 | 30 |
| 5. Evidence-first checker, transparent signals | 5 | 4 | 3 | 4 | 4 | 4 | 5 | 29 |

Why the low scores: (1) sends raw messages to a provider and cannot explain or bound its errors; (2) there is no
legally usable labelled data yet (see `docs/DATA_SOURCES.md`), so fine-tuning would only memorise synthetic
templates; (3) needs volume of real, linked scammer identifiers, which conflicts with the redaction policy.

**Selected: 4 + 5.** The benchmark measures the checker, and the checker is the thing the benchmark measures.

### Iterations (three, then stopped)

| # | Addition tested | Kept? | Reason |
|---|---|---|---|
| 1 | Combine benchmark with the evidence-first engine through one shared `analyse()` path | Kept | Rules out a "demo-only" scoring path by construction: the API and the benchmark import the same function |
| 2 | Seeded mutation lab (meaning-preserving vs. needs-review transforms, lineage, replay) | Kept | Produces measurable robustness numbers without any real data, and reuses the existing lineage/leakage machinery |
| 2 | Structured evidence attribution: the LLM must quote exact substrings; ungrounded claims are discarded | Kept | Few lines, directly testable, stops a model from inventing red flags |
| 3 | Multi-baseline evaluation B0–B4 with campaign-aware bootstrap | Kept | Already in PLAN §6.3; without baselines a score means nothing |
| 3 | Campaign graph UI, database, transformer fine-tune, live URL reputation, Presidio by default, calibration plots | Rejected | Add complexity with no evidence of value at the current data volume; reputation results would have to be invented; no probabilities are exposed, so calibration plots have nothing to show |

## 2. Data flow

```
                ┌──────────────── one engine: src/scamcheck/engine ────────────────┐
 text, url? ──▶ │ parse ─▶ rules ─▶ url_static ─▶ [redact ─▶ llm]? ─▶ combine ─▶ explain │ ──▶ Analysis
                └───────────────────────────────────────────────────────────────────┘
                     ▲                                           ▲
       FastAPI /api/analyse (online)           scamcheck benchmark / robustness (offline)
```

| Module | Responsibility |
|---|---|
| `engine/parse.py` | NFKC, hidden-character and confusable detection (recorded as signals), defanged-URL recovery, script detection, input bounds |
| `engine/redact.py` | Regex redaction *assistance* before any external call; residual check with the existing `data/pii.py` detector. Not anonymisation |
| `engine/rules.py` | Versioned deterministic rule pack (English + Hinglish), negation-aware so "do not share your OTP" does not fire |
| `engine/urls.py` | Static URL structure only: IP hosts, punycode/mixed script, userinfo tricks, brand lookalikes, shorteners, free hosting, APK links. Never fetches |
| `engine/llm.py` | Provider-agnostic adapter (any OpenAI-compatible endpoint, including local Ollama). Off unless configured **and** the user opts in |
| `engine/combiner.py` | Pure verdict function; invariants are property-tested |
| `engine/explain.py` | English/Hinglish explanations generated only from signals that fired, plus what was *not* checked |
| `eval/` | Baselines B0–B4, metrics with Wilson and campaign-bootstrap intervals, report writer, mutation lab |
| `api.py` | FastAPI app; logs method, path, status and latency only |
| `web/` | Next.js App Router frontend (Analyse, Benchmark Lab, Robustness Lab, Method) |

## 3. Verdict policy (`engine/combiner.py`)

```
any HIGH rule/URL signal                                          → LIKELY_SCAM
model ok, label "scam", ≥1 quote found verbatim in the input      → LIKELY_SCAM
model ok, label "not_scam", no MEDIUM+ signal, no obfuscation or
  injection signal, no URL left unverified                        → NO_STRONG_SIGNALS
otherwise (incl. no model, model error/timeout/invalid output)    → UNCLEAR
```

Consequences, each covered by a test:

- An LLM cannot cancel a HIGH signal and cannot by itself produce `NO_STRONG_SIGNALS`.
- Rule-only mode (the default, no paid API) answers `LIKELY_SCAM` or `UNCLEAR` only: it abstains rather than
  reassure, because silence from a rule pack is not evidence.
- A message with a link can't get `NO_STRONG_SIGNALS` while no reputation/domain-age adapter exists: static
  structure is checked, but the URL's destination is not.
- No probability or "confidence %" is returned anywhere. The model returns a categorical label plus quotes.

## 4. Evaluation design

- B0 always-UNCLEAR / always-LIKELY_SCAM; B1 rules only, silence → `NO_STRONG_SIGNALS` (shows what trusting rule
  silence costs); B2 char 2–5-gram TF-IDF + logistic regression fit on `train` only, fixed thresholds recorded in the
  config; B3 zero-shot LLM (only when configured); B4 full engine.
- Metrics per class, language and category; Wilson 95% intervals for every rate; campaign-group bootstrap when the
  evaluated split has at least 20 campaigns, otherwise reported as "too few campaigns".
- Each run writes `benchmark.json` + `benchmark.md` with dataset hash, manifest hash, seeds, rule-pack, engine,
  prompt and model ids.
- The bundled benchmark data is **synthetic, written by the same maintainer who wrote the rules**. Its scores show the
  pipeline works; they are optimistic by construction and are not real-world detection performance.

## 5. Mutation lab

`eval/mutate.py` holds named, versioned transforms. Each variant is generated from
`random.Random(f"{seed}:{parent_id}:{transform}")`, so any single variant can be rebuilt from its record.
Meaning-preserving transforms inherit the parent label and measure verdict consistency; meaning-changing ones
(prompt-injection suffix, link removal, code-switch rewrites) are marked `needs_human_review` and excluded from label-based
metrics until a reviewer confirms them. Randomness exists only here, never in `analyse()`.

## 6. Dependencies and why each exists

Versions were checked against the package indexes on 2026-10-25 and are pinned in `uv.lock`
(`requirements-lock.txt` is exported from it for pip users).

| Dependency | Where | Why |
|---|---|---|
| pydantic | core | Existing single source of truth for the dataset schema; also the API/engine models |
| fastapi, uvicorn | `api` extra | Typed HTTP API with request validation; uvicorn serves it |
| scikit-learn | `eval` extra | Baseline B2 only (TF-IDF + logistic regression). Imported lazily so the API does not need it |
| hypothesis | dev | Property-based tests for combiner invariants and seeded mutation replay |
| httpx2 | dev | Required by Starlette 1.x's TestClient (it deprecates `httpx`) |
| ruff (exact pin) | dev | Lint gate with an explicit rule selection, so upgrades cannot silently change it |
| uv | tooling | Reproducible lock file; plain pip remains documented |
| Next.js, React, TypeScript, ESLint | `web/` | Requested frontend stack; versions from `create-next-app@16.4.3`; system fonts only (no third-party font requests) |
| GitHub Actions | CI | Lint, schema check, tests, byte-identical report reproduction, frontend lint/type-check/build |
| Promptfoo (not installed; `npx promptfoo@0.125.0`) | `promptfoo/` | Optional red-team probes against the running API. Verified 6/6 passing in rule-only mode; its value is mainly for the LLM path |

Considered and not added:

- **Microsoft Presidio.** Its useful recognisers need a spaCy model download, its NER is English-only, and the
  identifier shapes that matter here (Indian mobile numbers, UPI ids, Aadhaar-like and PAN numbers) are already
  covered by `data/pii.py`, which has tests and counter-examples. Without a labelled redaction set there is no way to
  show that Presidio would catch more in Hinglish text. Revisit once such a set exists.
- **A database.** Reports are small JSON/JSONL files, regenerated byte-identically; nothing is stored from users.
- **tldextract / a PSL snapshot.** A short multi-label suffix list covers the Indian suffixes in use; marked as a
  shortcut in `engine/urls.py`.

## 7. What is deliberately absent

Voice, deepfakes, screenshots/OCR, WhatsApp automation, multi-agent orchestration, URL fetching, reputation or
domain-age lookups, message storage, user accounts.
