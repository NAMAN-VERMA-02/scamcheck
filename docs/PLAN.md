# ScamCheck v1 — Implementation Plan

Working name: `scamcheck` (placeholder). Scope: English + Hinglish text messages and the URLs inside them.
Thesis: **measured trust**. The evaluation system is built first; the checker is a thin interface on top.

Legend used throughout:
- **[FACT]** — verified in our research notes (source in `research_notes/`), or a mathematical property.
- **[ASSUMPTION]** — believed true, not yet verified; must be checked before relying on it.
- **[DECISION]** — a design choice made here; can be changed.

---

## 0. Non-negotiable rules (from the V1 decisions)

1. Verdicts are exactly: `LIKELY_SCAM`, `UNCLEAR`, `NO_STRONG_SIGNALS`. There is no "safe" label anywhere in code, UI or docs.
2. The model can push a verdict **toward** scam, never force `NO_STRONG_SIGNALS`. That verdict requires *all* independent checks to be quiet (see §1.3).
3. No claim about competitors or "accuracy" leaves the repo unless it is produced by the frozen test-set report with confidence intervals.
4. Out of scope for v1: voice, deepfakes, screenshots/OCR, browser extension, family verification, WhatsApp, live URL fetching.

---

## 1. System architecture and data flow

### 1.1 Components

```
                 ┌─────────────────────────── OFFLINE (built first) ───────────────────────────┐
 sources ──▶ ingest ──▶ redact ──▶ annotate ──▶ adjudicate ──▶ group/dedup ──▶ split ──▶ freeze
 (donated,     (normalise,  (PII→       (2 people,     (3rd person   (campaign ids)   (train/dev/  (hash +
  public,       URL          placeholders) independent)  on conflict)                  test)        manifest)
  synthetic)    snapshot)                                                                            │
                                                                                                     ▼
                                           eval harness ◀── baselines B0–B3 ◀── engine (same code as online)
                                                │
                                                ▼
                                     report: metrics + CIs + slices + error list
                 └────────────────────────────────────────────────────────────────────────────┘

                 ┌──────────────────────────── ONLINE (later) ──────────────────────────────────┐
 user text ──▶ API ──▶ normalise ──▶ redact ──▶ [rules] [url signals] [model] ──▶ combiner ──▶ verdict
                                                                                             + red flags
                                                                                             + next step
                 (no message stored; log = verdict + signal ids + latency only)
                 └────────────────────────────────────────────────────────────────────────────┘
```

The **same `engine` package** runs offline (on the dataset) and online (behind the API). There is no separate "demo" code path.

### 1.2 Engine stages

| Stage | Input → Output | Notes |
|---|---|---|
| `normalise` | raw text → canonical text + extracted URLs/phones/UPI handles | Unicode NFKC, strip zero-width / bidi control chars (record that they were present — that is itself a signal), lowercase copy for rules, URL extraction incl. defanged/obfuscated forms |
| `redact` | text → text with `<PHONE>`, `<ACCT>`, `<OTP>`, `<NAME>`, `<AMOUNT>` placeholders | Runs **before** any external call. Scam infrastructure (URL domains, UPI handle suffix) is kept because it is evidence |
| `rules` | text → list of `Signal(id, severity, span)` | Hand-written, versioned rule pack: OTP/PIN request, KYC/account-block threat, UPI collect/"enter PIN to receive", remote-access app names, "digital arrest"/police/CBI/customs, task/job-for-payment, guaranteed returns, urgency + link combos |
| `url_signals` | URLs → `Signal`s | Lookalike/homoglyph vs. brand list, shortener, raw IP host, punycode, suspicious TLD list, domain age (RDAP), CT first-seen, reputation list hit. **Offline: read from the snapshot taken at collection time** (§3) — never live-queried during eval |
| `model` | redacted text → `{p_scam, category, flags[]}` | Structured JSON output. Message content is passed as a quoted data field, never as instructions. v1 = LLM via API; later = fine-tuned encoder |
| `combiner` | signals + model output → verdict | Pure function, fully unit-tested, see §1.3 |
| `explain` | verdict + signals → user text in the user's register (English or Hinglish) | Templated from signal ids first; model text only for phrasing. Never invents a red flag that has no signal behind it |

### 1.3 Combiner policy [DECISION]

```
if any rule/url signal with severity == HIGH:            LIKELY_SCAM
elif model.p_scam >= T_HIGH:                              LIKELY_SCAM
elif (no MEDIUM+ signals) and model.p_scam <= T_LOW
     and all url checks completed (or no URLs present)
     and no injection/obfuscation signal:                 NO_STRONG_SIGNALS
else:                                                     UNCLEAR
```

- `T_HIGH`, `T_LOW` are tuned on **dev only**, then frozen before the test run.
- Model failure or timeout → never `NO_STRONG_SIGNALS`; rules-only result, capped at `UNCLEAR` unless a HIGH signal fires.
- The model can never cancel a HIGH signal. This is enforced by a property test.

---

## 2. Repository structure

```
scamcheck/
├── README.md
├── pyproject.toml                  # one package, Python 3.11+
├── .gitignore                      # data/raw/, data/private/, .env, *.cache
├── docs/
│   ├── PLAN.md                     # this file
│   ├── ANNOTATION_GUIDELINES.md
│   ├── THREAT_MODEL.md
│   ├── DATA_POLICY.md              # consent, retention, licensing
│   └── DATASHEET.md                # filled at release
├── schema/
│   └── item.schema.json            # generated from the pydantic model, committed
├── src/scamcheck/
│   ├── data/
│   │   ├── schema.py               # pydantic models = single source of truth
│   │   ├── validate.py             # CLI: validate a .jsonl file
│   │   ├── redact.py
│   │   ├── grouping.py             # near-dup + campaign clustering
│   │   └── split.py                # grouped, stratified split + manifest
│   ├── engine/
│   │   ├── normalise.py
│   │   ├── rules/                  # rule pack + version file
│   │   ├── url_signals.py
│   │   ├── model.py                # provider adapter + response cache
│   │   ├── combiner.py
│   │   └── explain.py
│   ├── eval/
│   │   ├── run.py                  # CLI: system × split → predictions.jsonl
│   │   ├── metrics.py              # rates, Wilson + cluster-bootstrap CIs
│   │   ├── baselines.py            # B0–B3
│   │   └── report.py               # markdown report + error list
│   └── app/                        # milestone 6
│       └── api.py
├── data/
│   ├── raw/                        # gitignored, encrypted at rest, deleted per policy
│   ├── annotated/                  # redacted + annotated, may be committed once licensing clears
│   └── splits/                     # manifest.json with ids + content hashes
├── reports/                        # generated eval reports (committed)
└── tests/
    ├── fixtures/sample_items.jsonl
    ├── test_schema.py
    ├── test_combiner.py
    ├── test_grouping.py
    └── test_split_leakage.py
```

---

## 3. Dataset schema

One JSON object per line (`.jsonl`). Pydantic model in `src/scamcheck/data/schema.py`; `schema/item.schema.json` is generated from it.

```jsonc
{
  "id": "sc-000123",                       // stable, never reused
  "schema_version": "1.0",
  "text": "Dear customer aapka SBI account <ACCT> block ho jayega ...",  // REDACTED text only
  "channel": "sms",                        // sms | whatsapp | telegram | email | other | unknown
  "sender": {"type": "dlt_header", "value": "VM-XXXXXX"},  // optional; dlt_header | phone | email | unknown
  "language": "hinglish",                  // english | hinglish
  "script": "latin",                       // latin | devanagari | mixed
  "code_mix_index": 0.42,                  // computed, not hand-entered

  "urls": [{
    "raw": "hxxps://sbi-kyc-update[.]in/x",  // stored defanged
    "registered_domain": "sbi-kyc-update.in",
    "snapshot": {                          // taken ONCE at collection time, reused by every eval run
      "taken_at": "2026-11-02T10:00:00Z",
      "rdap_created": "2026-10-28",        // null if lookup failed
      "ct_first_seen": "2026-10-28",
      "reputation_hit": null,              // provider name or null
      "lookup_errors": []
    }
  }],

  "gold": {
    "label": "scam",                       // scam | legitimate | promotional | ambiguous
    "category": "bank_kyc_impersonation",  // see category list below
    "basis": "annotator_judgment",         // donor_confirmed | official_advisory | sender_verified | annotator_judgment
    "adjudicated": false,
    "evidence": [{"start": 21, "end": 47, "type": "account_block_threat"}]
  },

  "annotations": [                         // every individual judgement, kept for agreement stats
    {"annotator": "A1", "label": "scam", "category": "bank_kyc_impersonation",
     "confidence": 3, "evidence": [{"start": 21, "end": 47, "type": "account_block_threat"}],
     "note": "", "at": "2026-11-03"}
  ],

  "provenance": {
    "source_type": "donated",              // donated | public_dataset | official_advisory | synthetic
    "source_name": "donation-form-v1",
    "source_url": null,
    "licence": "consent-v1",               // SPDX id, or consent form version, or "unknown" (unknown = cannot ship)
    "consent_id": "c-0045",                // required when source_type == donated
    "collected_at": "2026-11-02"
  },
  "synthetic": null,                       // or {"generator": "...", "seed_id": "sc-000100", "method": "paraphrase|template|translate"}
  "adversarial": null,                     // or {"type": "prompt_injection|zero_width|homoglyph|transliteration|llm_rewrite", "parent_id": "sc-000100"}

  "campaign_id": null,                     // filled by grouping.py
  "redaction": {"version": "r1", "checked_by": "A1"}
}
```

**Label set [DECISION]**
- `scam` — tries to obtain money, credentials, OTP/PIN, remote access or personal data under false pretences.
- `legitimate` — genuine transactional or informational message from the entity it claims to be.
- `promotional` — genuine but unsolicited marketing. It is kept separate so we don't hide false positives inside "legitimate", and is reported as its own slice.
- `ambiguous` — a careful expert could not decide from the message and URL snapshot. It is excluded from the primary metrics and used to test that the system returns `UNCLEAR`.

**Categories [DECISION]**
- Scam:
  - `phishing_credential`
  - `bank_kyc_impersonation`
  - `govt_impersonation` (e-challan, electricity, digital arrest, customs)
  - `delivery_scam`
  - `upi_collect_refund`
  - `job_task_scam`
  - `investment_trading`
  - `loan_app`
  - `lottery_prize`
  - `other_scam`
- Legitimate:
  - `bank_txn_alert`
  - `otp`
  - `payment_confirmation`
  - `delivery_notification`
  - `govt_notice`
  - `service_account` (telecom, utility)
  - `personal`
  - `marketing` (for the `promotional` label)

---

## 4. Annotation guidelines and adjudication

Full text goes in `docs/ANNOTATION_GUIDELINES.md`. These are the core rules.

**What annotators judge.** Label what a careful expert would conclude from the message text, sender field and URL snapshot. Do not use outside knowledge of this specific message. Exception: when `basis` is `donor_confirmed` or `official_advisory`, the gold label comes from that basis, and annotators still record their own blind judgement so we can measure how hard the item is.

**Decision order:**
1. Does it ask for an OTP or PIN, a password, remote-access app installation, or payment to "receive" money? → `scam` (unless the sender is verified and the text is a standard "never share this OTP" message).
2. Does it impersonate an institution and push to a non-official domain or personal number/UPI? → `scam`.
3. Does it promise returns, a job-for-payment or a prize requiring a fee? → `scam`.
4. Is it a recognisable transactional template with no call to action other than "call the number on your card / ignore if it was you"? → `legitimate`.
5. Is it marketing from a plausible real brand with an official domain? → `promotional`.
6. Otherwise → `ambiguous`. Do not guess.

**Required on every item:**
- **Evidence:** at least one evidence span with a type from a fixed list, or for `legitimate`, the span that makes it look genuine.
- **Confidence:** 1 = guessing, 2 = fairly sure, 3 = certain.

**Process:**
- **Two independent annotators per item.** Neither sees the other's labels. No model pre-labels are shown for anything that may end up in dev or test.
- **Pilot:** 100 items. Compute Cohen's κ on `label`. If κ < 0.70, discuss the disagreements, revise the guidelines, and re-annotate the pilot from scratch.
- **Production batches:** κ is computed per batch of 100. A batch with κ < 0.60 is re-annotated after a guideline review.
- **Adjudication:** any disagreement on `label`, and on `category` within `scam`, goes to a third person. That person sees both annotations, records a final decision plus a one-line rationale, and sets `adjudicated: true`. If the adjudicator cannot decide, the item becomes `ambiguous`.
- **Guideline versioning:** each annotation records the guideline version; changing a rule bumps the version.

---

## 5. Train / dev / test split strategy

The goal is to stop the score from rewarding memorised scam templates.

1. **Normalise for grouping.** Mask numbers, amounts, names, URLs and phone numbers into placeholders, then lowercase.
2. **Near-duplicate edges.** Character 5-gram MinHash. Any pair with Jaccard ≥ 0.6 on the normalised text gets an edge. The threshold is tuned by eye on 50 pairs.
3. **Campaign edges.** Items sharing a registered domain, a scammer phone number, a UPI handle, or the same legitimate sender + template get an edge.
4. **Lineage edges.** A synthetic variant links to its `seed_id`, and an adversarial variant links to its `parent_id`.
5. **Groups.** Connected components (union-find) become `campaign_id`s.
6. **Split by group, never by item.** A greedy stratified group split targets 60/15/25 train/dev/test, balanced on `label × language × category`.
7. **Temporal holdout.** At least 30% of test-set scams come from campaigns collected after the training cutoff date, which is a better imitation of "new scam scripts".
8. **Synthetic policy [DECISION]:**
   - The test set is **real items only**: donated, official advisory, or licensed public data. Synthetic items may go in train and dev only.
   - Why: LLM-written scams may be easier for LLM detectors and would inflate scores. This is an [ASSUMPTION] we will measure on dev.
9. **Freeze.**
   - `data/splits/manifest.json` stores ids plus a SHA-256 hash of each item.
   - The test set is evaluated only at milestones M4 and M7.
   - Every run is logged in `reports/test_runs.md`; no tuning after viewing test results.
10. **Leakage tests in CI:**
    - No `campaign_id` appears in two splits.
    - The maximum cross-split normalised-text Jaccard is below the grouping threshold.
    - No URL domain appears in two splits.

---

## 6. Evaluation

### 6.1 Metrics (all reported per language and per category)

| Metric | Definition | Why |
|---|---|---|
| **False-alarm rate** | P(`LIKELY_SCAM` \| legitimate), per legit category | The core trust claim |
| **Dangerous-miss rate** | P(`NO_STRONG_SIGNALS` \| scam) | The worst failure: the user is reassured about a scam |
| Scam catch rate | P(`LIKELY_SCAM` \| scam) | Recall |
| Unclear rate | P(`UNCLEAR`), per class | Stops the system from "winning" by answering `UNCLEAR` to everything |
| Language gap | Hinglish − English, for each metric above | The core differentiation claim |
| Ranking quality | ROC-AUC and PR-AUC of `p_scam` | Model quality independent of thresholds |
| Calibration | Expected calibration error and a reliability plot of `p_scam` on dev | Required if a score is ever shown |
| Adversarial flip rate | Share of adversarial variants whose verdict moves toward `NO_STRONG_SIGNALS` compared with their parent | Robustness |
| Cost / latency | $ per 1k checks; p50 and p95 seconds | Operability |

### 6.2 Confidence intervals [FACT: statistics]
- **Single-proportion rates:** Wilson 95% interval.
- **Headline numbers:** **cluster bootstrap by `campaign_id`**, 2,000 resamples. Items in one campaign are not independent, so a plain bootstrap would give intervals that are too narrow.
- **System vs. baseline:** paired cluster bootstrap on the difference, plus McNemar's test.
- **Sample size reality check:**
  - With 0 false alarms in *n* legitimate items, the Wilson 95% upper bound is about 3.84/(n+3.84): roughly 6.0% at n=60, 3.7% at n=100 and 1.9% at n=200.
  - So a claim of "≤ 5% false alarms per category" needs **at least about 75 test items per legitimate category**, or the claim must be made on the pooled legitimate set instead.

### 6.3 Baselines

| ID | System | Purpose |
|---|---|---|
| B0 | Always `UNCLEAR` / always `LIKELY_SCAM` | Sanity floor; exposes metric gaming |
| B1 | Keyword rules only (our rule pack, no URL signals, no model) | How far rules alone get |
| B2 | Character n-gram TF-IDF + logistic regression trained on train | Cheap, strong, often under-estimated text baseline |
| B3 | Zero-shot LLM, fixed prompt, temperature 0, same verdict mapping | The baseline we must beat; "just ask the AI" |
| B4 | Full engine (rules + URL snapshot + model + combiner) | Our system |
| B5 (later) | Fine-tuned multilingual encoder (MuRIL / XLM-R class) | Cheaper, offline-capable model. [ASSUMPTION] that it suits code-mixed text, per arXiv 2602.21933 in our notes |

- **Consumer tools** (Scamio, Genie, etc.) are tested **manually on at most 50–100 items**, and only where their terms allow. Results go in a separate, clearly labelled appendix and never in the headline table.
- **LLM responses are cached** by (model id, prompt version, item hash), so a report can be regenerated exactly.

### 6.4 Error analysis (every report)
- **Confusion matrix** for each of: language, category, script, code-mix bin, has-URL, adversarial type.
- **Top 25 false alarms and top 25 dangerous misses**, each with the signals that fired and the model's reason.
- **Each error tagged** from a fixed list: `template_unseen`, `rule_overfire`, `url_signal_missing`, `model_hallucinated_flag`, `label_noise`, `translit_failure`, `injection_success`. Tag counts are tracked across versions.
- **Re-check before fixing:** any error tagged `label_noise` goes back to adjudication rather than being "fixed" in the system.

---

## 7. Privacy, security, licensing, retention

**Data handling**
- **Raw donations** live only in `data/raw/`, which is gitignored and stored on an encrypted disk.
  - They are redacted and checked by a second person, then **deleted within 30 days** [DECISION].
  - Only redacted text is ever sent to an external API.
- **What redaction covers:**
  - Real people's phone numbers, names, account and card digits, OTP codes, addresses and email addresses.
  - Scammer phone numbers and UPI IDs are also pseudonymised (they may belong to mule-account victims), consistently within an item.
  - Scam URL domains are kept for evidence and published defanged.
- **Consent form (v1).** It states what is collected, that the text is redacted, that the redacted text may be published in an open dataset, and how to withdraw. The donor must be 18 or older.
  - [FACT, medium confidence] India's DPDP Rules were notified on 14 Nov 2025, with most obligations including verifiable parental consent applying from about May 2027. Design to them now anyway.
- **External APIs:**
  - **LLM:** use a provider and plan whose API data is not used for training. [ASSUMPTION] Each provider's retention terms must be checked and recorded in `DATA_POLICY.md` before the first call.
  - **VirusTotal public API:** not used. [FACT] It is restricted to non-commercial use and 4 requests/minute.
  - **Google Web Risk:** may be used for reputation lookups. [FACT] Its results cannot be redistributed, so reputation hits are kept as a boolean signal and never as list data in the released dataset.
- **No live fetching of scam URLs in v1.** Only passive lookups: RDAP, Certificate Transparency and reputation lists. A sandboxed fetcher is a separate, later project.

**Online app**
- No message storage by default. Logs keep only the verdict, the signal ids, the rule-pack version and the latency.
- Rate limiting per IP / user.
- Rule details and raw scores are never shown to the user, because scammers can use a public checker to test evasions.

**Licensing**
- **Code:** Apache-2.0 [DECISION].
- **Dataset:** the release licence is decided per source.
  - Items with `licence: unknown` are **never released** and never used in the published test set.
  - [UNVERIFIED] UCI SMS Spam Collection licence, and the 63-item Hinglish scam set on Hugging Face (licence unconfirmed). Both need verifying before use.
  - [FACT, from notes] COMI-LINGUA is CC-BY-4.0 and code-mixed but has no scam labels, so it can only serve as a source of legitimate Hinglish style.
- [ASSUMPTION] If LLM-generated synthetic items are released, the generating provider's output terms must allow it.

**Threat model** (`docs/THREAT_MODEL.md`, milestone M5)

| Threat | Mitigation |
|---|---|
| Prompt injection inside the message | Content passed as data; strict output schema; injection detector raises a signal; model cannot force `NO_STRONG_SIGNALS` |
| Zero-width / homoglyph obfuscation | Handled in `normalise` and also raises a signal |
| Scammers using the checker as an oracle | Rate limits; scores and rule details not exposed |
| Poisoning of reputation data | No user-submitted reputation in v1 |
| Leaking user content | Redaction before every external call; no storage |
| Denial of service / cost blow-up | Per-user quota; hard monthly budget cap at the provider |

---

## 8. Milestones and acceptance criteria

Each milestone is done only when **every** criterion passes.

| # | Milestone | Acceptance criteria |
|---|---|---|
| **M0** | Repo, schema, validator | <ul><li>`scamcheck-validate tests/fixtures/sample_items.jsonl` exits 0</li><li>Invalid fixtures fail with a field-level error</li><li>Schema JSON regenerated from pydantic and matches the committed file</li><li>CI runs the tests on push</li></ul> |
| **M1** | Guidelines + pilot | <ul><li>`ANNOTATION_GUIDELINES.md` v1 written</li><li>100 pilot items double-annotated</li><li>κ on `label` ≥ 0.70 (after at most one revision round)</li><li>Every disagreement adjudicated with a rationale</li></ul> |
| **M2** | Dataset v0.1 + splits | <ul><li>≥ 900 non-ambiguous items</li><li>Test set real-only, with ≥ 75 legitimate items per legitimate category in at least 4 categories, ≥ 120 English scams and ≥ 120 Hinglish scams</li><li>All three leakage tests pass in CI</li><li>Manifest hashes committed</li><li>Every item has a provenance record and a licence ≠ `unknown`</li></ul> |
| **M3** | Eval harness + baselines | <ul><li>`scamcheck-eval --system B0..B3 --split dev` produces the report with CIs from cached responses</li><li>Re-running gives byte-identical metrics</li><li>B0 metrics match hand-computed values in a unit test</li></ul> |
| **M4** | Engine v1, test run #1 | <ul><li>Thresholds frozen on dev before the run</li><li>On the **test** set: false-alarm rate ≤ 5% pooled over legitimate items</li><li>Dangerous-miss rate ≤ 3%</li><li>Scam catch rate ≥ 85%</li><li>Unclear rate ≤ 25% on non-ambiguous items</li><li>Hinglish−English gap ≤ 5 points on catch rate and ≤ 3 points on false alarms</li><li>Beats B3 on dangerous-miss rate, or on false-alarm rate at equal catch rate, with the paired-bootstrap 95% interval excluding 0</li><li>**If B3 is not beaten:** publish the benchmark (Concept B) as the main result, and make no product claims</li></ul> |
| **M5** | Adversarial set + threat model | <ul><li>≥ 50 prompt-injection, 50 LLM-rewritten, 30 homoglyph-URL and 30 transliteration variants of dev and test parents</li><li>Injection flips to `NO_STRONG_SIGNALS` ≤ 2 of 50</li><li>Catch rate on rewritten scams ≥ 85%</li><li>Lookalike URLs flagged ≥ 90%</li><li>Threat model has no unmitigated high-severity item</li></ul> |
| **M6** | Web interface | <ul><li>FastAPI + single page</li><li>p95 latency ≤ 6 s for text</li><li>A test confirms no message text reaches logs</li><li>Explanation copy passes a comprehension test: ≥ 80% of 12 users restate the verdict and the next step correctly</li></ul> |
| **M7** | Public release | <ul><li>Dataset card and datasheet</li><li>Scorecard generated from the frozen test run</li><li>Limitations section</li><li>Every public claim traces to a line in a committed report</li></ul> |

Telegram integration is a post-M6 option, not a milestone.

---

## 9. Decisions that genuinely block implementation

| # | Decision | Blocks | Recommendation |
|---|---|---|---|
| 1 | **Who is annotator #2 and the adjudicator?** | M1 onward. A one-person dataset can't produce κ and won't be credible | Two classmates who speak Hinglish; you act as adjudicator only where you weren't an annotator |
| 2 | **Where do real messages come from?** Donation form, your own and your family's inboxes, official advisories (RBI, bank and police advisories quoting scam texts — licence check per source) | M2 | Start with your own and your family's SMS archives (consented, redacted) plus a Google Form for classmates |
| 3 | **Which LLM provider and budget** for model B3/B4 (retention terms, price, JSON output) | M3 | Pick one cheap model with structured output. [ASSUMPTION] Our notes put the Flash-Lite class at about $0.11 per 1k text checks |
| 4 | **Public or private repo until M7?** | M0 (CI and secrets setup) | Private until M7; code goes public with the scorecard |
| 5 | **Synthetic items allowed in train/dev?** (they are never allowed in test) | M2 | Yes, capped at 40% of train and tagged |

Not blocking now: web vs. Telegram, the encoder model choice, the project name, hosting.

---

## 10. Facts vs. assumptions summary

**Verified in our research notes:**
- Telegram bots are free with a 20 MB download limit.
- The VirusTotal public API is non-commercial only, at 4 requests/minute and 500/day.
- Web Risk forbids redistributing its results.
- Meta's AI-provider clause has applied since 15 Jan 2026.
- The DPDP Rules were notified on 14 Nov 2025, with a staggered start.
- COMI-LINGUA is CC-BY-4.0.
- The only Hinglish scam set we found has 63 examples.
- The prompt-injection attack on multimodal LLM detectors comes from Koide et al., accepted at RAID 2026.
- No vendor publishes false-positive rates.

**Assumptions to check before relying on them:**
- LLM price per 1k checks.
- LLM provider retention terms.
- The UCI SMS Spam licence.
- Web Risk pricing and free tier.
- That synthetic scams inflate LLM scores.
- That MuRIL / XLM-R handle Hinglish well.
- That DLT sender headers are a reliable "legitimate" signal (scam SMS sometimes arrive via registered headers, so this stays a weak signal only).

**There are no benchmark results yet.** Every number in §8 is a target set before testing, not a result.

---

## 11. First implementation task

**Task M0-1: the dataset schema and validator.** Everything else (annotation, grouping, splits, evaluation) reads and writes this format, so it comes first.

**Done when:**
- `pip install -e .` works.
- `scamcheck-validate tests/fixtures/sample_items.jsonl` exits 0.
- `scamcheck-validate tests/fixtures/invalid_items.jsonl` exits non-zero and prints the bad field for each line.
- `pytest` passes.

**What the validator enforces:**
- Enums for `label`, `category`, `language`, `script`, `source_type`, `basis`, and the evidence types.
- The category must belong to its label (no `otp` category on a `scam`).
- `consent_id` is required when `source_type == donated`.
- `synthetic` must be non-null when `source_type == synthetic`.
- Evidence spans must fall inside the text.
- Ids must be unique within a file.
- URLs must be stored defanged.

**Files:**

| File | Contents |
|---|---|
| `pyproject.toml` | Package metadata; deps: `pydantic>=2`, `pytest`; console script `scamcheck-validate` |
| `.gitignore` | `data/raw/`, `data/private/`, `.env`, caches |
| `src/scamcheck/__init__.py` | Empty |
| `src/scamcheck/data/__init__.py` | Empty |
| `src/scamcheck/data/schema.py` | Pydantic models from §3 with cross-field validators |
| `src/scamcheck/data/validate.py` | CLI: read the JSONL, validate every line, check id uniqueness, print errors with line numbers, exit code |
| `schema/item.schema.json` | Generated from `schema.py` (`Item.model_json_schema()`) |
| `tests/fixtures/sample_items.jsonl` | 10 hand-written, clearly synthetic items covering every label and both languages |
| `tests/fixtures/invalid_items.jsonl` | One item per validation rule, each broken in exactly one way |
| `tests/test_schema.py` | Valid items pass; each invalid item fails on the expected field; the generated schema matches the committed one |
