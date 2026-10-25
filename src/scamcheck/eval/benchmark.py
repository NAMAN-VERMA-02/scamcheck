"""Benchmark runner: every system × the chosen split → metrics, predictions and a markdown report.

The output contains no timestamps, so re-running on the same data, manifest and seed is byte-identical.
"""

from __future__ import annotations

import hashlib
import json
import platform
from importlib.metadata import version
from pathlib import Path
from typing import Optional

from ..data.schema import Item
from ..engine import VERSIONS
from ..engine.llm import PROMPT_ID, ChatAdapter
from .baselines import build_systems
from .metrics import Row, auc, summarise

SYNTHETIC_WARNING = ("SYNTHETIC FIXTURE RESULTS. Every item was hand-written by the maintainer who also wrote the "
                     "rule pack. These numbers show the pipeline works; they are optimistic by construction and are "
                     "NOT real-world detection performance.")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_benchmark(items: list[Item], manifest: dict, *, split: str, seed: int, dataset_path: Path,
                  manifest_path: Path, model: Optional[ChatAdapter] = None) -> dict:
    split_of = {r["id"]: r["split"] for r in manifest["items"]}
    train = [it for it in items if split_of.get(it.id) == "train" and it.gold.label != "ambiguous"]
    evaluated = [it for it in items if split_of.get(it.id) == split]
    if not evaluated:
        raise ValueError(f"no items in split {split!r}")
    if split == "train":
        raise ValueError("refusing to evaluate on the training split")
    systems = build_systems([it.text for it in train], [it.gold.label == "scam" for it in train], seed, model)
    synthetic_only = all(it.is_synthetic for it in items)

    results = {}
    for s in systems:
        rows = [Row(it.id, it.gold.label, it.gold.category, it.language, it.campaign_id or it.id, s.predict(it.text))
                for it in evaluated]
        results[s.name] = {"description": s.description, "config": s.config, "metrics": summarise(rows, seed),
                           "predictions": {r.id: r.verdict for r in rows}}
        if s.score:
            ranked = [it for it in evaluated if it.gold.label != "ambiguous"]
            results[s.name]["ranking_auc"] = auc([s.score(it.text) for it in ranked],
                                                 [it.gold.label == "scam" for it in ranked])
    return {
        "meta": {
            "data_label": SYNTHETIC_WARNING if synthetic_only else "Contains non-synthetic items; see dataset report",
            "synthetic_only": synthetic_only,
            "dataset": {"path": Path(dataset_path).as_posix(), "sha256": file_sha256(dataset_path)},
            "manifest": {"path": Path(manifest_path).as_posix(), "sha256": file_sha256(manifest_path),
                         "params": manifest["params"], "counts": manifest["counts"]},
            "split": split, "seed": seed, "n_train": len(train), "n_evaluated": len(evaluated),
            "versions": {**VERSIONS, "python": platform.python_version(), "scikit-learn": version("scikit-learn")},
            "model": {"model_id": model.model_id, "prompt_id": PROMPT_ID} if model else
                     {"model_id": None, "note": "no model configured; B3 not run, B4 in rule-only mode"},
        },
        "items": [{"id": it.id, "label": it.gold.label, "category": it.gold.category, "language": it.language,
                   **({"text": it.text} if synthetic_only else {})} for it in evaluated],
        "systems": results,
    }


def _pct(m: dict | None) -> str:
    if not m or m.get("rate") is None:
        return "n/a (n=0)"
    return f"{m['rate'] * 100:.1f}% [{m['lo'] * 100:.1f}–{m['hi'] * 100:.1f}] ({m['k']}/{m['n']})"


def to_markdown(res: dict) -> str:
    meta = res["meta"]
    lines = [f"# Benchmark report — split `{meta['split']}`", ""]
    lines += [f"> **{meta['data_label']}**", ""]
    lines += ["Rates are point estimates with Wilson 95% intervals and counts. Lower is better for false alarms, "
              "dangerous misses and unclear rate; higher is better for scam recall.", ""]
    lines += ["| System | Scam recall | Dangerous misses | False alarms (legitimate) | Unclear (non-ambiguous) |",
              "|---|---|---|---|---|"]
    for name, s in res["systems"].items():
        o = s["metrics"]["overall"]
        lines.append(f"| {name} | {_pct(o['scam_recall'])} | {_pct(o['dangerous_miss_rate'])} | "
                     f"{_pct(o['false_alarm_rate_legitimate'])} | {_pct(o['unclear_rate_non_ambiguous'])} |")
    for name, s in res["systems"].items():
        if "ranking_auc" in s:
            r = s["ranking_auc"]
            lines += ["", f"{name} threshold-free ranking: ROC-AUC {r['auc']} ({r['n_pos']} scam vs {r['n_neg']} "
                          f"non-scam). Its verdicts use thresholds fixed before evaluation "
                          f"({s['config']['t_low']}/{s['config']['t_high']}); an AUC well above 0.5 with an "
                          f"all-UNCLEAR verdict row means the scores are informative but compressed, not tuned."]
    lines += ["", "## Campaign-bootstrap intervals (headline metrics)", ""]
    for name, s in res["systems"].items():
        b = s["metrics"]["bootstrap"]
        if "skipped" in b:
            lines.append(f"- {name}: skipped — {b['skipped']}")
        else:
            parts = [f"{k} [{v['lo'] * 100:.1f}–{v['hi'] * 100:.1f}]" for k, v in b.items()
                     if isinstance(v, dict)]
            lines.append(f"- {name} ({b['campaigns']} campaigns, {b['resamples']} resamples, seed {b['seed']}): "
                         + "; ".join(parts))
    lines += ["", "## By language", "", "| System | Language | Scam recall | Dangerous misses | False alarms | Unclear |",
              "|---|---|---|---|---|---|"]
    for name, s in res["systems"].items():
        for lang, m in s["metrics"]["by_language"].items():
            lines.append(f"| {name} | {lang} | {_pct(m['scam_recall'])} | {_pct(m['dangerous_miss_rate'])} | "
                         f"{_pct(m['false_alarm_rate_legitimate'])} | {_pct(m['unclear_rate_non_ambiguous'])} |")
        gap = s["metrics"]["language_gap_hinglish_minus_english"]
        if gap:
            lines.append(f"| {name} | gap (hi − en) | " + " | ".join(
                "n/a" if gap[k] is None else f"{gap[k] * 100:+.1f} pts" for k in
                ("scam_recall", "dangerous_miss_rate", "false_alarm_rate_legitimate", "unclear_rate_non_ambiguous"))
                + " |")
    lines += ["", "## False alarms by legitimate category (LIKELY_SCAM on non-scam items)", "",
              "| Category | " + " | ".join(res["systems"]) + " |", "|---|" + "---|" * len(res["systems"])]
    cats = next(iter(res["systems"].values()))["metrics"]["false_alarm_by_legit_category"]
    for cat in cats:
        lines.append(f"| {cat} | " + " | ".join(_pct(s["metrics"]["false_alarm_by_legit_category"][cat])
                                               for s in res["systems"].values()) + " |")
    lines += ["", "## Confusion matrices (gold label × verdict)", ""]
    for name, s in res["systems"].items():
        lines += [f"### {name}", "", "| Gold \\ verdict | LIKELY_SCAM | UNCLEAR | NO_STRONG_SIGNALS |", "|---|---|---|---|"]
        for lab, row in s["metrics"]["confusion"]["overall"].items():
            lines.append(f"| {lab} | {row['LIKELY_SCAM']} | {row['UNCLEAR']} | {row['NO_STRONG_SIGNALS']} |")
        lines.append("")
    b4 = res["systems"].get("B4-engine")
    if b4:
        items = {i["id"]: i for i in res["items"]}
        errs = [(i, v) for i, v in b4["predictions"].items()
                if (items[i]["label"] == "scam" and v == "NO_STRONG_SIGNALS")
                or (items[i]["label"] in ("legitimate", "promotional") and v == "LIKELY_SCAM")]
        lines += ["## B4 errors (dangerous misses and false alarms)", ""]
        lines += [f"- {i} ({items[i]['label']}, {items[i]['language']}): {v}" for i, v in errs] or ["- none"]
        lines.append("")
    lines += ["## Configuration", "", "```json"]
    lines += [json.dumps(meta, indent=2, ensure_ascii=False), "```", ""]
    return "\n".join(lines)
