# scamcheck — dataset & benchmark infrastructure

Phase 1 of an English + Hinglish scam-checking engine. Thesis: **measured trust, not another chatbot**. This
repository currently contains only the data pipeline: schema, validation, duplicate/campaign grouping, leakage-safe
splits and a dataset quality report. There is no detector yet and **no performance results anywhere in this repo**.

Design rationale and milestones: [docs/PLAN.md](docs/PLAN.md). Engineering audit: [docs/AUDIT.md](docs/AUDIT.md).
Annotation: [docs/ANNOTATION_GUIDELINES.md](docs/ANNOTATION_GUIDELINES.md) and the pilot procedure
[docs/PILOT_WORKFLOW.md](docs/PILOT_WORKFLOW.md) (`scamcheck pilot-sheet / pilot-import / pilot-resolve /
pilot-adjudicate / pseudo-id`).

## Setup

Requires Python 3.11+.

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows (Git Bash: source .venv/Scripts/activate); macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

Dependencies: `pydantic>=2.5` (runtime), `pytest>=8` (dev). Nothing else, and nothing is downloaded at runtime.

No install? Run from the checkout with `PYTHONPATH=src python -m scamcheck.cli ...` and `PYTHONPATH=src python -m pytest`.

## Run the tests

```bash
pytest -q
```

The tests use only `tests/fixtures/synthetic_items.jsonl` and `tests/fixtures/invalid_items.jsonl`. Every fixture
message is **hand-written and synthetic** (`source_type: "synthetic"`, `source_name: "unit-test-fixture"`); brands
like "XYZ Bank" and the domains are invented. They exist to exercise the pipeline and must never be cited as
real-world evidence. Regenerate them with `python tests/fixtures/build_fixtures.py` (a test checks the committed files
match the builder).

## Pipeline

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

1. **Check the source is usable before collecting anything.**
   - *Donated* (you, family, classmates): the donor is 18+, read the consent text (to be written in
     `docs/DATA_POLICY.md`), and agreed. Record a `consent_id`; set `licence` to the consent form version (e.g. `consent-v1`).
   - *Public dataset*: read its licence page yourself. Record the SPDX id and the URL; set `licence_verified: true` only
     after you have read it. Spam corpora are not scam corpora; check that labels mean what we need.
   - *Official advisory* (bank, police, regulator notice quoting a scam text): record the URL and the page's terms.
   - Unknown licence → `licence: "unknown"`, `licence_verified: false`. Such items may help during development but
     are blocked from `test` and from any release. Only licences in `ACCEPTED_LICENCES` (`schema.py`) validate;
     add one there only after reading its terms.
   - Do not scrape or bulk-download anything whose terms you have not checked.
2. **Redact** before the text leaves your machine: real people's names, phone numbers, account/card digits, OTPs,
   addresses → `<NAME>`, `<PHONE>`, `<ACCT>`, `<OTP>`, `<ADDRESS>`. Scammer phone numbers and UPI ids are also
   replaced (they may belong to mule-account victims). Keep scam URL domains, defanged: `hxxps://evil[.]in/x`.
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
src/scamcheck/data/   schema.py  io.py  normalise.py  grouping.py  split.py  report.py
src/scamcheck/cli.py  command line entry point (`scamcheck`)
schema/               item.schema.json generated from the pydantic models
tests/                unit tests + synthetic fixtures (tests/fixtures/build_fixtures.py)
data/                 annotated/ processed/ review/ splits/ (raw/ is gitignored)
docs/PLAN.md          implementation plan
```

## Known limitations

- Near-duplicate search is O(n²) pairwise Jaccard: fine for a few thousand items; switch to MinHash/LSH beyond that.
- With very small strata the greedy group split cannot hit the 60/15/25 ratios (most singleton strata land in `train`).
  This resolves once each label × language stratum has dozens of groups.
- κ is computed on the first two annotations of each item, assuming the same two people annotate throughout.
- No temporal hold-out yet (PLAN.md §5 step 7); `collected_at` is stored so it can be added.
- URL lookups (RDAP, CT, reputation) are schema fields only; no lookup code exists yet.
