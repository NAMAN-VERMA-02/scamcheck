# Pilot readiness (status as of 2026-10-25)

**Verdict: the pilot cannot start.**
- No real messages have been collected. None may be collected until every item in §4 is ticked.
- Nothing here is a legal review, and no consent version or permission has been approved.
- The detector does not exist yet. Its real-world accuracy and user demand are unmeasured.

## 1. Consent and permissions

### Current status (verified in the repository)
| Item | Status | Where |
|---|---|---|
| `consent-v1` text | **Draft, pending legal review** | `docs/PILOT_WORKFLOW.md` ("Consent text v1") |
| `APPROVED_CONSENT_VERSIONS` | **Empty**, so no donation is releasable or test-eligible | `src/scamcheck/data/schema.py` |
| Intake | Rejects `licence_verified=yes` for an unapproved consent version | `src/scamcheck/data/pilot.py` |
| `RECORDED_PERMISSIONS` | Built only from register rows that are `PERMITTED` and signed; there are none, so no permission counts as granted | `data/source_register.csv` |
| Every source in the register | **Blocked, candidate (not approved) or reference-only**; none is approved | `data/source_register.csv`, `docs/DATA_SOURCES.md` |

### Requirements before consent-v1 can be used
1. A reviewer with legal or data-protection competence (for example the college's data-protection, ethics or legal contact) reviews the text against the checklist below and records the outcome, reviewer role and date in the `src-donations` row of `data/source_register.csv`.
2. Only after step 1, a maintainer adds `"consent-v1"` to `APPROVED_CONSENT_VERSIONS` in a separate, reviewable commit that references the register row.
3. If the reviewer requires changes, the text becomes `consent-v2` and v1 is never approved.

### Consent review checklist (questions for the reviewer, not answers)
Mark each item *adequate*, *needs change* or *not applicable*, and note the reason.

- [ ] **Scope:** which messages may be shared (received SMS/WhatsApp only)? Is excluding private conversations clear enough, and is it enforceable?
- [ ] **Purpose:** the stated purpose is "build and test a scam checker". Does it cover research publication, benchmark evaluation by third parties, and any future commercial use? Anything not named should be excluded or asked for separately.
- [ ] **Two separate permissions.** The draft currently combines them in one sentence:
  - *permission to submit* (we may store and use the redacted message internally for annotation and evaluation);
  - *permission to redistribute or publish* (the redacted text may appear in an open dataset).

  Should these be separate opt-ins? A donor may agree to the first and not the second.
- [ ] **Retention:** how long are raw messages in `data/raw/` and the consent register kept? The plan's default is to delete raw data 30 days after redaction is verified, but the consent text doesn't say so.
- [ ] **Withdrawal:** how does it work before and after publication? "Removed from future versions" can't recall copies already downloaded; the donor must be told this.
- [ ] **Redaction promise:** the text promises specific placeholders. Is that promise accurate given the documented limits (names and addresses depend on human review)?
- [ ] **Third parties:** received messages contain *senders'* data, and scam senders may be mule-account victims. Can a donor's consent cover this, and is redaction sufficient?
- [ ] **Attribution:** donors are not credited, and `consent_id` is the only link to them. Confirm this is acceptable and stated.
- [ ] **Age and capacity:** "18 or older" is self-declared. Is that sufficient?
- [ ] **Applicable law and policy:** India's DPDP Act and Rules (staggered commencement per the earlier research notes, not verified here), plus the college's research-ethics policy. Is a notice with the controller's identity and contact required? Who is the controller?
- [ ] **Permitted evaluation use:** may redacted donated items be used in a held-out test set that is published with the benchmark?
- [ ] **Record keeping:** is initials plus date in a gitignored register enough evidence of consent?

### Current system gap (reported, not changed)
The schema records one reuse right per donation (`licence = consent-vN`) plus the privacy permission (`consent_id`). It **does not** record a separate "may redistribute" opt-in. If the reviewer requires separate opt-ins, the schema, intake template and release gate need a change first. That change would need its own approval.

## 2. Human roles

### Separation rules (from `PILOT_WORKFLOW.md` and `ANNOTATION_GUIDELINES.md` §9)
| Rule | Enforced by |
|---|---|
| A1 and A2 are two different people who annotate blind | Tool: a second annotation by the same `annotator` id is rejected. Independence itself relies on process |
| The adjudicator never adjudicates an item they annotated | **Tool** (`pilot-adjudicate` rejects it) |
| The collector or donor of an item never annotates or adjudicates that item | Process only |
| The redaction checker is not the person who redacted the item | Process only (`redaction.checked_by` is free text) |

### Minimum team
- **Four people** for any item that needs adjudication: collector, A1, A2 and an adjudicator who is none of those.
  - The workflow heading previously said "at least three". Its own rules, and its example, require four; the heading is now corrected.
- **The redaction checker** may be A1, A2 or the adjudicator, but not the collector of that item.
  - Recommended: the adjudicator, because annotators should see only redacted text.
- **Roles can rotate across items.** For example, Person 1 collects batch 1 while Persons 2 and 3 annotate it and Person 4 adjudicates; for batch 2, Person 2 collects and so on. The per-item rules above must still hold.

### Role assignment template
Copy `docs/templates/role_assignment_template.csv` to `data/raw/role_assignment.csv`, which is gitignored. Record initials or role codes only: no full names, phone numbers or emails in the repository. Annotator and adjudicator codes (A1, A2, A3) are what the tools record.

## 3. Readiness checklist (80-item pilot)

**Every** box must be ticked, with evidence, before the first real message is collected.

**Consent and lawful collection**
- [ ] consent-v1 (or a successor) reviewed by a competent reviewer; outcome recorded in `data/source_register.csv`
- [ ] the approved version added to `APPROVED_CONSENT_VERSIONS` in its own reviewed commit
- [ ] the controller and contact for withdrawal named in the consent text (replacing `<coordinator>`)
- [ ] the retention period decided and written into the consent text and the workflow
- [ ] the college or ethics approval requirement confirmed (needed or not needed), with evidence

**Sources and provenance**
- [ ] donations are the only planned source; every public source stays blocked or reference-only as in the register
- [ ] any advisory text to be stored has an accepted licence or a `PERMITTED`, signed `permission-NNNN` register row

**People**
- [ ] at least four distinct people assigned (collector, A1, A2, adjudicator) and a redaction checker named, using role codes in `data/raw/role_assignment.csv`
- [ ] each person has read `ANNOTATION_GUIDELINES.md` (g1), `PILOT_WORKFLOW.md` and `REDACTION_CHECKLIST.md`
- [ ] annotators agree not to discuss items before adjudication

**Environment and secrets**
- [ ] `SCAMCHECK_PSEUDO_KEY` generated and stored outside the repository (e.g. in a password manager), and the collector knows how to set it
- [ ] `data/raw/` confirmed gitignored on the collector's machine (`git check-ignore data/raw/x`)
- [ ] the collector's spreadsheet app saves **CSV UTF-8**

**Dry run (synthetic only)**
- [ ] full `pilot-intake` → `pilot-sheet` → `pilot-import` → `pilot-resolve` → `pilot-adjudicate` → `validate` → `group` → `report` rehearsed on the synthetic fixtures by the actual team, using a scratch folder rather than `data/pilot/`
- [ ] audit-log hash chain checked after the dry run

**During the pilot** (from `PILOT_WORKFLOW.md` acceptance criteria)
- [ ] every row checked against `REDACTION_CHECKLIST.md` by the redaction checker
- [ ] two blind annotations per item; every disagreement adjudicated with a rationale and a cause tag
- [ ] κ on label ≥ 0.70, or one guideline revision then a stop
- [ ] near-duplicate review completed; audit log intact

**What the pilot can and cannot show:** whether people can label these messages consistently. It does not measure detection accuracy, scam prevalence or representativeness.
