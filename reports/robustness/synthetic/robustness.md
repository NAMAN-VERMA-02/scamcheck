# Robustness report

> **SYNTHETIC ADVERSARIAL FIXTURES derived from the synthetic benchmark. They measure consistency of the systems under controlled perturbations, not real-world robustness.**

Generator `mutate-2026.10.1`, seeds [11, 23, 37], 46 parents from dev/test.

| Generated | Excluded (no change) | Label inherited | Needs human review | Human reviewed |
|---|---|---|---|---|
| 1725 | 307 | 1199 | 219 | 0 |

| System | Consistency (meaning-preserving) | Scam → NO_STRONG_SIGNALS flips | Scam detections lost | Seed spread (min–max) |
|---|---|---|---|---|
| B1-rules | 96.8% [95.6–97.6] (1160/1199) | 6.2% [4.5–8.6] (34/544) | 11.0% [8.0–14.9] (35/319) | 96.5–97.0% |
| B2-tfidf-lr ⚠ constant verdict: trivially consistent | 100.0% [99.7–100.0] (1199/1199) | 0.0% [0.0–0.7] (0/544) | n/a | 100.0–100.0% |
| B4-engine | 97.1% [96.0–97.9] (1164/1199) | 0.0% [0.0–0.7] (0/544) | 7.6% [5.5–10.3] (35/463) | 96.8–97.5% |

## Consistency by transform

| Transform | B1-rules | B2-tfidf-lr | B4-engine |
|---|---|---|---|
| casing | 100.0% [97.3–100.0] (138/138) | 100.0% [97.3–100.0] (138/138) | 100.0% [97.3–100.0] (138/138) |
| char_spacing | 91.3% [85.4–95.0] (126/138) | 100.0% [97.3–100.0] (138/138) | 93.5% [88.1–96.5] (129/138) |
| confusables | 100.0% [97.3–100.0] (137/137) | 100.0% [97.3–100.0] (137/137) | 100.0% [97.3–100.0] (137/137) |
| fullwidth_nfkc | 100.0% [97.3–100.0] (138/138) | 100.0% [97.3–100.0] (138/138) | 100.0% [97.3–100.0] (138/138) |
| hinglish_spelling | 91.2% [81.1–96.2] (52/57) | 100.0% [93.7–100.0] (57/57) | 91.2% [81.1–96.2] (52/57) |
| punctuation | 92.8% [87.2–96.0] (128/138) | 100.0% [97.3–100.0] (138/138) | 92.8% [87.2–96.0] (128/138) |
| script_mix_devanagari | 92.6% [82.5–97.1] (50/54) | 100.0% [93.4–100.0] (54/54) | 92.6% [82.5–97.1] (50/54) |
| typo | 92.0% [85.0–95.9] (92/100) | 100.0% [96.3–100.0] (100/100) | 93.0% [86.2–96.6] (93/100) |
| url_defang_style | 100.0% [85.7–100.0] (23/23) | 100.0% [85.7–100.0] (23/23) | 100.0% [85.7–100.0] (23/23) |
| whitespace | 100.0% [97.3–100.0] (138/138) | 100.0% [97.3–100.0] (138/138) | 100.0% [97.3–100.0] (138/138) |
| zero_width | 100.0% [97.3–100.0] (138/138) | 100.0% [97.3–100.0] (138/138) | 100.0% [97.3–100.0] (138/138) |

## Consistency by language

| Language | B1-rules | B2-tfidf-lr | B4-engine |
|---|---|---|---|
| english | 97.6% [95.9–98.6] (528/541) | 100.0% [99.3–100.0] (541/541) | 97.8% [96.2–98.7] (529/541) |
| hinglish | 96.0% [94.3–97.3] (632/658) | 100.0% [99.4–100.0] (658/658) | 96.5% [94.8–97.7] (635/658) |

## Meaning-changing transforms (verdicts only; labels await human review)

- B1-rules / code_switch: LIKELY_SCAM 15, NO_STRONG_SIGNALS 33, UNCLEAR 3
- B1-rules / drop_link: LIKELY_SCAM 9, NO_STRONG_SIGNALS 9, UNCLEAR 12
- B1-rules / prompt_injection: LIKELY_SCAM 36, UNCLEAR 102
- B2-tfidf-lr / code_switch: UNCLEAR 51
- B2-tfidf-lr / drop_link: UNCLEAR 30
- B2-tfidf-lr / prompt_injection: UNCLEAR 138
- B4-engine / code_switch: LIKELY_SCAM 21, UNCLEAR 30
- B4-engine / drop_link: LIKELY_SCAM 9, UNCLEAR 21
- B4-engine / prompt_injection: LIKELY_SCAM 51, UNCLEAR 87
