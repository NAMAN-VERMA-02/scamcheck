"""Benchmark metrics with honest uncertainty.

Every rate carries its numerator, denominator and a Wilson 95% interval. Headline metrics additionally get a
campaign-level bootstrap interval when the evaluated rows span at least MIN_BOOTSTRAP_CAMPAIGNS campaigns;
items of one campaign are not independent, so resampling items would understate the uncertainty.
"""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Callable

from ..engine.models import VERDICTS

Z95 = 1.959963984540054
MIN_BOOTSTRAP_CAMPAIGNS = 20
BOOTSTRAP_RESAMPLES = 2000
MIN_INTERPRETABLE_N = 30   # docs/EVALUATION_PROTOCOL.md §5
PRIMARY = ("dangerous_miss_rate", "false_alarm_rate_legitimate")  # protocol §2; lower is better for both


@dataclass(frozen=True)
class Row:
    id: str
    label: str
    category: str | None
    language: str
    campaign: str
    verdict: str


def wilson(k: int, n: int) -> dict:
    """Rate with Wilson 95% interval. `interpretable` follows docs/EVALUATION_PROTOCOL.md §5: below
    MIN_INTERPRETABLE_N the counts are reported but the rate is not to be read as a finding."""
    if n == 0:
        return {"k": 0, "n": 0, "rate": None, "lo": None, "hi": None, "interpretable": False}
    p = k / n
    denom = 1 + Z95 ** 2 / n
    centre = (p + Z95 ** 2 / (2 * n)) / denom
    half = Z95 * math.sqrt(p * (1 - p) / n + Z95 ** 2 / (4 * n * n)) / denom
    return {"k": k, "n": n, "rate": round(p, 4), "lo": round(max(0.0, centre - half), 4),
            "hi": round(min(1.0, centre + half), 4), "interpretable": n >= MIN_INTERPRETABLE_N}


def auc(scores: list[float], positive: list[bool]) -> dict:
    """ROC-AUC as P(score of a random scam > score of a random non-scam), ties counted half."""
    pos = [s for s, p in zip(scores, positive) if p]
    neg = [s for s, p in zip(scores, positive) if not p]
    if not pos or not neg:
        return {"auc": None, "n_pos": len(pos), "n_neg": len(neg)}
    wins = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return {"auc": round(wins / (len(pos) * len(neg)), 4), "n_pos": len(pos), "n_neg": len(neg)}


def _rate(rows: list[Row], label_pred: Callable[[Row], bool], verdict: str) -> dict:
    sel = [r for r in rows if label_pred(r)]
    return wilson(sum(r.verdict == verdict for r in sel), len(sel))


def _is_legit(r: Row) -> bool:
    return r.label == "legitimate"


def _is_scam(r: Row) -> bool:
    return r.label == "scam"


# name → (rows → (k, n)); used for both the point estimates and the bootstrap.
HEADLINE: dict[str, Callable[[list[Row]], tuple[int, int]]] = {
    "scam_recall": lambda rs: (sum(r.verdict == "LIKELY_SCAM" for r in rs if _is_scam(r)), sum(map(_is_scam, rs))),
    "dangerous_miss_rate": lambda rs: (sum(r.verdict == "NO_STRONG_SIGNALS" for r in rs if _is_scam(r)),
                                       sum(map(_is_scam, rs))),
    "false_alarm_rate_legitimate": lambda rs: (sum(r.verdict == "LIKELY_SCAM" for r in rs if _is_legit(r)),
                                               sum(map(_is_legit, rs))),
    "unclear_rate_non_ambiguous": lambda rs: (sum(r.verdict == "UNCLEAR" for r in rs if r.label != "ambiguous"),
                                              sum(r.label != "ambiguous" for r in rs)),
}


def core(rows: list[Row]) -> dict:
    out = {name: wilson(*fn(rows)) for name, fn in HEADLINE.items()}
    out["false_alarm_rate_promotional"] = _rate(rows, lambda r: r.label == "promotional", "LIKELY_SCAM")
    out["unclear_rate_by_label"] = {lab: _rate(rows, lambda r, lab=lab: r.label == lab, "UNCLEAR")
                                    for lab in sorted({r.label for r in rows})}
    return out


def confusion(rows: list[Row]) -> dict:
    table: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(VERDICTS, 0))
    for r in rows:
        table[r.label][r.verdict] += 1
    return {lab: table[lab] for lab in sorted(table)}


def bootstrap(rows: list[Row], seed: int, resamples: int = BOOTSTRAP_RESAMPLES) -> dict:
    by_campaign: dict[str, list[Row]] = defaultdict(list)
    for r in rows:
        by_campaign[r.campaign].append(r)
    campaigns = sorted(by_campaign)
    if len(campaigns) < MIN_BOOTSTRAP_CAMPAIGNS:
        return {"skipped": f"only {len(campaigns)} campaigns (< {MIN_BOOTSTRAP_CAMPAIGNS}); see Wilson intervals"}
    rng = random.Random(seed)
    samples: dict[str, list[float]] = {name: [] for name in HEADLINE}
    for _ in range(resamples):
        draw = [r for c in rng.choices(campaigns, k=len(campaigns)) for r in by_campaign[c]]
        for name, fn in HEADLINE.items():
            k, n = fn(draw)
            if n:
                samples[name].append(k / n)
    out = {"seed": seed, "resamples": resamples, "campaigns": len(campaigns)}
    for name, vals in samples.items():
        vals.sort()
        out[name] = ({"lo": round(vals[int(0.025 * (len(vals) - 1))], 4),
                      "hi": round(vals[int(0.975 * (len(vals) - 1))], 4)} if vals else None)
    return out


def paired_difference(a: list[Row], b: list[Row], seed: int, resamples: int = BOOTSTRAP_RESAMPLES,
                      level: float = 0.95) -> dict:
    """Paired campaign bootstrap of rate(a) − rate(b) for each primary metric (same items, two systems).

    Conclusion per protocol §6: "a_lower" / "b_lower" only when the interval excludes 0, otherwise
    "inconclusive" — never "equivalent".
    """
    b_by_id = {r.id: r for r in b}
    if {r.id for r in a} != set(b_by_id):
        raise ValueError("paired comparison needs predictions for the same items")
    by_campaign: dict[str, list[tuple[Row, Row]]] = defaultdict(list)
    for r in a:
        by_campaign[r.campaign].append((r, b_by_id[r.id]))
    campaigns = sorted(by_campaign)
    if len(campaigns) < MIN_BOOTSTRAP_CAMPAIGNS:
        return {"skipped": f"only {len(campaigns)} campaigns (< {MIN_BOOTSTRAP_CAMPAIGNS})"}
    rng = random.Random(seed)
    diffs: dict[str, list[float]] = {name: [] for name in PRIMARY}
    for _ in range(resamples):
        draw = [p for c in rng.choices(campaigns, k=len(campaigns)) for p in by_campaign[c]]
        for name in PRIMARY:
            (ka, n), (kb, _) = HEADLINE[name]([x for x, _ in draw]), HEADLINE[name]([y for _, y in draw])
            if n:
                diffs[name].append(ka / n - kb / n)
    tail = (1 - level) / 2
    out: dict = {"seed": seed, "resamples": resamples, "campaigns": len(campaigns), "level": level}
    for name, vals in diffs.items():
        if not vals:
            out[name] = None
            continue
        vals.sort()
        lo, hi = vals[int(tail * (len(vals) - 1))], vals[int((1 - tail) * (len(vals) - 1))]
        (ka, n), (kb, _) = HEADLINE[name](a), HEADLINE[name](b)
        out[name] = {"diff": round((ka - kb) / n, 4) if n else None, "lo": round(lo, 4), "hi": round(hi, 4),
                     "conclusion": "a_lower" if hi < 0 else "b_lower" if lo > 0 else "inconclusive"}
    return out


def summarise(rows: list[Row], seed: int) -> dict:
    by_lang = {lang: core([r for r in rows if r.language == lang]) for lang in sorted({r.language for r in rows})}
    gap = {}
    if {"english", "hinglish"} <= set(by_lang):
        for name in HEADLINE:
            e, h = by_lang["english"][name]["rate"], by_lang["hinglish"][name]["rate"]
            gap[name] = None if e is None or h is None else round(h - e, 4)
    categories = sorted({(r.label, r.category) for r in rows if r.category})
    return {
        "n": len(rows),
        "n_by_label": dict(Counter(r.label for r in rows)),
        "overall": core(rows),
        "by_language": by_lang,
        "language_gap_hinglish_minus_english": gap,
        "false_alarm_by_legit_category": {
            cat: _rate(rows, lambda r, cat=cat: r.category == cat, "LIKELY_SCAM")
            for lab, cat in categories if lab in ("legitimate", "promotional")},
        "scam_recall_by_category": {
            cat: _rate(rows, lambda r, cat=cat: r.category == cat, "LIKELY_SCAM")
            for lab, cat in categories if lab == "scam"},
        "confusion": {"overall": confusion(rows),
                      "by_language": {lang: confusion([r for r in rows if r.language == lang]) for lang in by_lang},
                      "by_category": {cat: confusion([r for r in rows if r.category == cat])
                                      for _, cat in categories}},
        "bootstrap": bootstrap(rows, seed),
    }
