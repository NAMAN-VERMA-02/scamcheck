# Annotation pilot (M1): 50–100 real English/Hinglish messages

Goal: test the guidelines and the tooling on **real, properly sourced** messages before collecting at scale.
Pilot items are never synthetic.

## Roles (at least three people)

| Role | Does | Must not |
|---|---|---|
| **Collector** | Gets consent, redacts, creates intake items, records `basis` | Annotate or adjudicate items they collected |
| **A1, A2** | Annotate blind, independently | Talk about items before adjudication; see each other's sheets |
| **Adjudicator** | Decides each disagreement and writes a rationale | Adjudicate an item they annotated or collected (the tool enforces the first part) |
| **Redaction checker** | A second person who checks every redacted item | Be the person who redacted it |

One person can hold several roles **for different items**. For example, you can collect a family member's
messages while two classmates annotate them and a third adjudicates.

## Target composition (80 items; at least 50 to finish the pilot)

| Group | Category | Target | At least Hinglish |
|---|---|---:|---:|
| Legitimate | `bank_txn_alert` | 10 | 3 |
| Legitimate | `otp` | 8 | 2 |
| Legitimate | `delivery_notification` | 8 | 2 |
| Legitimate | `payment_confirmation` (including genuine payment or collect requests) | 8 | 3 |
| Promotional | `marketing` | 8 | 3 |
| Scam | `phishing_credential` | 8 | 3 |
| Scam | impersonation: `bank_kyc_impersonation`, `govt_impersonation`, `delivery_scam` | 14 | 5 |
| Scam | `upi_collect_refund` (fake payment requests) | 6 | 3 |
| Scam | `investment_trading`, `job_task_scam` | 10 | 4 |
| Either | Whatever annotators later find `ambiguous` | — | — |

Don't force-fill a category. Report the shortfall instead. Promotional messages that turn out to be scams are labelled `scam` anyway.

## Allowed sources for the pilot

1. **Donated messages** from the collector, family or classmates:
   - Each donor is 18 or older and has read the consent text below.
   - Each donor gets a `consent_id` (`c-0001`, …) recorded in `data/raw/consent_register.csv` (gitignored), with the date and the donor's initials only.
   - Licence: `consent-v1`; set `licence_verified: true`.
2. **Official advisories** that quote a scam text verbatim (a bank, RBI, CERT-In, a police cyber cell):
   - Record the page URL and read the site's terms.
   - Set `licence: unknown` and `licence_verified: false` unless the page carries an accepted open licence. These items are allowed in the pilot but can never be in test or a release.
3. **Not allowed:** scraping, downloading datasets, screenshots from social media, or anything whose terms you have not read.

### Consent text v1 (read to or by every donor)

> I am 18 or older. I am sharing SMS/WhatsApp messages I received so they can be used to build and test a scam
> checker. Before anything is stored, names, phone numbers, account numbers, OTPs and addresses will be replaced by
> placeholders. The redacted text may be published in an open research dataset. I can withdraw by contacting
> <coordinator>, and my messages will be removed from future versions. I will not share messages that contain other
> people's private conversations.

## Steps

All commands append to `data/pilot/audit_log.jsonl`. Each entry has a timestamp, the SHA-256 hashes of the input and output files, counts, and the hash of the previous line, so editing or deleting history is detectable.

**0. One-time setup**
- Create a long random secret for pseudonymising scammer numbers and keep it **outside the repo**, for example in a password manager:
  ```bash
  export SCAMCHECK_PSEUDO_KEY='<random 32+ chars>'
  ```
- Losing the key means new tokens won't match old ones. Leaking it lets someone confirm a guessed number.

**1. Intake (collector)**
- Copy each message into `data/raw/` (gitignored).
- Redact:
  - real names, phone numbers, account or card digits, OTPs and addresses → `<NAME>`, `<PHONE>`, `<ACCT>`, `<OTP>`, `<ADDRESS>`
  - URLs → defanged (`hxxps://x[.]in`)
- Record each scammer phone, UPI ID or email as a token:
  ```bash
  scamcheck pseudo-id PHONE "+91 98xxxxxx10"
  ```
  Put the result in `scammer_ids`, and use `<PHONE>` in the text.
- Write one JSON line per message to `data/pilot/intake.jsonl` with:
  - `id`: `dn-…` for donated, `oa-…` for advisories
  - `language`, `script`, `channel` and `sender`
  - `urls`, with `registered_domain`
  - `provenance` and `redaction`
  - **no `gold` and no `annotations`**
- Write the ground-truth basis for each item into `data/pilot/basis.csv` (`id,basis`), where it's known:
  - `donor_confirmed`: the donor knows the outcome
  - `sender_verified`: a DLT header from a known bank
  - `official_advisory`

**2. Redaction check (second person)**
- Read every item and fix anything missed.
- Set `redaction.checked_by`.
- Then run:
  ```bash
  scamcheck validate data/pilot/intake.jsonl
  ```
  It must report **0 errors**.

**3. Blind sheets**
```bash
scamcheck pilot-sheet data/pilot/intake.jsonl --annotator A1 --out data/pilot/sheets/A1.csv
scamcheck pilot-sheet data/pilot/intake.jsonl --annotator A2 --out data/pilot/sheets/A2.csv
```
- Each annotator gets the items in a different random order.
- Sheets contain no labels from anyone else.
- Sheets are UTF-8 CSV and open in Excel or Google Sheets.
- Annotators fill in `label`, `category`, `confidence`, `evidence` and `note`, following [ANNOTATION_GUIDELINES.md](ANNOTATION_GUIDELINES.md) g1. They must **not edit `text`**.

**4. Import (all-or-nothing per sheet)**
```bash
scamcheck pilot-import data/pilot/intake.jsonl --sheet data/pilot/sheets/A1.csv --annotator A1 --guideline g1 --out data/pilot/items.jsonl
scamcheck pilot-import data/pilot/items.jsonl  --sheet data/pilot/sheets/A2.csv --annotator A2 --guideline g1 --out data/pilot/items.jsonl
```
If any row is invalid, nothing from that sheet is imported:
- unknown label or category
- a category that doesn't fit its label
- an evidence phrase that isn't in the text
- edited text
- confidence outside 1–3

Fix the row and re-run.

**5. Resolve and adjudicate**
```bash
scamcheck pilot-resolve data/pilot/items.jsonl --out data/pilot/items.jsonl --adjudication data/pilot/adjudication.csv
```
- Full agreement on label and category sets gold with `basis: annotator_judgment`.
- The adjudicator fills `final_label`, `final_category`, `basis` and a one-line `rationale` for every row of `adjudication.csv`. Undecidable items become `ambiguous`. Then:
  ```bash
  scamcheck pilot-adjudicate data/pilot/items.jsonl --sheet data/pilot/adjudication.csv --adjudicator A3 --out data/pilot/items.jsonl
  ```
- For agreed items whose `basis.csv` entry isn't `annotator_judgment`, add a row to an adjudication sheet with the same label, the recorded basis and the rationale "basis from intake", and apply it the same way.

**6. Measure and report**
```bash
scamcheck validate data/pilot/items.jsonl
scamcheck group  data/pilot/items.jsonl --out data/pilot/items.grouped.jsonl --review data/pilot/near_dup_pairs.jsonl
scamcheck report data/pilot/items.grouped.jsonl --review data/pilot/near_dup_pairs.jsonl --out reports/quality/pilot_report.md
```
The pilot needs no split; it is for measuring the guidelines.

## Acceptance criteria (pilot passes only if all hold)

| # | Criterion |
|---|---|
| 1 | ≥ 50 real items (0 synthetic); `validate` reports 0 errors |
| 2 | ≥ 30% Hinglish; at least 6 of the 9 composition rows have ≥ 5 items |
| 3 | Every item has two independent annotations and a gold label; every disagreement has an adjudication rationale |
| 4 | Cohen's κ on label ≥ 0.70. Below that, run one guideline revision (g2) and re-annotate the **whole** pilot from fresh sheets. If κ is still < 0.70, stop and redesign the label set |
| 5 | Every adjudicated disagreement is tagged in its rationale with a cause: `guideline_gap`, `annotator_error`, `genuinely_ambiguous` or `missing_context`. Fix each `guideline_gap` in g2 |
| 6 | The redaction checker has signed off every item (`redaction.checked_by` is not the redactor) |
| 7 | `audit_log.jsonl` hash chain is intact (each `prev` equals the SHA-256 of the line before it) |
| 8 | The near-duplicate review file has no `needs_review` pairs left undecided |

**What the pilot does not establish:**
- any detection performance
- prevalence of scam types
- whether the dataset represents Indian users

It measures only whether people can label these messages consistently.
