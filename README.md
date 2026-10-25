# ScamCheck Research Workbench

An evidence-first scam checker for English and Hinglish messages, with a reproducible benchmark lab and a seeded
adversarial robustness lab. Thesis: **measured trust, not another chatbot**.

**Research question.** Can a transparent checker be measured honestly on English and Hinglish messages? That means
false alarms per legitimate category, dangerous misses, abstention, the language gap and robustness to obfuscation,
compared against simple baselines.

> **Status: no real-world results.** No real messages have been collected (the consent form still awaits legal
> review). Every number in this repository comes from **synthetic** data written by the same maintainer who wrote the
> rules. These numbers show the measurement pipeline works and expose concrete failure modes. They do not show
> detection accuracy.

| | |
|---|---|
| Analyse | Paste a message (and optionally a link); get `LIKELY_SCAM`, `UNCLEAR` or `NO_STRONG_SIGNALS`, the evidence behind it, what to do, and what was *not* checked |
| Benchmark Lab | Baselines B0–B4 on a frozen split, per category and language, Wilson and campaign-bootstrap intervals |
| Robustness Lab | 14 seeded transforms (zero-width, confusables, Hinglish spelling, Devanagari mixing, defanging, prompt injection…) with full lineage and exact replay |

Design and decisions: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (design search, data flow, verdict policy).
Original plan: [docs/PLAN.md](docs/PLAN.md). Audit: [docs/AUDIT.md](docs/AUDIT.md). Annotation:
[docs/ANNOTATION_GUIDELINES.md](docs/ANNOTATION_GUIDELINES.md), pilot procedure
[docs/PILOT_WORKFLOW.md](docs/PILOT_WORKFLOW.md), readiness [docs/PILOT_READINESS.md](docs/PILOT_READINESS.md).
Sources and licences: [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) and `data/source_register.csv`.
Project summary: [docs/PROJECT_SUMMARY.md](docs/PROJECT_SUMMARY.md).

## Architecture in one picture

```
                ┌──────────────── one engine: src/scamcheck/engine ────────────────┐
 text, url? ──▶ │ parse ─▶ rules ─▶ url_static ─▶ [redact ─▶ llm]? ─▶ combine ─▶ explain │ ──▶ Analysis
                └───────────────────────────────────────────────────────────────────┘
                     ▲                                           ▲
       FastAPI /api/analyse ◀── Next.js web/        scamcheck benchmark / robustness (offline)
```

The API and the benchmark call the same `scamcheck.engine.analyse()`; there is no demo-only scoring path.

Verdict rules (pure function, property-tested in `tests/test_engine_combiner.py`):

- any HIGH rule or URL signal → `LIKELY_SCAM`, and no model can overrule it;
- a model can raise a verdict to `LIKELY_SCAM` only by quoting text that is verbatim in the message;
- `NO_STRONG_SIGNALS` needs a working model that said `not_scam` **and** no MEDIUM/HIGH signal, no obfuscation or
  injection signal, and no link left unverified;
- no model configured, model timeout, or invalid model output → `UNCLEAR` unless a HIGH signal fires.

There is no `SAFE` verdict and no confidence percentage anywhere.

## Setup

Requires Python 3.11+ and, for the web app, Node.js 20+ (tested with 24). Run every command from the repository root.

**With uv (recommended, uses `uv.lock`):**

```bash
uv sync --locked --all-extras
```

Then prefix commands with `uv run` (e.g. `uv run pytest -q`), or activate `.venv` as below.

**With pip (still supported):**

```bash
python -m venv .venv
```

Activate it:

| Shell | Command |
|---|---|
| PowerShell | `.venv\Scripts\Activate.ps1` |
| cmd.exe | `.venv\Scripts\activate.bat` |
| Git Bash | `source .venv/Scripts/activate` |
| macOS/Linux | `source .venv/bin/activate` |

```bash
pip install -c requirements-lock.txt -e ".[dev]"
```

Extras: `api` (FastAPI, uvicorn), `eval` (scikit-learn for baseline B2), `dev` (both, plus pytest, Hypothesis,
httpx2 for FastAPI's test client, ruff). The core package needs only pydantic. Nothing is downloaded at runtime.
`requirements-lock.txt` is exported from `uv.lock`. Pinning matters because `scamcheck schema --check` compares
against pydantic's JSON Schema output.

**Windows: keep the checkout path short** (e.g. `C:\Projects\scamcheck`). With long-path support disabled (the
Windows default), creating a venv inside a deeply nested folder fails while installing pip, because pip's files
exceed the 260-character path limit.

### Run the app locally

```bash
uvicorn scamcheck.api:app --port 8000
```

In a second terminal:

```bash
cd web && npm ci && npm run dev
```

Open http://localhost:3000. The Next.js server proxies `/api/*` to `SCAMCHECK_API_URL` (default
`http://127.0.0.1:8000`), so the browser talks to one origin. The API docs are at http://localhost:8000/api/docs.
The app runs fully in **rule-only mode** without any paid API.

**Optional language model.** Any OpenAI-compatible chat endpoint works, including a local Ollama server. Set these
before starting the API:

```bash
export SCAMCHECK_LLM_BASE_URL=http://127.0.0.1:11434/v1 SCAMCHECK_LLM_MODEL=<model name>
```

`SCAMCHECK_LLM_API_KEY` and `SCAMCHECK_LLM_TIMEOUT` are optional. The model is used only when the user ticks the
opt-in for that request. Only redacted text is sent, and the call is skipped if the residual detector still sees an
identifier. Check your provider's retention terms first (PLAN.md §7).

### Command line

```bash
scamcheck analyse "Aapke account mein Rs 10,000 cashback aaya hai. Paisa lene ke liye UPI PIN daaliye." --language hinglish
```

## Run the tests

```bash
pytest -q
ruff check .
scamcheck schema --check
cd web && npm run lint && npx tsc --noEmit && npm run build
```

CI (`.github/workflows/ci.yml`) runs all of these and also checks that the committed benchmark and robustness
reports reproduce byte for byte.

The suite covers combiner invariants (Hypothesis), legitimate bank/OTP/delivery/payment messages that must not be
flagged, English/Hinglish/mixed-script input, disguised requests (zero-width, Cyrillic lookalikes, full-width, spaced
letters), prompt injection, URL parsing with a guard that fails on any network use, LLM timeouts and invalid output,
API bounds and malformed bodies, a privacy test that no message text reaches logs or disk, metrics against
hand-computed values, split leakage, and seeded mutation replay.

Hypothesis prints a `@reproduce_failure` blob for every failure. CI sets `HYPOTHESIS_PROFILE=ci` (derandomized), so a
failing example fails on every run. Locally, `.hypothesis/` replays the last failure first. Hypothesis has already
found one real combiner bug: an `ok` model result with no label could reach `NO_STRONG_SIGNALS`. It is fixed and
covered by the invariant test.

The original pipeline tests use only `tests/fixtures/synthetic_items.jsonl` and `tests/fixtures/invalid_items.jsonl`.
Every fixture message is **hand-written and synthetic** (`source_type: "synthetic"`, `source_name: "unit-test-fixture"`);
brands like "XYZ Bank" and the domains are invented. They exist to exercise the pipeline and must never be cited as
real-world evidence. Regenerate them with `python tests/fixtures/build_fixtures.py` (a test checks the committed files
match the builder).

## Benchmark Lab

```bash
D=benchmarks/synthetic
python $D/build.py                                   # regenerate the synthetic set (a test checks it matches)
scamcheck group $D/items.jsonl --out $D/items.grouped.jsonl --review $D/near_dup_pairs.jsonl
scamcheck split $D/items.grouped.jsonl --out $D/manifest.json --allow-synthetic-in-test
scamcheck benchmark $D/items.grouped.jsonl --manifest $D/manifest.json --out-dir reports/benchmark/synthetic
```

`benchmark` refuses to run if the leakage check fails or if asked to evaluate `train`. It writes `benchmark.json` and
`benchmark.md` with dataset and manifest SHA-256, seed, split counts, rule-pack/engine/prompt versions and model id.
The files contain no timestamps, so a re-run is byte-identical. `--with-llm` adds B3 and runs B4 with the model.

| ID | System |
|---|---|
| B0 | always `UNCLEAR` / always `LIKELY_SCAM` (controls that expose metric gaming) |
| B1 | rule pack only; rule silence → `NO_STRONG_SIGNALS` (what trusting a keyword list costs) |
| B2 | char 2–5-gram TF-IDF + logistic regression, trained on `train` only, thresholds 0.3/0.7 fixed in advance |
| B3 | zero-shot LLM with a fixed, hashed prompt (only when a model is configured) |
| B4 | the full engine (rule-only mode when no model is configured) |

Metrics: scam recall, dangerous-miss rate (scams → `NO_STRONG_SIGNALS`), false alarms per legitimate category and for
promotional messages, `UNCLEAR` rate per class, confusion matrices per language and category, Hinglish − English gaps,
Wilson 95% intervals with k/n for every rate, and a campaign-level bootstrap (2,000 resamples) when the split has at
least 20 campaigns. B2 also reports a threshold-free ROC-AUC.

### Example results — SYNTHETIC fixture, `test` split (28 items: 12 scam, 12 legitimate, 2 promotional, 2 ambiguous)

| System | Scam recall | Dangerous misses | False alarms (legit) | Unclear (non-ambiguous) |
|---|---|---|---|---|
| B0-unclear | 0/12 | 0/12 | 0/12 | 26/26 |
| B0-scam | 12/12 | 0/12 | 12/12 | 0/26 |
| B1-rules | 5/12 (42%, CI 19–68%) | 3/12 (25%, CI 9–53%) | 0/12 | 4/26 |
| B2-tfidf-lr | 0/12 | 0/12 | 0/12 | 26/26 (ROC-AUC 0.97) |
| B4-engine (rule-only) | 9/12 (75%, CI 47–91%) | 0/12 | 0/12 | 17/26 (65%) |

How to read this, honestly:

- The intervals are wide (12 scams). The data was written by the same person who wrote the rules. None of this is
  evidence of real-world performance.
- B4 has no dangerous misses **by construction**: without a model it never reassures. The cost is visible: it answers
  `UNCLEAR` for every legitimate message.
- B1 shows the alternative. Treating rule silence as reassurance produced 3 dangerous misses out of 12.
- B2 ranks well (AUC 0.97), but 64 training items never push its probabilities past the pre-set thresholds, so it
  abstains on everything. The thresholds were not retuned after seeing test results.

Full report: [reports/benchmark/synthetic/benchmark.md](reports/benchmark/synthetic/benchmark.md). Run log:
[reports/test_runs.md](reports/test_runs.md).

## Robustness Lab (seeded mutation testing)

```bash
scamcheck robustness $D/items.grouped.jsonl --manifest $D/manifest.json --out-dir reports/robustness/synthetic
scamcheck robustness $D/items.grouped.jsonl --manifest $D/manifest.json --out-dir /tmp/x \
    --replay reports/robustness/synthetic/variants.jsonl     # regenerate every variant and compare hashes
```

How it works (`src/scamcheck/eval/mutate.py`):

- Each variant comes from `random.Random(f"{seed}:{parent_id}:{transform}")`. Python hashes string seeds
  deterministically, so any single variant can be rebuilt from its record.
- Every record stores `variant_id`, `parent_id`, `seed`, `transform`, `generator_version`, `output_sha256` and a
  status. Default seeds are 11, 23 and 37 (`--seeds` to change).
- **Meaning-preserving** transforms (whitespace, punctuation, character spacing, zero-width, confusables, full-width,
  casing, typo, Hinglish spelling, Devanagari mixing, defang style) inherit the parent label, and verdict consistency
  is measured.
- **Meaning-changing or ambiguous** transforms (prompt-injection suffix, link removal, English→Hinglish code-switch)
  are `needs_human_review`. They appear only as verdict counts until a reviewer supplies labels with
  `--reviews decisions.jsonl` (`{"variant_id": "...", "label": "scam"}` per line).
- Outputs identical to the parent are excluded and counted. Parents come only from `dev`/`test`, never `train`, so
  B2 never sees a variant of its own training data. A test checks this lineage.
- Randomness exists only here. `analyse()` is deterministic.

### Example results — SYNTHETIC adversarial fixtures (46 parents × 3 seeds)

1,725 generated · 307 excluded (no change) · 1,199 label-inherited · 219 awaiting human review · 0 reviewed.

| System | Consistency (meaning-preserving) | Scam → `NO_STRONG_SIGNALS` | Scam detections lost | Seed spread |
|---|---|---|---|---|
| B1-rules | 96.8% (1160/1199) | 6.2% (34/544) | 11.0% (35/319) | 96.5–97.0% |
| B2-tfidf-lr | 100% — constant verdict, trivially consistent | 0% | n/a | — |
| B4-engine | 97.1% (1164/1199) | 0.0% (0/544) | 7.6% (35/463) | 96.8–97.5% |

The lab found real weaknesses:

- Newlines broke sentence-scoped rules: whitespace consistency was 87.7%. That is now fixed in `parse()` and is at
  100%.
- Still open: inserted punctuation (`...`, `!!`), adjacent-letter typos in keywords, Hinglish spelling variants
  (`apka`, `kro`, `bta do`) and Devanagari words in romanised text each cost 7–9 points of consistency.

Full report: [reports/robustness/synthetic/robustness.md](reports/robustness/synthetic/robustness.md).

## Privacy and URL safety

- No message is stored. The API logs only method, path, status and latency. Validation errors do not echo input.
  Responses are `Cache-Control: no-store`. A test posts a marker string and asserts it reaches neither the logs nor
  the disk.
- URLs are parsed as text. Nothing is resolved, fetched, redirected or executed. Domain age, CT logs and reputation
  are reported as **not checked**, never guessed. The brand-domain list is used only to avoid a lookalike flag on a
  brand's own domain; it never vouches for a link.
- There is no outbound lookup adapter, so there is no SSRF surface. The LLM endpoint comes from the operator's
  environment, never from a request, must be http(s), and does not follow redirects. Any future lookup adapter must
  resolve the host once, refuse private/loopback/link-local addresses, pin the resolved IP, and disable redirects.
- Redaction (`engine/redact.py`) is assistance, not anonymisation. It cannot find names or addresses. The dataset
  pipeline keeps its mandatory second-person redaction check.

## Consent and licensing status

- Code: Apache-2.0 ([LICENSE](LICENSE)).
- No source is approved and no real message has been collected. `APPROVED_CONSENT_VERSIONS` is empty, so donated
  items cannot reach a test split or a release until consent-v1's legal review is recorded
  (`docs/PILOT_READINESS.md`).
- The synthetic benchmark (`benchmarks/synthetic/`) and the unit-test fixtures were written for this repository and
  are released as CC0-1.0. Brand names appear only as imitation targets; domains are invented.

## How real-world claims will be evaluated

Nothing here supports a claim yet. A claim will need: consented or licensed messages, redacted and checked by a
second person; two independent annotators with κ ≥ 0.70 and adjudication; campaign-aware splits with a real-only
frozen test set; thresholds frozen on `dev`; and one logged test run with campaign-bootstrap intervals, compared with
B0–B3. PLAN.md §6 and §8 set the targets (e.g. at least ~75 test items per legitimate category before quoting a
per-category false-alarm rate). Every public number must trace to a committed report.

## Known limitations

- Synthetic results only; same author for rules and data; 12 scams in the test split.
- Rule-only mode can never say `NO_STRONG_SIGNALS`, and no message with a link can, until a lookup adapter exists.
- Rules are sentence-scoped regexes. Punctuation noise, keyword typos, Hinglish spelling variety and Devanagari mixing
  still cause misses (see the Robustness report). The confusables table is a selected subset.
- `registered_domain` uses a short list of multi-label suffixes, not the full Public Suffix List.
- B2's fixed thresholds make it abstain at this data size. B3 has not been run; no model was configured.
- No rate limiting: the API is a local research tool, not a public service. Add rate limiting before exposing it.
- Near-duplicate search is O(n²) pairwise Jaccard: fine for a few thousand items; switch to MinHash/LSH beyond that.
- With very small strata the greedy group split cannot hit the 60/15/25 ratios (most singleton strata land in `train`).
- κ is computed on the first two annotations of each item, assuming the same two people annotate throughout.
- No temporal hold-out yet (PLAN.md §5 step 7); `collected_at` is stored so it can be added.

## Future work (only where evidence justifies it)

1. Run the pilot once consent-v1 is reviewed, then report B0–B4 on real `dev` data.
2. Add human review for the 219 needs-review variants, and measure prompt-injection flips with confirmed labels.
3. Address the measured gaps: punctuation-tolerant windows and Hinglish spelling normalisation, each re-measured in
   the Robustness Lab.
4. Configure B3 and use the optional Promptfoo red-team config (`promptfoo/`) against it, with synthetic inputs only.
5. Fine-tune a multilingual encoder only if enough legally usable labelled data exists and B2/B3 show headroom.

## Dataset pipeline

```bash
scamcheck validate data/annotated/items.jsonl                 # schema + cross-field rules, line-numbered errors
scamcheck group    data/annotated/items.jsonl \
                   --out data/processed/items.grouped.jsonl \
                   --review data/review/near_dup_pairs.jsonl \
                   --decisions data/review/near_dup_decisions.jsonl
scamcheck split    data/processed/items.grouped.jsonl --out data/splits/manifest.json
scamcheck check-leakage data/processed/items.grouped.jsonl --manifest data/splits/manifest.json \
                   --decisions data/review/near_dup_decisions.jsonl
scamcheck report   data/processed/items.grouped.jsonl --manifest data/splits/manifest.json \
                   --review data/review/near_dup_pairs.jsonl --out reports/quality/dataset_report.md
scamcheck schema --check                                      # schema/item.schema.json matches the models
```

What each step guarantees:

| Step | Guarantee |
|---|---|
| `validate` | Enumerated labels/categories/evidence types; category matches label (ambiguous has none); donated items carry a consent id; public/advisory items carry a source URL; synthetic items carry a `synthetic` block and only they may; URLs are stored defanged; evidence spans lie inside the text; annotator disagreements are adjudicated with a rationale; ids are unique. Exact duplicates and unverified licences are reported as warnings. |
| `group` | Items join one group (`campaign_id`) on: identical normalised text, char-5-gram Jaccard ≥ 0.6, same scam domain (shared platforms like `t.me`/`web.app` and any domain also seen on a non-scam item excluded), same pseudonymised `scammer_ids`, synthetic seed / adversarial parent lineage, or a reviewer "same" decision. Pairs with similarity 0.4–0.6 and every domain/scammer link are written to the review file. |
| `split` | Splits whole groups, never single items, stratified by label × language (60/15/25, fixed seed). Groups containing synthetic items or unverified licences can never enter `test` (real items blocked this way are listed). Adversarial variants are evaluation-only and listed with their parent's split. Items without gold labels are excluded. |
| `check-leakage` | Independently re-checks: no campaign, exact-duplicate text, scam domain or near duplicate crosses splits; no item changed since the manifest was written; nothing ineligible is in `test`. Exit code 1 on any problem. |
| `report` | Counts by label, label × language, category, basis, script, channel, source, licence; κ and adjudication stats; group sizes; per-split composition; leakage result; gaps against the PLAN.md targets. Synthetic content is called out at the top. |

`--allow-synthetic-in-test` exists only for pipeline testing; the manifest records it and the report prints a warning.

## Reviewing near duplicates

`group` writes `near_dup_pairs.jsonl` with `status` = `needs_review` for borderline pairs. For each, look at both
texts and append a decision to `data/review/near_dup_decisions.jsonl`:

```json
{"a": "dn-0012", "b": "dn-0047", "decision": "same"}
{"a": "dn-0013", "b": "dn-0101", "decision": "different"}
```

Re-run `group`. "same" forces a merge; "different" stops the similarity edge (it cannot split exact duplicates,
shared scam domains or lineage).

## Adding properly sourced examples

Never commit raw messages. `data/raw/` is gitignored; only redacted items go in `data/annotated/`.
**No source is approved yet and no real data has been collected.** The pilot follows
[docs/PILOT_WORKFLOW.md](docs/PILOT_WORKFLOW.md), whose start condition includes a legal review of consent-v1.

1. **Check the source is usable before collecting anything.**
   - *Donated* (you, family, classmates): the donor is 18+, read the consent text (`docs/PILOT_WORKFLOW.md`,
     pending legal review), and agreed. Record a `consent_id` (`c-NNNN`); set `licence` to the consent form version
     (e.g. `consent-v1`) and `licence_verified: false`. Donations are never releasable or test-eligible until their
     consent version is listed in `APPROVED_CONSENT_VERSIONS` (`schema.py`), which happens only after the legal review
     is recorded in `data/source_register.csv`.
   - *Public dataset*: read its licence page yourself. Record the SPDX id and the URL; set `licence_verified: true` only
     after you have read it. Spam corpora are not scam corpora; check that labels mean what we need.
   - *Official advisory* (bank, police, regulator notice quoting a scam text): store text only under an accepted open
     licence or a recorded written permission (`licence: "permission-NNNN"`, with conditions in the source register).
     Unclear rights → reference-only; the schema rejects advisory items with `licence: "unknown"`.
   - Unknown licence (other source types) → `licence: "unknown"`, `licence_verified: false`. Such items may help during
     development but are blocked from `test` and from any release. Only licences in `ACCEPTED_LICENCES` (`schema.py`)
     validate; add one there only after reading its terms.
   - Record ids use the format `prefix-NNNN` (`dn-0001`, `oa-0042`); the schema rejects ids that are not.
   - Do not scrape or bulk-download anything whose terms you have not checked.
2. **Redact** every field before it leaves your machine, using the placeholder table and
   [REDACTION_CHECKLIST.md](docs/templates/REDACTION_CHECKLIST.md): names, phones, emails, UPI ids, account and card
   numbers, OTPs, ID numbers and addresses → `<NAME>`, `<PHONE>`, `<EMAIL>`, `<UPI>`, `<ACCT>`, `<CARD>`, `<OTP>`,
   `<ID>`, `<ADDRESS>`. This includes `sender.value` (the schema rejects real sender numbers) and URL query strings.
   Scammer phone numbers and UPI ids are also replaced (they may belong to mule-account victims). Keep scam URL
   domains, defanged: `hxxps://evil[.]in/x`. The automated check (`scamcheck validate`, `pilot-intake`) scans every
   field but cannot detect names or addresses, so the human check by a second person is mandatory.
   Record `redaction: {"version": "r1", "checked_by": "<second person>"}`. Record each scammer phone/UPI/email as a
   token in `scammer_ids` with `scamcheck pseudo-id PHONE "<number>"` (needs `SCAMCHECK_PSEUDO_KEY`, kept outside the
   repo) so campaigns stay linkable after redaction.
3. **Fill the item**: `language` (`english`/`hinglish`), `script`, `channel`, `urls` with `registered_domain`, and the
   provenance block. Use a source prefix in ids (`dn-` donated, `pd-` public dataset, `oa-` advisory, `sy-` synthetic).
4. **Annotate twice, independently** (two different people, guideline version recorded, no model pre-labels).
   Add both to `annotations`.
5. **Set `gold`**. If annotators agree, copy their label with the right `basis` (`donor_confirmed` when the donor knows
   the outcome, `official_advisory`, `sender_verified`, otherwise `annotator_judgment`). If they disagree, a third
   person adjudicates: `adjudicated: true` plus a one-line `rationale`; undecidable → `ambiguous`.
6. Run `validate`, then the rest of the pipeline. Fix every error; read every warning.

Synthetic or augmented items are allowed for train/dev only and must use `source_type: "synthetic"` with the
`synthetic` block filled in (method, generator, seed id).

## Layout

```
src/scamcheck/engine/  parse · redact · rules · urls · llm · combiner · explain · models   (one analyse() path)
src/scamcheck/eval/    baselines · metrics · benchmark · mutate · robustness
src/scamcheck/api.py   FastAPI app            src/scamcheck/examples.py  synthetic demo examples
src/scamcheck/data/    schema · io · normalise · grouping · split · report · pii · pilot
src/scamcheck/cli.py   command line entry point (`scamcheck`)
web/                   Next.js App Router frontend (Analyse, Benchmark Lab, Robustness Lab, Method)
benchmarks/synthetic/  synthetic benchmark set, builder, grouped items, split manifest
reports/               generated benchmark and robustness reports (synthetic), test-run log
schema/                item.schema.json generated from the pydantic models
tests/                 unit, property-based and API tests + synthetic fixtures
data/                  annotated/ processed/ review/ splits/ (raw/ is gitignored)
docs/                  ARCHITECTURE, PLAN, AUDIT, annotation and pilot procedures, PROJECT_SUMMARY
```
