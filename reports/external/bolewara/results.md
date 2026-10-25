# External-author check

> **EXTERNAL-AUTHOR SYNTHETIC CHECK. Hand-written by the dataset author, not by the rule author; still synthetic and small. Not real-world accuracy.**

`bolewara/hinglish-scam-text-dataset` @ `743799229923fc80fd7e9f2c764b5e9bd4ab3c9a`, 38 Hinglish rows in 38 campaigns. Frozen code `87b0e04c16c6` (commit 1f0e2993930a3afa8883805bb0db727f614b1b1d). † = n < 30, counts only.

| System | Scam recall | Dangerous misses | False alarms (legitimate) | Unclear (all) |
|---|---|---|---|---|
| B0-unclear | 0/16 (0.0%, 95% CI 0.0–19.4) † | 0/16 (0.0%, 95% CI 0.0–19.4) † | 0/22 (0.0%, 95% CI 0.0–14.9) † | 38/38 (100.0%, 95% CI 90.8–100.0) |
| B0-scam | 16/16 (100.0%, 95% CI 80.6–100.0) † | 0/16 (0.0%, 95% CI 0.0–19.4) † | 22/22 (100.0%, 95% CI 85.1–100.0) † | 0/38 (0.0%, 95% CI 0.0–9.2) |
| B1-rules | 1/16 (6.2%, 95% CI 1.1–28.3) † | 10/16 (62.5%, 95% CI 38.6–81.5) † | 0/22 (0.0%, 95% CI 0.0–14.9) † | 5/38 (13.2%, 95% CI 5.8–27.3) |
| B2-tfidf-lr | 0/16 (0.0%, 95% CI 0.0–19.4) † | 0/16 (0.0%, 95% CI 0.0–19.4) † | 0/22 (0.0%, 95% CI 0.0–14.9) † | 38/38 (100.0%, 95% CI 90.8–100.0) |
| B4-engine | 4/16 (25.0%, 95% CI 10.2–49.5) † | 0/16 (0.0%, 95% CI 0.0–19.4) † | 0/22 (0.0%, 95% CI 0.0–14.9) † | 34/38 (89.5%, 95% CI 75.9–95.8) |
| B3-llm | 16/16 (100.0%, 95% CI 80.6–100.0) † | 0/16 (0.0%, 95% CI 0.0–19.4) † | 0/22 (0.0%, 95% CI 0.0–14.9) † | 2/38 (5.3%, 95% CI 1.5–17.3) |
| B4-engine+llm | 16/16 (100.0%, 95% CI 80.6–100.0) † | 0/16 (0.0%, 95% CI 0.0–19.4) † | 0/22 (0.0%, 95% CI 0.0–14.9) † | 2/38 (5.3%, 95% CI 1.5–17.3) |

## Paired comparisons (first − second, campaign bootstrap; negative favours the first)

- B4-engine vs B1-rules (exploratory, 95%): dangerous_miss_rate -62.5 pts [-86.7, -36.8] → a_lower; false_alarm_rate_legitimate +0.0 pts [+0.0, +0.0] → inconclusive
- B4-engine vs B2-tfidf-lr (exploratory, 95%): dangerous_miss_rate +0.0 pts [+0.0, +0.0] → inconclusive; false_alarm_rate_legitimate +0.0 pts [+0.0, +0.0] → inconclusive
- B4-engine+llm vs B3-llm (primary, 97.5%): dangerous_miss_rate +0.0 pts [+0.0, +0.0] → inconclusive; false_alarm_rate_legitimate +0.0 pts [+0.0, +0.0] → inconclusive
- B4-engine vs B3-llm (exploratory, 95%): dangerous_miss_rate +0.0 pts [+0.0, +0.0] → inconclusive; false_alarm_rate_legitimate +0.0 pts [+0.0, +0.0] → inconclusive

## Model

- `openai-compatible:qwen2.5:3b` (digest `357c53fb659c5076de1`), prompt `zero-shot-v1:b413ed4f7af7`, timeout 180.0 s, endpoint local: True
- 38 model calls, shared by B3 and B4+llm; statuses: ok 38
- wall time for all systems: 356.0 s

## B4-engine misses and false alarms (row index, signals that fired)

- row 55 (scam): UNCLEAR; signals: R-PRIZE-CLAIM
- row 589 (scam): UNCLEAR; signals: none
- row 612 (scam): UNCLEAR; signals: none
- row 1116 (scam): UNCLEAR; signals: none
- row 1150 (scam): UNCLEAR; signals: none
- row 1721 (scam): UNCLEAR; signals: none
- row 1757 (scam): UNCLEAR; signals: R-PRIZE-CLAIM
- row 1863 (scam): UNCLEAR; signals: R-PERSONAL-PAYMENT
- row 2007 (scam): UNCLEAR; signals: none
- row 2080 (scam): UNCLEAR; signals: R-ACCOUNT-THREAT, R-URGENCY
- row 2899 (scam): UNCLEAR; signals: none
- row 3467 (scam): UNCLEAR; signals: R-URGENCY

## B4-engine+llm misses and false alarms (row index, signals that fired)

- none
