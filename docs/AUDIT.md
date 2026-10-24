# Phase 1 engineering audit (2026-10-25)

Scope: repository hygiene, plus the implementation of the schema, normalisation, grouping, splitting, leakage checker
and quality report. Regression tests for every defect are in `tests/test_audit_defects.py`. Each of those tests
failed before its fix; that was confirmed by running them before changing any code. The thresholds (0.6 near
duplicate, 0.4 review band) were **not** changed.

## A. Repository hygiene

| Check | Finding |
|---|---|
| Project path | A temporary folder the Claude app created for this session. **It is deleted when the session is deleted.** |
| Git root | `C:/Users/naman`: the **whole home directory** is a Git repository |
| Home repo state | Branch `master`, **0 commits**, 0 tracked files, no `.gitignore`. Remote `origin` = `https://github.com/eNVy-rights/MSE2FULLSTACK.git` |
| Project status | Every project file is untracked (`??`); nothing has been staged or committed by this work |
| Risk | A `git add .` + `git push` run anywhere in the home folder would stage and could publish `.ssh/`, `.claude.json`, `.npmrc`, `.docker/`, `.kube/` and similar credential stores to that remote. With 0 commits this looks accidental (probably a `git init` run in the wrong folder) |

**Recommendation (nothing has been moved or deleted):**
1. Confirm the home-directory repo is unintended. If it is, remove only `C:\Users\naman\.git`; with 0 commits nothing is lost except the remote setting. If it *is* intended, add a home `.gitignore` that ignores `*` and allow-lists only the intended folder.
2. Move this project to a dedicated folder **outside** the home repo, e.g. `C:\dev\scamcheck`, or `C:\Users\naman\Desktop\scamcheck` once step 1 is done. Then `git init` there and make the first commit from the project folder only, after `git status` shows just project files.
3. Files to carry over: everything listed in the README layout, plus `docs/`, `research_notes/` and `reports/`. Nothing in the project contains secrets or personal data; the fixtures are synthetic.

## B. Implementation audit

Severity: **H** invalidates results or leaks data · **M** distorts results or misleads · **L** friction.

| # | Concern | Finding | Sev | Fix and test |
|---|---|---|---|---|
| 1 | Does 0.6 merge unrelated messages? | Measured on realistic pairs. Different banks' OTP and debit-alert templates score **0.81–0.84**, so every bank using the same boilerplate merges. Unrelated short messages ("ok call me"/"pls call me") score 0.44 and land in review, not merged. A scam and a real KYC reminder score 0.18; job scams from different gangs 0.33. | M | Merging same-template messages is the *safe* direction for leakage: a model that learned bank A's template has effectively seen bank B's. The real cost is chaining (row 3). The threshold is unchanged; reviewers can record `different` to split auto-merged pairs. |
| 2 | Domain grouping merges unrelated campaigns | Domain links only applied to scams, so legitimate bank and delivery messages never linked by domain (OK). **Defect:** scams that *quote the real bank's domain* were merged with each other. **Defect:** free hosts missing from the shared-platform list (`web.app`, `firebaseapp.com`, `herokuapp.com`, …) merged unrelated scams. | H | A domain that also appears on any non-scam item no longer links, and the platform list was extended. Every domain link is now written to the review file (`linked_by_domain`) for audit. Tests: `test_official_domain_…`, `test_free_hosting_…` |
| 3 | Transitive giant groups | Confirmed: union-find chains A~B~C even when A and C are dissimilar. Eight messages each similar only to their neighbours became one group. A giant group moves as one unit, so whole categories can vanish from test. | M | Not "fixed" by weakening merges, because over-merging protects against leakage. The report now flags **Giant group** (≥ 5 items and > 5% of the data) with its category mix and points to the review file. Test: `test_transitive_chaining_…` |
| 4 | Synthetic/adversarial items stay with their source | Synthetic and adversarial items did stay grouped with their parents. **Defect:** because the group then held a synthetic member, the *real parent was silently barred from test*: every augmentation shrank the test pool, biased toward unaugmented items. **Defect:** a `seed_id`/`parent_id` pointing to a missing item was silently ignored. | H | Adversarial variants are now evaluation-only. They are excluded from train/dev/test, listed in `manifest.adversarial` with their parent's split, and never constrain the parent. Paraphrase-type synthetics still pin their group out of test, and the manifest and report now count `test_blocked_by_group`. A dangling lineage reference gives a warning. Tests: `test_adversarial_variant_does_not_block_…`, `test_dangling_lineage_…` |
| 5 | Leakage checker independence | It independently re-derived exact-text, scam-domain and near-duplicate leakage, but trusted `campaign_id` for lineage. **Defect:** a synthetic child and its seed in different splits with different campaign ids passed. Scammer-id leakage wasn't checked. | H | Lineage is now checked directly from `seed_id`/`parent_id`, the adversarial parent split is verified, and the scammer-id check was added. Test: `test_leakage_checker_catches_lineage_…` |
| 6 | `promotional` vs `legitimate` | Already separate gold labels. The mapping to verdicts wasn't written down anywhere. | L | `ACCEPTABLE_VERDICTS` in `schema.py` and §2 of the guidelines: promotional → `NO_STRONG_SIGNALS`/`UNCLEAR`; a `LIKELY_SCAM` on promotional is a false alarm reported as its own slice. |
| 7 | Licence/provenance fail safely | **Defect:** `licence` was free text. `"Unknown"`, `"TBD"`, `"free"` and `""` with `licence_verified: true` all counted as releasable. **Defect:** consent licences weren't tied to donations. **Defect:** `registered_domain` wasn't checked against the URL, so a typo silently changed grouping. **Defect:** an adversarial variant could claim to be a real donation. | H | Accepted-licence allow-list (fails closed); `consent-vN` only for donations and required for them; the URL host must match `registered_domain`; `adversarial` requires `source_type: synthetic`. Tests: four schema tests |
| 8 | Misleading reports on empty or tiny data | **Defect:** κ returned **1.0** when both annotators used one identical label; it is actually undefined. A 5-item report looked as authoritative as a 5,000-item one. Empty manifests were already handled ("No items"). | M | κ now returns undefined in that case, a caution is added below 30 pairs, and a small-dataset banner appears below 50 gold items. Tests: `test_kappa_is_undefined_…`, `test_tiny_dataset_…`, `test_empty_manifest_…` (this one passed before the fix and is kept as a guard) |
| 9 | Unflagged split imbalance | **Defect:** the split stratifies by label × language only, and the report showed counts without warnings. Categories could be entirely absent from dev/test unnoticed. | M | "Split balance warnings" now cover empty splits, label/category combinations absent from dev or test, and label share > 15 points off the overall share (splits ≥ 20 items). Test: `test_report_flags_category_missing_…` |
| 10 | Identical text, different gold labels | **Defect:** not detected. | M | Validation warning "conflicting gold labels for identical text". Test: `test_conflicting_gold_labels_…` |

### False-merge risks that remain (items wrongly grouped together)

- Different senders using the same boilerplate (row 1). This is deliberate and errs on the safe side, at a cost to balance.
- Chaining through intermediate messages (row 3). Flagged, not prevented.
- Scam domains on a shared platform missing from `SHARED_PLATFORM_DOMAINS`. The list is hand-maintained; check `linked_by_domain` entries in the review file.
- A genuinely shared scammer number used by two crews: rare, and accepted.

### Missed-duplicate risks that remain (related items not grouped; these cause leakage)

- **Translations and paraphrases of a real campaign** (English vs. Hinglish scored 0.17) are only linked if they share a scam domain or a scammer ID. Mitigation: record `scammer_ids` at intake (new field, linked dataset-wide by a keyed hash).
- **Domain rotation:** the same script on fresh domains with different wording.
- **Scams that use only a shared platform** (e.g. `t.me`) and no scammer ID.
- **Redaction differences:** placeholders are normalised, but a redactor who leaves a name in one copy lowers similarity slightly.
- **Pairs in the 0.4–0.6 band** stay separate until a reviewer decides on them.

### Not changed, and why

- **Thresholds 0.6 and 0.4:** no labelled duplicate pairs exist yet to tune them against. Tune once the pilot's review decisions provide them.
- **O(n²) similarity:** fine below about 5k items.
- **κ uses annotation order:** correct while two fixed people annotate, as in the pilot design.

## C. Test results after the audit

`50 passed`: 21 original, 19 audit regression tests (18 failed before their fixes, plus 1 guard that already
passed), and 10 pilot-workflow tests.
