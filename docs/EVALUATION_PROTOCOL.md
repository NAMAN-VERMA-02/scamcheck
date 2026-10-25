# Evaluation protocol (pre-registered, version 1, 2026-10-25)

This protocol is fixed **before** any real-data evaluation. It turns PLAN.md §5–§8 into rules that a run either
follows or records as a deviation. Changing anything below after real data has been seen creates version 2. The
change and its reason are logged in `reports/test_runs.md`, and version 2 needs a test set that version 1 never
touched.

Status: no real data exists, so no run has been made under this protocol. The synthetic reports in `reports/` are
pipeline checks and are out of scope for every rule here except §7.

## 1. Research questions

| ID | Question | Kind |
|---|---|---|
| RQ1 | On real English and Hinglish messages, what are B4's dangerous-miss rate (scams → `NO_STRONG_SIGNALS`) and false-alarm rate (legitimate → `LIKELY_SCAM`)? | primary, descriptive |
| RQ2 | Does B4 differ from B3 (zero-shot LLM) on those two rates? | primary, comparative |
| RQ3 | How large is the Hinglish − English gap on RQ1's rates and on scam recall? | secondary, pre-specified |
| RQ4 | Do RQ1's rates hold on campaigns collected after the training period (temporal hold-out)? | secondary, pre-specified |
| RQ5 | How consistent are verdicts under mutation families that a human review has validated as meaning-preserving? | secondary, pre-specified |

Everything else (per-channel, per-script, has-URL, AUC, B4 vs B1/B2) is **exploratory**. It is reported as such
and never used to support a claim.

## 2. Metrics

- **Primary:** dangerous-miss rate on `scam`, and false-alarm rate pooled over `legitimate`. Lower is better for
  both. `promotional` is a separate slice and is not pooled into either.
- **Secondary:** scam recall (`LIKELY_SCAM` | scam); `UNCLEAR` rate per class and on all non-ambiguous items;
  false-alarm rate per legitimate category; RQ3 gaps; RQ4 rates on the temporal test split.
- **Guard against abstention gaming:** a system that lowers either primary rate by answering `UNCLEAR` must also
  show its `UNCLEAR` rate. A primary-metric improvement that comes with a higher non-ambiguous `UNCLEAR` rate is
  reported as a trade-off, not an improvement.
- `ambiguous` items are excluded from the primary metrics. Their `UNCLEAR` rate is reported.
- Unit: the item. Uncertainty: a Wilson 95% interval for every rate, plus a campaign-level bootstrap (2,000
  resamples, seed 13) for primary metrics when the split has at least 20 campaigns. All of this is implemented in
  `src/scamcheck/eval/metrics.py`.

## 3. Thresholds and frozen configuration (development only)

- The engine (B4) has **no tunable thresholds**. Its verdict comes from the rule pack and the combiner. The rule
  pack, combiner and prompt are frozen by `RULE_PACK_VERSION`, `ENGINE_VERSION`, `PROMPT_ID` and the git commit, all
  of which `scamcheck benchmark` records.
- B2's thresholds are the only tunable values. On real data they are chosen on **`dev` only** by this fixed rule:
  maximise dev scam recall subject to dev false-alarm rate ≤ 5% and dev dangerous-miss rate ≤ 3%. If no threshold
  pair meets both, keep the pre-set 0.3/0.7 and record "infeasible on dev".
- B2's current 0.3/0.7 were set before any evaluation. They are **not** changed in response to the synthetic
  results already seen.
- Before a test run, append to `reports/test_runs.md`: protocol version, commit, dataset and manifest SHA-256,
  thresholds and their dev evidence, model id and prompt id.

## 4. Test-set restrictions

1. The test split contains only real, releasable items (`allowed_in_test`). `--allow-synthetic-in-test` manifests
   are never used for results.
2. The manifest (with its SHA-256) is committed before the first test run. `check-leakage` must pass.
   `scamcheck benchmark` refuses otherwise.
3. **Temporal hold-out is preferred** (`scamcheck split --temporal-cutoff`). Use it when the data spans at least
   three months and the post-cutoff campaigns meet the §5 minimums. The cutoff is chosen from the date distribution
   alone, before any labels or results are looked at. Otherwise use the random group split and say so. Both are
   fixed before the run.
4. At most **two** test evaluations per protocol version (PLAN milestones M4 and M7), each logged. No rule,
   threshold, prompt or code change may be motivated by a test result. A change after a test run means a new
   protocol version and a new, unseen test set (for example the next temporal window).
5. Errors found on test may be listed and tagged (PLAN §6.4). Fixing them is allowed only for the next version, and
   `label_noise` items go back to adjudication rather than into the code.

## 5. Subgroups and sample size

Pre-specified subgroups: language (RQ3), legitimate category, scam category, temporal side (RQ4). Exploratory:
channel, script, has-URL, code-mix bin.

- Every subgroup is reported with its counts. A rate is **interpretable only when n ≥ 30** (`interpretable` in the
  JSON, † in the markdown). Below that, report counts only and draw no conclusion.
- Minimums before **any** real-data claim (the PLAN M2 criteria): ≥ 120 English scams and ≥ 120 Hinglish scams in
  test; ≥ 75 legitimate items in each of at least 4 legitimate categories. With fewer, the run is a **pilot report**:
  descriptive only, no claims.
- What these sizes can show (Wilson 95%, computed with the project's own `wilson()`):
  - With 0 errors, the upper bound is ≤ 5% from n = 73, ≤ 3% from n = 125, and ≤ 2% from n = 189. Supporting
    "dangerous-miss rate ≤ 3%" needs at least 125 scams **with zero misses**. One miss in 125 gives an upper bound
    of 4.4%.
  - Two false alarms in 75 legitimate items give an upper bound of 9.2%, so a per-category "≤ 5%" claim needs more
    than 75 items as soon as any false alarm occurs.
  - At 120 scams per language and recall near 85%, each language's interval is about ±6.4 points and the gap's is
    about ±9 points. **Language gaps smaller than about 9 points will be inconclusive at the M2 minimum**; at 200
    per language, about 7 points.

## 6. Interpreting results

Each target from PLAN §8 M4 is judged against its interval, not its point estimate:

| Outcome | Rule (error rates; mirrored for recall) | Wording allowed |
|---|---|---|
| Meets target | whole 95% interval below the target | "meets the target on this test set" |
| Misses target | whole 95% interval above the target | "does not meet the target" |
| **Inconclusive** | interval contains the target | "inconclusive at this sample size". Report the interval; never round it to a pass |

Comparisons use the **paired campaign bootstrap** of the difference (`paired_difference` in `metrics.py`). B4 vs B3
is the only primary comparison, at 97.5% per metric (Bonferroni over the two primary metrics). B4 vs B1/B2 are
exploratory at 95%. A system is "lower" only when the interval excludes 0. Otherwise the result is
"inconclusive", **never "equivalent"**. If B3 is not beaten, PLAN §8 applies: publish the benchmark, make no product
claim.

## 7. Reporting rules (all runs, including synthetic)

- Data provenance appears at the top of every report. Synthetic results are never put in a headline, a résumé or a
  comparison with other products.
- No probability or "confidence" is reported for any verdict. AUC is reported only as a ranking diagnostic for
  scored baselines.
- Deviations from this protocol are listed in `reports/test_runs.md` with a reason, next to the run they affect.
