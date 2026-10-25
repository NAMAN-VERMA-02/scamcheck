"""Robustness Lab: evaluate systems on seeded variants of dev/test parents.

Variants are adversarial fixtures, never training data and never real-world evidence. Their lineage
(parent_id, seed, transform, generator_version, output hash) is written next to the report.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Optional

from ..data.schema import Item
from ..engine import VERSIONS
from ..engine.llm import ChatAdapter
from .baselines import build_systems
from .metrics import wilson
from .mutate import GENERATOR_VERSION, TRANSFORMS, variant_record

DEFAULT_SEEDS = (11, 23, 37)
SYSTEMS_EVALUATED = ("B4-engine", "B1-rules", "B2-tfidf-lr")


def run_robustness(items: list[Item], manifest: dict, *, seeds: tuple[int, ...] = DEFAULT_SEEDS,
                   splits: tuple[str, ...] = ("dev", "test"), model: Optional[ChatAdapter] = None,
                   reviews: Optional[dict[str, str]] = None, train_seed: int = 13) -> tuple[dict, list[dict]]:
    reviews = reviews or {}
    split_of = {r["id"]: r["split"] for r in manifest["items"]}
    train = [it for it in items if split_of.get(it.id) == "train" and it.gold.label != "ambiguous"]
    parents = [it for it in items if split_of.get(it.id) in splits]
    systems = {s.name: s for s in build_systems([it.text for it in train], [it.gold.label == "scam" for it in train],
                                               train_seed, model) if s.name in SYSTEMS_EVALUATED}

    records = [variant_record(p.id, p.text, p.language, p.gold.label, t.name, seed)
               for seed in seeds for p in parents for t in TRANSFORMS if p.language in t.languages]
    for r in records:
        if r["variant_id"] in reviews and r["status"] == "needs_human_review":
            r["status"], r["label"] = "human_reviewed", reviews[r["variant_id"]]
    live = [r for r in records if r["status"] != "excluded_no_change"]
    by_id = {p.id: p for p in parents}
    parent_v = {name: {p.id: s.predict(p.text) for p in parents} for name, s in systems.items()}
    variant_v = {name: {r["variant_id"]: s.predict(r["text"]) for r in live} for name, s in systems.items()}

    out_systems = {}
    for name in systems:
        pv, vv = parent_v[name], variant_v[name]
        labelled = [r for r in live if r["status"] in ("label_inherited", "human_reviewed")]
        pres = [r for r in labelled if r["preserving"]]

        def consistency(rs: list[dict], pv=pv, vv=vv) -> dict:
            return wilson(sum(vv[r["variant_id"]] == pv[r["parent_id"]] for r in rs), len(rs))

        def group(key: str, rs: list[dict]) -> dict:
            g = defaultdict(list)
            for r in rs:
                g[r[key]].append(r)
            return {str(k): consistency(v) for k, v in sorted(g.items())}

        scam = [r for r in labelled if r["label"] == "scam"]
        per_seed = group("seed", pres)
        seed_rates = [v["rate"] for v in per_seed.values() if v["rate"] is not None]
        failures = [r for r in pres if vv[r["variant_id"]] != pv[r["parent_id"]]]
        out_systems[name] = {
            "description": systems[name].description,
            # A system that always gives the same verdict is trivially "consistent"; say so instead of implying it.
            "constant_verdict": len(set(pv.values()) | set(vv.values())) == 1,
            "consistency_preserving": consistency(pres),
            "consistency_by_transform": group("transform", pres),
            "consistency_by_language": group("language", pres),
            "consistency_by_seed": per_seed,
            "seed_variation": {"min": min(seed_rates), "max": max(seed_rates),
                               "stdev": round(statistics.pstdev(seed_rates), 4)} if seed_rates else None,
            "scam_flip_to_no_strong_signals": wilson(
                sum(vv[r["variant_id"]] == "NO_STRONG_SIGNALS" and pv[r["parent_id"]] != "NO_STRONG_SIGNALS"
                    for r in scam), len(scam)),
            "scam_lost_detection": wilson(
                sum(pv[r["parent_id"]] == "LIKELY_SCAM" and vv[r["variant_id"]] != "LIKELY_SCAM" for r in scam),
                sum(pv[r["parent_id"]] == "LIKELY_SCAM" for r in scam)),
            "needs_review_verdicts": _verdict_counts([r for r in live if r["status"] == "needs_human_review"], vv),
            "failure_examples": [
                {"variant_id": r["variant_id"], "parent_id": r["parent_id"], "transform": r["transform"],
                 "seed": r["seed"], "language": r["language"], "label": r["label"],
                 "parent_verdict": pv[r["parent_id"]], "variant_verdict": vv[r["variant_id"]]}
                for r in failures],
        }

    # Side-by-side examples for the UI: for each transform, the first variant per seed order, failures first.
    b4v, b4p = variant_v.get("B4-engine", {}), parent_v.get("B4-engine", {})
    examples = []
    for t in TRANSFORMS:
        rs = [r for r in live if r["transform"] == t.name]
        rs.sort(key=lambda r: (b4v.get(r["variant_id"]) == b4p.get(r["parent_id"]), r["seed"], r["parent_id"]))
        for r in rs[:3]:
            examples.append({"transform": t.name, "preserving": t.preserving, "seed": r["seed"],
                             "variant_id": r["variant_id"], "parent_id": r["parent_id"], "status": r["status"],
                             "language": r["language"], "label": r.get("label"),
                             "parent_text": by_id[r["parent_id"]].text, "variant_text": r["text"],
                             "parent_verdict": b4p.get(r["parent_id"]), "variant_verdict": b4v.get(r["variant_id"])})

    result = {
        "meta": {
            "data_label": ("SYNTHETIC ADVERSARIAL FIXTURES derived from the synthetic benchmark. They measure "
                           "consistency of the systems under controlled perturbations, not real-world robustness."),
            "generator_version": GENERATOR_VERSION, "seeds": list(seeds), "parent_splits": list(splits),
            "n_parents": len(parents), "versions": VERSIONS,
            "transforms": [{"name": t.name, "preserving": t.preserving, "languages": list(t.languages)}
                           for t in TRANSFORMS],
            "counts": {"generated": len(records),
                       "excluded_no_change": sum(r["status"] == "excluded_no_change" for r in records),
                       "label_inherited": sum(r["status"] == "label_inherited" for r in records),
                       "needs_human_review": sum(r["status"] == "needs_human_review" for r in records),
                       "human_reviewed": sum(r["status"] == "human_reviewed" for r in records)},
        },
        "systems": out_systems,
        "examples": examples,
    }
    return result, records


def _verdict_counts(rs: list[dict], vv: dict[str, str]) -> dict:
    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rs:
        out[r["transform"]][vv[r["variant_id"]]] += 1
    return {k: dict(v) for k, v in sorted(out.items())}


def to_markdown(res: dict) -> str:
    m = res["meta"]
    lines = ["# Robustness report", "", f"> **{m['data_label']}**", "",
             f"Generator `{m['generator_version']}`, seeds {m['seeds']}, {m['n_parents']} parents from "
             f"{'/'.join(m['parent_splits'])}.", "",
             "| Generated | Excluded (no change) | Label inherited | Needs human review | Human reviewed |",
             "|---|---|---|---|---|",
             "| {generated} | {excluded_no_change} | {label_inherited} | {needs_human_review} | {human_reviewed} |"
             .format(**m["counts"]), ""]

    def pct(w):
        return "n/a" if w is None or w["rate"] is None else \
            f"{w['rate'] * 100:.1f}% [{w['lo'] * 100:.1f}–{w['hi'] * 100:.1f}] ({w['k']}/{w['n']})"

    lines += ["| System | Consistency (meaning-preserving) | Scam → NO_STRONG_SIGNALS flips | Scam detections lost "
              "| Seed spread (min–max) |", "|---|---|---|---|---|"]
    for name, s in res["systems"].items():
        sv = s["seed_variation"]
        spread = f"{sv['min'] * 100:.1f}–{sv['max'] * 100:.1f}%" if sv else "n/a"
        flag = " ⚠ constant verdict: trivially consistent" if s["constant_verdict"] else ""
        lines.append(f"| {name}{flag} | {pct(s['consistency_preserving'])} | "
                     f"{pct(s['scam_flip_to_no_strong_signals'])} | {pct(s['scam_lost_detection'])} | {spread} |")
    names = list(res["systems"])
    lines += ["", "## Consistency by transform", "", "| Transform | " + " | ".join(names) + " |",
              "|---|" + "---|" * len(names)]
    transforms = sorted({t for s in res["systems"].values() for t in s["consistency_by_transform"]})
    for t in transforms:
        lines.append(f"| {t} | " + " | ".join(pct(res["systems"][n]["consistency_by_transform"].get(t))
                                              for n in names) + " |")
    lines += ["", "## Consistency by language", "", "| Language | " + " | ".join(names) + " |",
              "|---|" + "---|" * len(names)]
    for lang in ("english", "hinglish"):
        lines.append(f"| {lang} | " + " | ".join(pct(res["systems"][n]["consistency_by_language"].get(lang))
                                                 for n in names) + " |")
    lines += ["", "## Meaning-changing transforms (verdicts only; labels await human review)", ""]
    for name, s in res["systems"].items():
        for t, counts in s["needs_review_verdicts"].items():
            lines.append(f"- {name} / {t}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    lines.append("")
    return "\n".join(lines)
