# Datasheet

Structure follows Gebru et al., "Datasheets for Datasets". The repository holds two kinds of data, and they must
never be confused:

| Dataset | Status | Where |
|---|---|---|
| **ScamCheck synthetic benchmark v1** | Exists. 114 hand-written synthetic messages | `benchmarks/synthetic/` |
| **ScamCheck real dataset** (planned) | **Does not exist.** No message has been collected | would live in `data/annotated/` |
| **External-author check set** (third-party, not ours) | 38 Hinglish rows (16 scam, 22 benign) selected from `bolewara/hinglish-scam-text-dataset` @ `7437992`, CC BY 4.0, by Anuj Bolewar. Used once for evaluation only; **no text is stored or redistributed** here, only row indices. The card's 35 + 28 rows are not all present in the file (Deviation 1) | `reports/external/bolewara/` (indices, plan, results); data in gitignored `data/raw/external/` |

The unit-test fixtures (`tests/fixtures/`, 20 valid and 14 invalid synthetic lines) exist only to test the
pipeline and are not a dataset.

## 1. Motivation

- **Why:** to measure, rather than assert, how a scam checker behaves on English and romanised-Hinglish messages:
  false alarms on legitimate bank/OTP/delivery/payment messages, dangerous misses, abstention and the language gap.
  The research notes found no vendor-published false-positive rates and only one small (63-item) Hinglish scam set
  (`docs/DATA_SOURCES.md`).
- **Synthetic benchmark:** exists so that the grouping, splitting, benchmark and robustness code can be exercised
  end to end and published without any personal data.
- **Created by** the project maintainer. **Funding:** none.

## 2. Composition

### Synthetic benchmark v1 (counts from `benchmarks/synthetic/items.jsonl`)

| | English | Hinglish | Total |
|---|---:|---:|---:|
| scam | 26 | 26 | 52 |
| legitimate | 24 | 24 | 48 |
| promotional | 4 | 4 | 8 |
| ambiguous | 3 | 3 | 6 |
| **total** | 57 | 57 | **114** |

- Scam categories: bank/KYC impersonation 8, government impersonation 8, phishing/credential 7, job/task 6, other
  6, UPI collect/refund 4, investment 4, lottery/prize 4, delivery 3, loan app 2.
- Legitimate categories: bank transaction alert 8, service/account 8, personal 8, OTP 7, payment confirmation 6,
  government notice 6, delivery notification 5. Promotional: marketing 8.
- Channels: SMS 84, WhatsApp 23, other 4, Telegram 2, email 1. Script: Latin only. 20 items contain a (defanged) URL.
- 114 campaigns: no two items were grouped together. Split (seed 13, `--allow-synthetic-in-test`): train 68, dev
  18, test 28 (12 scam, 12 legitimate, 2 promotional, 2 ambiguous).
- Every item carries `collected_at = 2026-10-25`, the date the set was written. So **a temporal hold-out is
  impossible on this set**, and `scamcheck split --temporal-cutoff` refuses it with that reason.
- Intentionally hard cases: 6 scams with no strong keyword, legitimate messages with threat-like wording (a card
  "blocked as requested", a police fraud advisory), and genuinely ambiguous openers.
- Brands (SBI, HDFC, Amazon…) appear only as imitation targets. "XYZ Bank" and "Example …" names and all domains are
  invented. Placeholders (`<PHONE>`, `<UPI>`, `<OTP>`, `<REF>`, `<NAME>`) stand in for identifiers. No personal data.
- Derived data: `reports/robustness/synthetic/variants.jsonl` holds 1,725 seeded mutation variants of dev/test
  parents. These are evaluation fixtures with lineage, never training data.

### Planned real dataset (targets from PLAN.md §8 M2, not facts)

≥ 900 non-ambiguous items; real-only test set with ≥ 120 English and ≥ 120 Hinglish scams and ≥ 75 legitimate items
in each of at least 4 legitimate categories.

## 3. Collection

- **Synthetic:** hand-written by the maintainer on 2026-10-25 (`benchmarks/synthetic/build.py`). No model generated
  any text. The **same person wrote the rule pack**, which makes results on this set optimistic by construction.
- **Real (planned):** consented donations (donors 18+, own received messages), plus public datasets or official
  advisories only where the licence or a recorded written permission allows reuse. The process is
  `docs/PILOT_WORKFLOW.md`. Nothing is scraped. Status of every candidate source: `data/source_register.csv`. All
  are blocked, candidate or reference-only; **none is approved**.
- `collected_at` records when the project collected an item, not when the message was received. A temporal
  hold-out on real data therefore measures drift in *collection* time; donors' late submissions blur it.

## 4. Licences and consent

- Synthetic benchmark and fixtures: written for this repository, released as **CC0-1.0**. Code: Apache-2.0.
- Consent form `consent-v1`: **draft, pending legal review**. `APPROVED_CONSENT_VERSIONS` is empty, so donated items
  cannot enter a test split or a release. `RECORDED_PERMISSIONS` is empty because no register row is signed as
  permitted.
- Accepted open licences are listed in `ACCEPTED_LICENCES` (`schema.py`). Unknown licences block test and release.
- Nothing in this datasheet approves a source or a consent version. That requires the documented review recorded in
  `data/source_register.csv` (`docs/PILOT_READINESS.md`).

## 5. Preprocessing and cleaning

- Storage: URLs defanged (`hxxps://`, `[.]`). Identifiers replaced with placeholders.
- Redaction (real data): a human second-person check is mandatory (`docs/templates/REDACTION_CHECKLIST.md`). The
  automated detector (`data/pii.py`) is a safety net that cannot find names or addresses. The engine's
  `engine/redact.py` is assistance before model calls, not anonymisation.
- Grouping: exact and near duplicates (char 5-gram Jaccard ≥ 0.6), shared scam domain, scammer id, lineage, and
  reviewer decisions → `campaign_id`. Splits are made by campaign, never by item.
- Raw donations stay in gitignored `data/raw/` and are deleted 30 days after verified redaction (PLAN §7).

## 6. Annotation

- Synthetic: labelled by the author (`basis: annotator_judgment`, no `annotations` entries). There is no agreement
  statistic because there was one annotator.
- Real (planned): two independent annotators per item with no model pre-labels, guideline-versioned
  (`docs/ANNOTATION_GUIDELINES.md`). Cohen's κ ≥ 0.70 on the pilot; a third person adjudicates every disagreement
  with a rationale; undecidable items become `ambiguous`.
- Mutation variants: labels are inherited only after human review (guideline `mr1`, `docs/ROBUSTNESS_REVIEW.md`).
  Currently 0 reviews exist, so 0 variants carry a label.

## 7. Uses

**Intended:**
- testing the pipeline;
- demonstrating the benchmark and robustness workflow;
- regression tests for the engine;
- teaching how to evaluate a checker with honest uncertainty.

**Not intended:**
- estimating real-world detection accuracy, or comparing with commercial products;
- training a production model;
- quoting any number from it as evidence of effectiveness;
- inferring anything about real scam prevalence or about the brands named.

## 8. Limitations

- Same author for data and rules; a small test split (12 scams); one collection date; Latin script only (Devanagari
  appears only in mutation variants).
- Categories are unevenly covered: 2 loan-app scams, 3 delivery scams.
- Synthetic Hinglish reflects one writer's spelling habits. The mutation lab shows that spelling variants alone cost
  the rules about 9 points of verdict consistency.

## 9. Distribution and maintenance

- Distributed in this repository. Regenerate with `python benchmarks/synthetic/build.py`; a test checks the
  committed file matches the builder.
- Changes bump the source name (`scamcheck-synthetic-benchmark-v1`) and are noted in `reports/test_runs.md` when
  they affect reported numbers.
- The real dataset will get its own datasheet section before release, with withdrawal handling from the consent
  form.
