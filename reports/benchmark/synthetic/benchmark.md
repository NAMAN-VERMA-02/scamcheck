# Benchmark report — split `test`

> **SYNTHETIC FIXTURE RESULTS. Every item was hand-written by the maintainer who also wrote the rule pack. These numbers show the pipeline works; they are optimistic by construction and are NOT real-world detection performance.**

Rates are point estimates with Wilson 95% intervals and counts. Lower is better for false alarms, dangerous misses and unclear rate; higher is better for scam recall. † marks n < 30: counts only, not a finding (docs/EVALUATION_PROTOCOL.md §5).

| System | Scam recall | Dangerous misses | False alarms (legitimate) | Unclear (non-ambiguous) |
|---|---|---|---|---|
| B0-unclear | 0.0% [0.0–24.2] (0/12) † | 0.0% [0.0–24.2] (0/12) † | 0.0% [0.0–24.2] (0/12) † | 100.0% [87.1–100.0] (26/26) † |
| B0-scam | 100.0% [75.8–100.0] (12/12) † | 0.0% [0.0–24.2] (0/12) † | 100.0% [75.8–100.0] (12/12) † | 0.0% [0.0–12.9] (0/26) † |
| B1-rules | 41.7% [19.3–68.0] (5/12) † | 25.0% [8.9–53.2] (3/12) † | 0.0% [0.0–24.2] (0/12) † | 15.4% [6.2–33.5] (4/26) † |
| B2-tfidf-lr | 0.0% [0.0–24.2] (0/12) † | 0.0% [0.0–24.2] (0/12) † | 0.0% [0.0–24.2] (0/12) † | 100.0% [87.1–100.0] (26/26) † |
| B4-engine | 75.0% [46.8–91.1] (9/12) † | 0.0% [0.0–24.2] (0/12) † | 0.0% [0.0–24.2] (0/12) † | 65.4% [46.2–80.6] (17/26) † |

B2-tfidf-lr threshold-free ranking: ROC-AUC 0.9702 (12 scam vs 14 non-scam). Its verdicts use thresholds fixed before evaluation (0.3/0.7); an AUC well above 0.5 with an all-UNCLEAR verdict row means the scores are informative but compressed, not tuned.

## Paired comparisons on primary metrics (B4 − other; negative favours B4)

- B4-engine vs B1-rules (exploratory, 95% paired campaign bootstrap): dangerous_miss_rate -25.0 pts [-50.0, +0.0] → inconclusive; false_alarm_rate_legitimate +0.0 pts [+0.0, +0.0] → inconclusive
- B4-engine vs B2-tfidf-lr (exploratory, 95% paired campaign bootstrap): dangerous_miss_rate +0.0 pts [+0.0, +0.0] → inconclusive; false_alarm_rate_legitimate +0.0 pts [+0.0, +0.0] → inconclusive
- B4-engine vs B3-llm (primary): not run — no model configured.

## Campaign-bootstrap intervals (headline metrics)

- B0-unclear (28 campaigns, 2000 resamples, seed 13): scam_recall [0.0–0.0]; dangerous_miss_rate [0.0–0.0]; false_alarm_rate_legitimate [0.0–0.0]; unclear_rate_non_ambiguous [100.0–100.0]
- B0-scam (28 campaigns, 2000 resamples, seed 13): scam_recall [100.0–100.0]; dangerous_miss_rate [0.0–0.0]; false_alarm_rate_legitimate [100.0–100.0]; unclear_rate_non_ambiguous [0.0–0.0]
- B1-rules (28 campaigns, 2000 resamples, seed 13): scam_recall [13.3–70.0]; dangerous_miss_rate [0.0–50.0]; false_alarm_rate_legitimate [0.0–0.0]; unclear_rate_non_ambiguous [3.7–29.6]
- B2-tfidf-lr (28 campaigns, 2000 resamples, seed 13): scam_recall [0.0–0.0]; dangerous_miss_rate [0.0–0.0]; false_alarm_rate_legitimate [0.0–0.0]; unclear_rate_non_ambiguous [100.0–100.0]
- B4-engine (28 campaigns, 2000 resamples, seed 13): scam_recall [45.5–100.0]; dangerous_miss_rate [0.0–0.0]; false_alarm_rate_legitimate [0.0–0.0]; unclear_rate_non_ambiguous [46.2–83.3]

## By language

| System | Language | Scam recall | Dangerous misses | False alarms | Unclear |
|---|---|---|---|---|---|
| B0-unclear | english | 0.0% [0.0–39.0] (0/6) † | 0.0% [0.0–39.0] (0/6) † | 0.0% [0.0–39.0] (0/6) † | 100.0% [77.2–100.0] (13/13) † |
| B0-unclear | hinglish | 0.0% [0.0–39.0] (0/6) † | 0.0% [0.0–39.0] (0/6) † | 0.0% [0.0–39.0] (0/6) † | 100.0% [77.2–100.0] (13/13) † |
| B0-unclear | gap (hi − en) | +0.0 pts | +0.0 pts | +0.0 pts | +0.0 pts |
| B0-scam | english | 100.0% [61.0–100.0] (6/6) † | 0.0% [0.0–39.0] (0/6) † | 100.0% [61.0–100.0] (6/6) † | 0.0% [0.0–22.8] (0/13) † |
| B0-scam | hinglish | 100.0% [61.0–100.0] (6/6) † | 0.0% [0.0–39.0] (0/6) † | 100.0% [61.0–100.0] (6/6) † | 0.0% [0.0–22.8] (0/13) † |
| B0-scam | gap (hi − en) | +0.0 pts | +0.0 pts | +0.0 pts | +0.0 pts |
| B1-rules | english | 33.3% [9.7–70.0] (2/6) † | 33.3% [9.7–70.0] (2/6) † | 0.0% [0.0–39.0] (0/6) † | 15.4% [4.3–42.2] (2/13) † |
| B1-rules | hinglish | 50.0% [18.8–81.2] (3/6) † | 16.7% [3.0–56.4] (1/6) † | 0.0% [0.0–39.0] (0/6) † | 15.4% [4.3–42.2] (2/13) † |
| B1-rules | gap (hi − en) | +16.7 pts | -16.7 pts | +0.0 pts | +0.0 pts |
| B2-tfidf-lr | english | 0.0% [0.0–39.0] (0/6) † | 0.0% [0.0–39.0] (0/6) † | 0.0% [0.0–39.0] (0/6) † | 100.0% [77.2–100.0] (13/13) † |
| B2-tfidf-lr | hinglish | 0.0% [0.0–39.0] (0/6) † | 0.0% [0.0–39.0] (0/6) † | 0.0% [0.0–39.0] (0/6) † | 100.0% [77.2–100.0] (13/13) † |
| B2-tfidf-lr | gap (hi − en) | +0.0 pts | +0.0 pts | +0.0 pts | +0.0 pts |
| B4-engine | english | 66.7% [30.0–90.3] (4/6) † | 0.0% [0.0–39.0] (0/6) † | 0.0% [0.0–39.0] (0/6) † | 69.2% [42.4–87.3] (9/13) † |
| B4-engine | hinglish | 83.3% [43.6–97.0] (5/6) † | 0.0% [0.0–39.0] (0/6) † | 0.0% [0.0–39.0] (0/6) † | 61.5% [35.5–82.3] (8/13) † |
| B4-engine | gap (hi − en) | +16.7 pts | +0.0 pts | +0.0 pts | -7.7 pts |

## False alarms by legitimate category (LIKELY_SCAM on non-scam items)

| Category | B0-unclear | B0-scam | B1-rules | B2-tfidf-lr | B4-engine |
|---|---|---|---|---|---|
| bank_txn_alert | 0.0% [0.0–56.1] (0/3) † | 100.0% [43.9–100.0] (3/3) † | 0.0% [0.0–56.1] (0/3) † | 0.0% [0.0–56.1] (0/3) † | 0.0% [0.0–56.1] (0/3) † |
| delivery_notification | 0.0% [0.0–65.8] (0/2) † | 100.0% [34.2–100.0] (2/2) † | 0.0% [0.0–65.8] (0/2) † | 0.0% [0.0–65.8] (0/2) † | 0.0% [0.0–65.8] (0/2) † |
| otp | 0.0% [0.0–65.8] (0/2) † | 100.0% [34.2–100.0] (2/2) † | 0.0% [0.0–65.8] (0/2) † | 0.0% [0.0–65.8] (0/2) † | 0.0% [0.0–65.8] (0/2) † |
| payment_confirmation | 0.0% [0.0–79.3] (0/1) † | 100.0% [20.6–100.0] (1/1) † | 0.0% [0.0–79.3] (0/1) † | 0.0% [0.0–79.3] (0/1) † | 0.0% [0.0–79.3] (0/1) † |
| personal | 0.0% [0.0–65.8] (0/2) † | 100.0% [34.2–100.0] (2/2) † | 0.0% [0.0–65.8] (0/2) † | 0.0% [0.0–65.8] (0/2) † | 0.0% [0.0–65.8] (0/2) † |
| service_account | 0.0% [0.0–65.8] (0/2) † | 100.0% [34.2–100.0] (2/2) † | 0.0% [0.0–65.8] (0/2) † | 0.0% [0.0–65.8] (0/2) † | 0.0% [0.0–65.8] (0/2) † |
| marketing | 0.0% [0.0–65.8] (0/2) † | 100.0% [34.2–100.0] (2/2) † | 0.0% [0.0–65.8] (0/2) † | 0.0% [0.0–65.8] (0/2) † | 0.0% [0.0–65.8] (0/2) † |

## Confusion matrices (gold label × verdict)

### B0-unclear

| Gold \ verdict | LIKELY_SCAM | UNCLEAR | NO_STRONG_SIGNALS |
|---|---|---|---|
| ambiguous | 0 | 2 | 0 |
| legitimate | 0 | 12 | 0 |
| promotional | 0 | 2 | 0 |
| scam | 0 | 12 | 0 |

### B0-scam

| Gold \ verdict | LIKELY_SCAM | UNCLEAR | NO_STRONG_SIGNALS |
|---|---|---|---|
| ambiguous | 2 | 0 | 0 |
| legitimate | 12 | 0 | 0 |
| promotional | 2 | 0 | 0 |
| scam | 12 | 0 | 0 |

### B1-rules

| Gold \ verdict | LIKELY_SCAM | UNCLEAR | NO_STRONG_SIGNALS |
|---|---|---|---|
| ambiguous | 0 | 0 | 2 |
| legitimate | 0 | 0 | 12 |
| promotional | 0 | 0 | 2 |
| scam | 5 | 4 | 3 |

### B2-tfidf-lr

| Gold \ verdict | LIKELY_SCAM | UNCLEAR | NO_STRONG_SIGNALS |
|---|---|---|---|
| ambiguous | 0 | 2 | 0 |
| legitimate | 0 | 12 | 0 |
| promotional | 0 | 2 | 0 |
| scam | 0 | 12 | 0 |

### B4-engine

| Gold \ verdict | LIKELY_SCAM | UNCLEAR | NO_STRONG_SIGNALS |
|---|---|---|---|
| ambiguous | 0 | 2 | 0 |
| legitimate | 0 | 12 | 0 |
| promotional | 0 | 2 | 0 |
| scam | 9 | 3 | 0 |

## B4 errors (dangerous misses and false alarms)

- none

## Configuration

```json
{
  "data_label": "SYNTHETIC FIXTURE RESULTS. Every item was hand-written by the maintainer who also wrote the rule pack. These numbers show the pipeline works; they are optimistic by construction and are NOT real-world detection performance.",
  "synthetic_only": true,
  "dataset": {
    "path": "benchmarks/synthetic/items.grouped.jsonl",
    "sha256": "dd33ee3a5d0045c17a5067ed4b61af0337d811b1747f4a5089ff7e3fb78c3b7f"
  },
  "manifest": {
    "path": "benchmarks/synthetic/manifest.json",
    "sha256": "d355732207d137e6182ca15e387c17efbc4dd77facbb563ac9d706a8c5485f1e",
    "params": {
      "ratios": {
        "train": 0.6,
        "dev": 0.15,
        "test": 0.25
      },
      "seed": 13,
      "allow_synthetic_in_test": true
    },
    "counts": {
      "test": 28,
      "train": 68,
      "dev": 18
    }
  },
  "split": "test",
  "seed": 13,
  "n_train": 64,
  "n_evaluated": 28,
  "versions": {
    "engine": "engine-0.2.0",
    "rules": "rules-2026.10.1",
    "urls": "urls-2026.10.1",
    "prompt": "zero-shot-v1:b413ed4f7af7",
    "python": "3.12.10",
    "scikit-learn": "1.9.1"
  },
  "model": {
    "model_id": null,
    "note": "no model configured; B3 not run, B4 in rule-only mode"
  }
}
```
