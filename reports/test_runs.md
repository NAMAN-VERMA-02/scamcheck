# Test-split run log

Every evaluation on a `test` split is logged here (PLAN.md §5 step 9). No tuning after viewing test results.

| Date | Data | Split | Systems | Rule pack | Notes |
|---|---|---|---|---|---|
| 2026-10-25 | `benchmarks/synthetic` (SYNTHETIC, 114 items) | test (28) | B0, B1, B2, B4 rule-only | rules-2026.10.1 | First run. B2 thresholds 0.3/0.7 were fixed before the run and were not changed afterwards, even though B2 abstained on every item. |
| 2026-10-25 | same | test (28) | same | rules-2026.10.1 | Re-run after fixes found by the **Robustness Lab** on dev+test parents: whitespace collapsing in `parse()` (newlines broke sentence-scoped rules), and the injection pattern adjusted to work on collapsed text. Also fixed: UPI ids ending a sentence were missed by the PII detector, a model result with no label could reach `NO_STRONG_SIGNALS` (found by Hypothesis), and transposition typos in lookalike domains were missed. Test-split headline numbers were unchanged. Because these fixes followed failures seen on dev/test-derived variants, the synthetic robustness figures are further optimistic. |

| 2026-10-25 | same | test (28) | same | rules-2026.10.1 | Regenerated under evaluation protocol v1, with no change to any rule, threshold, prompt or prediction (verified field by field). Added paired campaign-bootstrap comparisons (B4 − B1 dangerous misses −25.0 pts, [−50.0, 0.0], inconclusive) and n < 30 markers. Robustness report: label inheritance removed until human review validates a family (0 reviews exist), so label-based rows are n/a and the earlier figures are shown as provisional parent-based rows. |

No real-data test run has happened. The first one requires the pilot (docs/PILOT_READINESS.md).

### Deviation 1 — external-author check selection (2026-10-25, before any verdict was computed)

The pre-registered selection rule (Devanagari, or ≥ 2 distinct `HINGLISH_MARKERS`) found 14 scam / 18 legitimate
rows; the dataset card states 35 / 28. Rows carry no language field and are shuffled through the file (checked by
row index and label only), so position cannot be used. A deliberately broad candidate filter (Devanagari, or any
marker including ka/ki/ke/ko/se/ho/ye/na/jo/bhi) finds only 54 rows, fewer than the card's 63.
Revised procedure, decided now: each of the 54 candidates is judged Hinglish or not by reading its text **without
its label**; the confirmed row list is committed before planning; labels come from the dataset unchanged. If the
confirmed set does not match the card, the mismatch is reported and the check runs on the confirmed set only as a
recorded deviation — no rule is tuned towards the card's numbers. No system verdict on these rows has been seen.
| 2026-10-25 | `bolewara/hinglish-scam-text-dataset` @ 743799229923 (SYNTHETIC, external author; Hinglish part 16 scam / 22 legitimate) | all selected rows | B0-unclear, B0-scam, B1-rules, B2-tfidf-lr, B4-engine, B3-llm, B4-engine+llm | frozen 87b0e04c16c6 | **PLANNED** external-author check; model openai-compatible:qwen2.5:3b; label-blind row selection per Deviation 1, not the card counts; plan `reports/external/bolewara/plan.json`. Must be committed before `external-run`; runs once. |
