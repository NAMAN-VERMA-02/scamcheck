# Candidate data sources: verification register

Checked on **2026-10-25** against each source's own page (UCI, Mendeley, Hugging Face and RBI re-fetched live, bypassing
any cache). **Nothing was downloaded, scraped or redistributed.** Machine-readable copy: `data/source_register.csv`.

Legend: ✅ verified on the source page · ⚠️ unverified or ambiguous · ❌ checked and absent.

**No source is approved.** A licence shown on a dataset's landing page covers what the publisher could license. It
does not settle the rights in the underlying messages, screenshots or component corpora, or the privacy of the
people in them. Every source needs a named human to sign `licence_verified_by` in the register before it is used.

## Summary

| # | Source | Page licence | Underlying rights | Personal data | Status |
|---|---|---|---|---|---|
| 1 | Consented donations | `consent-v1` (our form) | Donor's own received messages | Yes: redact before storing | **Blocked:** consent-v1 is pending legal review; collection has not started |
| 2 | UCI SMS Spam Collection | ✅ CC BY 4.0 | ⚠️ Compiled from "free or free for research sources"; component terms not checked | **Yes: unredacted numbers and names** | **Candidate, not approved** |
| 3 | Mendeley smishing set | ✅ CC BY 4.0 | ⚠️ OCR of internet screenshots; the screenshots' rights aren't addressed | ⚠️ Unknown | **Blocked** |
| 4 | bolewara Hinglish set | ✅ CC-BY-4.0 | Hinglish part written by the author; ⚠️ English "curated" part of unknown origin | ⚠️ Unknown | **Blocked for real-data use** (synthetic) |
| 5 | Smishtank Dataset I | ❌ None | Community submissions; no reuse grant | ⚠️ Unknown | **Blocked** |
| 6 | SMSDHL | ❌ None seen; paper says "academic and non-commercial" | ⚠️ Inbox contributors' contacts' consent not described | ⚠️ Unknown | **Blocked** |
| 7 | RBI material (BE(A)WARE etc.) | ✅ All rights reserved | All rights reserved | No | **Reference only** |

## Details

### 1. Consented donations
- **Licence:** our own consent text, `consent-v1` in `docs/PILOT_WORKFLOW.md`.
- ⚠️ **It has not been reviewed by anyone with legal or data-protection expertise.** India's DPDP Rules (notified Nov 2025; most duties apply from about May 2027, per our earlier research) and college policy may apply.
- **Status: blocked** until a reviewer approves consent-v1 and records it.
- **Content risk:** received messages contain other people's data (senders, names). Redaction is mandatory, and the consent form can't grant rights the donor doesn't hold.
- **Language:** English and Hinglish are expected, but nothing has been collected yet.

### 2. UCI SMS Spam Collection
- **Page:** <https://archive.ics.uci.edu/dataset/228/sms+spam+collection>, DOI `10.24432/C5CC84`.
- **Licence:** ✅ "This dataset is licensed under a Creative Commons Attribution 4.0 International (CC BY 4.0) license… provided that the appropriate credit is given."
- ✅ **Composition per the page:**
  - 425 spam messages "manually extracted from the Grumbletext Web site", a UK forum
  - 3,375 ham from the NUS SMS Corpus. Its volunteers "were made aware that their contributions were going to be made publicly available"; they were largely Singaporean students.
  - 450 ham from Caroline Tagg's PhD thesis
  - the SMS Spam Corpus v.0.1 Big (1,002 ham, 322 spam)
- ⚠️ **Underlying rights:** the page says the corpus "has been collected from free or free for research sources". The component sources' own terms were not checked, so whether UCI's CC BY grant fully covers them is an **assumption**.
- ✅ **Personal data:** the page's own sample rows include an unredacted UK phone number (a ham message giving the sender's own number; not reproduced here) and first names. **Any import must go through the full redaction and `pilot-intake` checks.**
- **Language:** ✅ English, from the UK and Singapore. It has no Indian or Hinglish content, and its labels are spam/ham, not scam.
- **Attribution:** required. Credit Almeida & Hidalgo and the DOI.
- **Status:** candidate, not approved, and not downloaded.

### 3. Mendeley: SMS Phishing Dataset for Machine Learning and Pattern Recognition
- **Page:** <https://data.mendeley.com/datasets/f45bkkt8pr/1>, DOI `10.17632/f45bkkt8pr.1`, 2022-06-20.
- **Licence:** ✅ CC BY 4.0 (the page's Licence field).
- ✅ **Collection:** "The data has been collected by converting the images obtained from the Internet to text using Python code."
  - 5,971 messages: 4,844 ham, 489 spam, 638 smishing.
  - The authors thank Tiago A. Almeida, creator of #2, for "making the text messages available", so the two likely overlap.
- ⚠️ **Underlying rights:** the screenshots' rights aren't addressed. The page licence can't be assumed to cover them.
- ⚠️ **Language and country:** **not stated on the page**. The earlier register entry "english" was an assumption and has been removed.
- **Status:** **blocked**; not downloaded.

### 4. bolewara/hinglish-scam-text-dataset
- **Page:** <https://huggingface.co/datasets/bolewara/hinglish-scam-text-dataset>
- **Licence:** ✅ README front matter `license: cc-by-4.0`; languages `en`, `hi`, `hi-Latn`.
- ✅ **Composition:**
  - "Hinglish scam: 35, **Hand-written**"; "Hinglish benign: 28, **Hand-written**"
  - English portions "derived from the public SMS Spam Collection (UCI)" plus "curated" texts ⚠️ of unstated origin
- **Status:** the Hinglish part is synthetic under our rules. **Blocked for real-data use**; at most train/dev augmentation after review, tagged `synthetic`. Not downloaded.

### 5. Smishtank Dataset I
- **Page:** <https://smishtank.com/dataset>; paper arXiv:2402.18430.
- ✅ **Paper:** "a corpus of 1062 smishing messages" from community submissions.
- ❌ **No licence.** The site's terms and dataset pages only ask for citation.
- ⚠️ Language and country are not stated.
- **Status:** **blocked** until the authors give written permission.

### 6. SMSDHL
- **Source:** preprint <https://www.techrxiv.org/doi/pdf/10.36227/techrxiv.173603655.53756505>
- ✅ **Paper:** messages gathered by students "from their own inboxes and those of their friends, relatives, neighbors"; 11,611 messages; access "for academic and non-commercial purposes".
- ❌ **No licence text** was seen; the hosting page was not opened.
- ⚠️ The Hindi script and any Hinglish content are unverified, and so is consent from the contacts whose messages were collected.
- **Status:** **blocked**. A non-commercial term would also conflict with an open release.

### 7. RBI material
- **Page:** <https://www.rbi.org.in/commonman/english/scripts/Disclaimer.aspx>
- ✅ The page shows "© Reserve Bank of India" and states that "caching and links to, and the framing of this Web Site or any of the contents are prohibited" except as permitted.
- **Status:** **reference only**. Read it to learn scam patterns, but don't store its text verbatim in the dataset without written permission.
- Other banks' and police cyber-cell advisories each need their own terms checked.

## How rights are recorded (all sources)
- **Open licence on the page:** record the SPDX id in `licence`. It must be in `ACCEPTED_LICENCES`.
- **Written permission:**
  - Add a register row with `source_id` `permission-NNNN`, giving the grantor, date, scope and conditions (attribution, no redistribution, etc.).
  - Items use `licence=permission-NNNN`.
  - Keep the permission document itself outside the repo.
  - The tools count the permission as granted only if the row's `source_id` is exactly `permission-NNNN`, its `status` starts with `PERMITTED`, and `licence_verified_by` is signed. They read `data/source_register.csv` from the repository root; with no register, no permission is granted.
- **Donations:** `licence=consent-vN`, a reuse right granted by the donor, is separate from `consent_id`, which is the privacy permission for a specific person. A donation is releasable only when its consent version has a recorded legal review *and* is listed in `APPROVED_CONSENT_VERSIONS`.
- **Unclear rights:** not reusable. The source stays blocked or reference-only. The schema rejects advisory items with `licence=unknown`.
- `licence_verified` is `no` until a second person checks the licence or permission text. Nothing becomes releasable because a template or spreadsheet pre-filled `yes`.

## Gaps and failed checks
- Component licences of the UCI corpus: not checked.
- Smishtank language composition: not found.
- SMSDHL hosting page: not opened.
- Terms for advisories other than RBI's: not checked.
- COMI-LINGUA (code-mixed Hinglish, CC-BY-4.0 per the earlier research notes): not re-verified and not scam-labelled.
- NUS SMS Corpus GitHub mirror (<https://github.com/kite1988/nus-sms-corpus>): shows no licence text.
