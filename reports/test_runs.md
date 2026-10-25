# Test-split run log

Every evaluation on a `test` split is logged here (PLAN.md §5 step 9). No tuning after viewing test results.

| Date | Data | Split | Systems | Rule pack | Notes |
|---|---|---|---|---|---|
| 2026-10-25 | `benchmarks/synthetic` (SYNTHETIC, 114 items) | test (28) | B0, B1, B2, B4 rule-only | rules-2026.10.1 | First run. B2 thresholds 0.3/0.7 were fixed before the run and were not changed afterwards, even though B2 abstained on every item. |
| 2026-10-25 | same | test (28) | same | rules-2026.10.1 | Re-run after fixes found by the **Robustness Lab** on dev+test parents: whitespace collapsing in `parse()` (newlines broke sentence-scoped rules), and the injection pattern adjusted to work on collapsed text. Also fixed: UPI ids ending a sentence were missed by the PII detector, a model result with no label could reach `NO_STRONG_SIGNALS` (found by Hypothesis), and transposition typos in lookalike domains were missed. Test-split headline numbers were unchanged. Because these fixes followed failures seen on dev/test-derived variants, the synthetic robustness figures are further optimistic. |

No real-data test run has happened. The first one requires the pilot (docs/PILOT_READINESS.md).
