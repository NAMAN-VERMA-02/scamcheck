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

## Start condition

**Do not collect any real message until all of these hold:**
- consent-v1 has been reviewed by someone with legal or data-protection expertise, and the outcome is recorded in `data/source_register.csv` (`src-donations`);
- the latest code review is clean;
- the three roles below are filled.

Until then, every row in the source register stays blocked or reference-only.

## Allowed sources for the pilot

1. **Donated messages** from the collector, family or classmates, *after* consent-v1 is approved:
   - Each donor is 18 or older and has read the consent text below.
   - Each donor gets a `consent_id` of the form `c-NNNN` (`c-0001`, …; `c-0000` is reserved for tests), recorded in `data/raw/consent_register.csv` (gitignored) with the date and the donor's initials only.
   - **Three separate questions**, recorded separately:
     1. **Privacy permission:** did this donor consent? That is the `consent_id`.
     2. **Reuse right:** that is the `licence` (`consent-v1`).
     3. **Review state:** has a human verified the licence? That is `licence_verified`.
   - Always enter `licence_verified=no`. Intake refuses `yes` for a consent version that isn't in `APPROVED_CONSENT_VERSIONS` (`src/scamcheck/data/schema.py`, empty today).
   - A donation only becomes releasable or test-eligible once a reviewer has recorded the legal review in `data/source_register.csv` *and* added the version to that list. A pre-filled `yes` can't bypass this.
2. **Official advisories** that quote a scam text verbatim. Store the text only if reuse is actually permitted:
   - **If the page carries an open licence:** use its SPDX id (it must be in `ACCEPTED_LICENCES`), with the exact `source_url`.
   - **If you hold written permission:**
     - Add a register row `permission-NNNN` that records who granted it, the date, the scope and the conditions (e.g. attribution, no redistribution).
     - Use `licence=permission-NNNN`.
     - The tools only treat the permission as granted when that row's `source_id` is exactly `permission-NNNN`, its `status` starts with `PERMITTED`, and a second person has signed `licence_verified_by`. Otherwise items citing it stay out of test and releases, and `validate` says why.
     - Store the permission document itself outside the repo.
   - **If the rights are unclear:** the source is **reference-only**. Read it to learn patterns, but never store its text. The schema rejects an `official_advisory` item with `licence=unknown`.
   - **RBI material is all rights reserved: reference only** unless written permission is recorded as above.
   - `licence_verified` starts at `no`. It becomes `yes` only after a second person has checked the licence or permission text.
3. **Not allowed:**
   - scraping or downloading datasets
   - screenshots from social media
   - any source marked blocked in [DATA_SOURCES.md](DATA_SOURCES.md)
   - anything whose terms you have not read

### Consent text v1: draft, pending legal review (read to or by every donor)

> I am 18 or older. I am sharing SMS/WhatsApp messages I received so they can be used to build and test a scam
> checker. Before anything is stored, names, phone numbers, email addresses, UPI IDs, account and card numbers,
> OTPs and addresses will be replaced by placeholders. The redacted text may be published in an open research
> dataset. I can withdraw by contacting <coordinator>, and my messages will be removed from future versions. I will
> not share messages that contain other people's private conversations.

## Steps

All commands append to `data/pilot/audit_log.jsonl`. Each entry has a timestamp, the SHA-256 hashes of the input and output files, counts, and the hash of the previous line, so editing or deleting history is detectable.

**0. One-time setup**
- Create a long random secret for pseudonymising scammer numbers and keep it **outside the repo**, for example in a password manager:
  ```bash
  export SCAMCHECK_PSEUDO_KEY='<random 32+ chars>'
  ```
- Losing the key means new tokens won't match old ones. Leaking it lets someone confirm a guessed number.

**1. Consent and raw capture (collector)**
- Before taking any message, record the donor in `data/raw/consent_register.csv` (gitignored), using the columns in `docs/templates/consent_register_template.csv`.
  - Record the donor's initials only, never their full name or phone number.
  - The `consent_id` (`c-0001`, …) is the only link between an item and a person.
- Copy each message as received into `data/raw/` (gitignored). Screenshots stay there too, and never leave the machine.
- **Withdrawal:** find every item whose `provenance.consent_id` matches, delete it from `data/pilot/`, and set `withdrawn_on` in the register. A future release must not contain it.

**2. Redacted intake CSV (collector)**
- Copy `docs/templates/intake_template.csv` to `data/pilot/intake.csv`. Add one row per message; it opens in Excel or Google Sheets.
  - `id`: `dn-0001`, `dn-0002`, … for donated messages; `oa-0001`, … for advisories. The format is a 2–4 letter prefix, a hyphen, and 3–6 digits. Ids are sequential and carry no donor information; the schema rejects anything else, such as a phone number or a name.
  - `text`: the **redacted** message. Replace every real identifier with a placeholder:

    | Identifier | Placeholder |
    |---|---|
    | Person's name | `<NAME>` |
    | Phone number (mobile, landline, WhatsApp) | `<PHONE>` |
    | Email address | `<EMAIL>` |
    | UPI ID (`name@bank`, `98…@ybl`) | `<UPI>` |
    | Bank account number | `<ACCT>` |
    | Card number | `<CARD>` |
    | OTP, PIN, CVV or verification code | `<OTP>` |
    | Aadhaar, PAN, passport, vehicle number or other ID | `<ID>` |
    | Postal address or PIN code | `<ADDRESS>` |

    - Masked digits the sender already printed (e.g. `XX1234`) may stay.
    - Transaction, UTR, order and AWB reference numbers may stay; they identify a transaction, not a person.
  - `sender_type` / `sender_value`. **Never enter a real number or address here.**
    - `phone`: `<PHONE>`, a pseudo-id token, or a public short code (e.g. `56161`).
    - `email`: `<EMAIL>` or a token.
    - `dlt_header`: the header as shown (e.g. `VM-HDFCBK`).
    - Leave both blank if unknown.
    - Intake rejects anything else.
  - `urls`: the defanged URLs (`hxxps://x[.]in/path`), space-separated.
    - **Redact query parameters and path parts that carry identifiers:** `?ph=98…` becomes `?ph=<PHONE>`, and `/u/ravi@okaxis` becomes `/u/<UPI>`.
    - Keep the domain; it's evidence.
  - `registered_domains`: one domain for each URL, in the same order (`x.in`).
  - `scammer_ids`: tokens from `scamcheck pseudo-id PHONE "<number>"` (also `UPI`, `EMAIL`, `ACCT`), space-separated. The number itself becomes `<PHONE>`, `<UPI>` etc. in the text.
  - Provenance:
    - **Donations:** `source_type=donated`, `source_name=donation-form-v1`, `licence=consent-v1`, **`licence_verified=no`**, plus the `consent_id` (`c-NNNN`). Intake rejects `yes` while consent-v1 is pending legal review.
    - **Advisories:** only when reuse is permitted (see "Allowed sources" above). Use `source_type=official_advisory`, `source_url=<exact page>`, `licence=<SPDX id>` or `licence=permission-NNNN`, and `licence_verified=no` until a second person checks it. Unclear rights mean reference-only: there is no intake row at all.
  - `basis`, where known:
    - `donor_confirmed`: the donor knows the outcome
    - `sender_verified`: a DLT header from a known bank
    - `official_advisory`
    - blank otherwise
  - Every source used must have a row in `data/source_register.csv`. Investigated public sources and their status are in [DATA_SOURCES.md](DATA_SOURCES.md).

**3. Redaction check (a second person), then conversion**
- Read every row of `intake.csv` against the raw message and work through [REDACTION_CHECKLIST.md](templates/REDACTION_CHECKLIST.md). Fix anything missed and fill `redaction_checked_by`.
- **The human check is the real safeguard.** The automated check below is a safety net:
  - **it cannot detect names or addresses at all;**
  - it misses identifiers written in unusual ways (e.g. spelled out in words, base64 in a URL, split by words, or non-Indian formats such as `+1 …`);
  - **it deliberately lets through these formats, which you must check by eye:**
    - any number directly after `Order ID`, `Txn ID`, `AWB`, `Tracking`, `Invoice`, `Booking` or `PNR`. That's correct for real order ids, but a personal mobile number written there is not flagged;
    - exactly 12 digits in a UPI/IMPS slot (`UPI/P2A/…/`, `IMPS/…/`, `UPI Ref No …`). This is the transaction RRN, but an Aadhaar number written there is indistinguishable unless the word "Aadhaar" is nearby;
    - **payee and payer names inside UPI/IMPS messages** (`UPI/P2A/412345678901/RAVI KUMAR`). These are real people's names and must become `<NAME>`;
  - back-to-back phone numbers separated only by spaces are flagged, but may be labelled "long number" rather than "phone number".
- Save the sheet as **CSV UTF-8**:
  - Excel: File > Save As > "CSV UTF-8 (Comma delimited)"
  - Google Sheets: File > Download > CSV

  Excel's plain "CSV (Comma delimited)" uses the ANSI code page and turns Devanagari into `?`. Intake rejects such files, and re-saving can't restore characters an earlier save already lost; re-export from the original.
- Then run:
  ```bash
  scamcheck pilot-intake data/pilot/intake.csv --out data/pilot/intake.jsonl --basis-out data/pilot/basis.csv
  ```
  It refuses to write if:
  - any row is invalid, including a real sender number
  - an output file already exists
  - **any field** (text, sender, URLs including query strings, source name, notes) still looks like it contains:
    - a phone number (any format, including Devanagari or full-width digits)
    - an email (including `[at]`/`[dot]` forms) or a UPI ID
    - an Aadhaar-like, account, card, PAN, IFSC, passport or vehicle number
    - an OTP, PIN or verification code

  If a warning is a false alarm (e.g. a customer-care number printed by a bank), a human checks it and re-runs with `--allow-pii-warnings`. The audit log records the warning count.
- `pilot-import` and `pilot-adjudicate` run the same check on annotator notes and adjudication rationales.

**4. Blind sheets**
```bash
scamcheck pilot-sheet data/pilot/intake.jsonl --annotator A1 --out data/pilot/sheets/A1.csv
scamcheck pilot-sheet data/pilot/intake.jsonl --annotator A2 --out data/pilot/sheets/A2.csv
```
- Each annotator gets the items in a different random order.
- Sheets contain no labels from anyone else.
- Sheets are UTF-8 CSV and open in Excel or Google Sheets.
- Annotators fill in `label`, `category`, `confidence`, `evidence` and `note`, following [ANNOTATION_GUIDELINES.md](ANNOTATION_GUIDELINES.md) g1. They must **not edit `text`**.

**5. Import (all-or-nothing per sheet)**
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

**6. Resolve and adjudicate**
```bash
scamcheck pilot-resolve data/pilot/items.jsonl --out data/pilot/items.jsonl --adjudication data/pilot/adjudication.csv --basis data/pilot/basis.csv
```
- Full agreement on label and category sets gold, with the `basis` recorded at intake (`annotator_judgment` if none was recorded).
- The adjudicator fills `final_label`, `final_category` and a one-line `rationale` for every row of `adjudication.csv`; `basis` comes pre-filled from intake. Undecidable items become `ambiguous`. Then:
  ```bash
  scamcheck pilot-adjudicate data/pilot/items.jsonl --sheet data/pilot/adjudication.csv --adjudicator A3 --out data/pilot/items.jsonl
  ```

**7. Measure and report**
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
