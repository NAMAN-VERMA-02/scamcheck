# Robustness review guideline (mr1)

The Robustness Lab marks 11 transform families as "meaning-preserving by design". That label is a **hypothesis**.
Until people check it, no variant inherits its parent's label, and every label-based robustness number is n/a.

## Who reviews

Anyone who reads both English and romanised Hinglish fluently. They must not have written the transform code or
the parent messages (on the synthetic set that excludes the maintainer, who wrote both). Two reviewers per sheet is
better: disagreements become `review_conflict` and give no label.

## Workflow

```bash
D=benchmarks/synthetic
scamcheck review-sheet $D/items.grouped.jsonl --variants reports/robustness/synthetic/variants.jsonl \
    --out review/sheet-R1.csv --per-family 30 --seed 1
# reviewer fills the sheet (Excel: save as "CSV UTF-8")
scamcheck review-import --sheet review/sheet-R1.csv --variants reports/robustness/synthetic/variants.jsonl \
    --reviewer R1 --out review/decisions.jsonl
scamcheck robustness $D/items.grouped.jsonl --manifest $D/manifest.json \
    --out-dir reports/robustness/synthetic --reviews review/decisions.jsonl
```

- The sheet samples up to `--per-family` not-yet-reviewed variants per family, seeded, so it is reproducible.
- It shows the parent and the variant, with invisible characters written as `⟨U+200B⟩`, and **does not show the
  parent's label**.
- Cells are escaped against spreadsheet formula injection.
- Import is all-or-nothing. It rejects unknown ids, invalid values, a missing label on a meaning-changing family,
  identifiers in notes, and a reviewer re-importing the same variant.

## What to decide per row

| Column | Values | Rule |
|---|---|---|
| `meaning_preserved` | `yes` / `no` / `unsure` | `yes` only if a typical recipient would understand the variant exactly as the parent: same request, same sender claim, same urgency, same link. Odd spelling or spacing is fine if it is still readable. `unsure` when you cannot tell |
| `label` | blank, or `scam` / `legitimate` / `promotional` / `ambiguous` | Required for `prompt_injection`, `drop_link` and `code_switch` unless `unsure`. For other families, fill it only when meaning changed. Label what the **variant** says, judged by `docs/ANNOTATION_GUIDELINES.md` |
| `note` | free text | No names, numbers or other identifiers |

## How decisions are used (`src/scamcheck/eval/review.py`)

| Situation | Status | Label |
|---|---|---|
| Not reviewed, family not validated | `unvalidated_family` | none |
| Not reviewed, family **validated** (≥ 30 reviewed, all `yes`) | `label_inherited` | parent's |
| Not reviewed, meaning-changing family | `needs_human_review` | none |
| Reviewed `yes` | `human_reviewed` | reviewer's label if given, else parent's |
| Reviewed `no`/`unsure` with a label | `human_reviewed` | reviewer's |
| Reviewed `no`/`unsure` without a label | `reviewed_no_label` | none |
| Reviewers disagree | `review_conflict` | none |

- A single `no` in a family marks it `meaning_change_observed`. From then on, only individually reviewed variants of
  that family count, and the transform should be fixed or moved to the meaning-changing class.
- 30/30 `yes` bounds the family's meaning-change rate below about 11% (Wilson 95%, the report prints the bound). It
  does not prove the rate is zero.
- Verdict consistency is label-free and is always reported. It is marked **provisional** while any contributing
  family is unvalidated, and excludes variants reviewed as `no`/`unsure`.
