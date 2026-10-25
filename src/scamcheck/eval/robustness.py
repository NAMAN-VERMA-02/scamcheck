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
from .review import MIN_FAMILY_REVIEWS, REVIEW_GUIDELINE, apply_reviews

DEFAULT_SEEDS = (11, 23, 37)
SYSTEMS_EVALUATED = ("B4-engine", "B1-rules", "B2-tfidf-lr")


STATUSES = ("excluded_no_change", "unvalidated_family", "label_inherited", "needs_human_review", "human_reviewed",
            "reviewed_no_label", "review_conflict")


def run_robustness(items: list[Item], manifest: dict, *, seeds: tuple[int, ...] = DEFAULT_SEEDS,
                   splits: tuple[str, ...] = ("dev", "test"), model: Optional[ChatAdapter] = None,
                   reviews: Optional[list[dict]] = None, train_seed: int = 13) -> tuple[dict, list[dict]]:
    split_of = {r["id"]: r["split"] for r in manifest["items"]}
    train = [it for it in items if split_of.get(it.id) == "train" and it.gold.label != "ambiguous"]
    parents = [it for it in items if split_of.get(it.id) in splits]
    systems = {s.name: s for s in build_systems([it.text for it in train], [it.gold.label == "scam" for it in train],
                                               train_seed, model) if s.name in SYSTEMS_EVALUATED}

    records = [variant_record(p.id, p.text, p.language, p.gold.label, t.name, seed)
               for seed in seeds for p in parents for t in TRANSFORMS if p.language in t.languages]
    families = apply_reviews(records, reviews or [])
    live = [r for r in records if r["status"] != "excluded_no_change"]
    by_id = {p.id: p for p in parents}
    parent_v = {name: {p.id: s.predict(p.text) for p in parents} for name, s in systems.items()}
    variant_v = {name: {r["variant_id"]: s.predict(r["text"]) for r in live} for name, s in systems.items()}

    # Verdict consistency needs no label, only "same meaning": preserving-by-design variants, minus any a reviewer
    # said changed meaning. It stays PROVISIONAL while any of them comes from an unvalidated family.
    pres = [r for r in live if r["preserving"] and r.get("review_meaning", "yes") == "yes"
            and r["status"] != "review_conflict"]
    validated = [r for r in pres if r["status"] in ("label_inherited", "human_reviewed")]
    labelled = [r for r in live if r["status"] in ("label_inherited", "human_reviewed")]
    provisional = any(r["status"] == "unvalidated_family" for r in pres)

    out_systems = {}
    for name in systems:
        pv, vv = parent_v[name], variant_v[name]

        def consistency(rs: list[dict], pv=pv, vv=vv) -> dict:
            return wilson(sum(vv[r["variant_id"]] == pv[r["parent_id"]] for r in rs), len(rs))

        def group(key: str, rs: list[dict]) -> dict:
            g = defaultdict(list)
            for r in rs:
                g[r[key]].append(r)
            return {str(k): consistency(v) for k, v in sorted(g.items())}

        def to_nss(rs: list[dict], pv=pv, vv=vv) -> dict:
            return wilson(sum(vv[r["variant_id"]] == "NO_STRONG_SIGNALS" and pv[r["parent_id"]] != "NO_STRONG_SIGNALS"
                              for r in rs), len(rs))

        def lost(rs: list[dict], pv=pv, vv=vv) -> dict:
            return wilson(sum(pv[r["parent_id"]] == "LIKELY_SCAM" and vv[r["variant_id"]] != "LIKELY_SCAM" for r in rs),
                          sum(pv[r["parent_id"]] == "LIKELY_SCAM" for r in rs))

        scam = [r for r in labelled if r["label"] == "scam"]
        scam_parent = [r for r in pres if r["parent_label"] == "scam"]
        per_seed = group("seed", pres)
        seed_rates = [v["rate"] for v in per_seed.values() if v["rate"] is not None]
        failures = [r for r in pres if vv[r["variant_id"]] != pv[r["parent_id"]]]
        out_systems[name] = {
            "description": systems[name].description,
            # A system that always gives the same verdict is trivially "consistent"; say so instead of implying it.
            "constant_verdict": len(set(pv.values()) | set(vv.values())) == 1,
            "consistency_provisional": provisional,
            "consistency_preserving": consistency(pres),
            "consistency_validated_only": consistency(validated),
            "consistency_by_transform": group("transform", pres),
            "consistency_by_language": group("language", pres),
            "consistency_by_seed": per_seed,
            "seed_variation": {"min": min(seed_rates), "max": max(seed_rates),
                               "stdev": round(statistics.pstdev(seed_rates), 4)} if seed_rates else None,
            # Label-based: only variants whose label a human confirmed (individually or by validated family).
            "scam_flip_to_no_strong_signals": to_nss(scam),
            "scam_lost_detection": lost(scam),
            # Parent-based (provisional): the variant's own label is unconfirmed; this describes verdict movement
            # away from a scam parent, not a measured miss.
            "parent_scam_moved_to_no_strong_signals": to_nss(scam_parent),
            "parent_scam_detection_lost": lost(scam_parent),
            "needs_review_verdicts": _verdict_counts([r for r in live if r["status"] == "needs_human_review"], vv),
            "failure_examples": [
                {"variant_id": r["variant_id"], "parent_id": r["parent_id"], "transform": r["transform"],
                 "seed": r["seed"], "language": r["language"], "status": r["status"],
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
            "n_parents": len(parents), "versions": VERSIONS, "review_guideline": REVIEW_GUIDELINE,
            "min_family_reviews": MIN_FAMILY_REVIEWS,
            "transforms": [{"name": t.name, "preserving": t.preserving, "languages": list(t.languages)}
                           for t in TRANSFORMS],
            "families": families,
            "counts": {"generated": len(records),
                       **{st: sum(r["status"] == st for r in records) for st in STATUSES},
                       "reviews": len(reviews or [])},
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
    c = m["counts"]
    lines = ["# Robustness report", "", f"> **{m['data_label']}**", "",
             f"Generator `{m['generator_version']}`, seeds {m['seeds']}, {m['n_parents']} parents from "
             f"{'/'.join(m['parent_splits'])}. Review guideline `{m['review_guideline']}`; a family is validated "
             f"after at least {m['min_family_reviews']} reviewed variants, all judged meaning-preserving "
             "(docs/ROBUSTNESS_REVIEW.md).", "",
             "| Generated | Excluded (no change) | Unvalidated family (no label) | Label inherited (validated family) "
             "| Needs human review | Human reviewed | Reviewed, no label | Review conflict | Review decisions |",
             "|---|---|---|---|---|---|---|---|---|",
             f"| {c['generated']} | {c['excluded_no_change']} | {c['unvalidated_family']} | {c['label_inherited']} | "
             f"{c['needs_human_review']} | {c['human_reviewed']} | {c['reviewed_no_label']} | {c['review_conflict']} | "
             f"{c['reviews']} |", ""]

    def pct(w):
        return "n/a" if w is None or w["rate"] is None else \
            f"{w['rate'] * 100:.1f}% [{w['lo'] * 100:.1f}–{w['hi'] * 100:.1f}] ({w['k']}/{w['n']})"

    lines += ["## Mutation families", "", "| Family | Preserving by design | Status | Reviewed | yes | no | unsure "
              "| conflict | Meaning-change rate, 95% upper bound |", "|---|---|---|---|---|---|---|---|---|"]
    for name, f in m["families"].items():
        ub = "n/a" if f["meaning_change_upper_95"] is None else f"{f['meaning_change_upper_95'] * 100:.1f}%"
        lines.append(f"| {name} | {'yes' if f['preserving_by_design'] else 'no'} | {f['status']} | {f['reviewed']} | "
                     f"{f['yes']} | {f['no']} | {f['unsure']} | {f['conflict']} | {ub} |")
    lines += ["", "## Summary", ""]
    if any(s["consistency_provisional"] for s in res["systems"].values()):
        lines += ["> **Provisional:** verdict consistency below includes variants from families no human has "
                  "validated yet. Label-based rows (scam → NO_STRONG_SIGNALS, detections lost) use only "
                  "human-confirmed labels and stay n/a until reviews exist. The parent-based rows describe verdict "
                  "movement away from a scam parent; the variant's own label is unconfirmed.", ""]
    lines += ["| System | Consistency (preserving by design) | Consistency (validated only) | Scam → NO_STRONG_SIGNALS "
              "(confirmed labels) | Scam detections lost (confirmed labels) | Parent-scam variants → NO_STRONG_SIGNALS "
              "(provisional) | Parent-scam detections lost (provisional) | Seed spread |",
              "|---|---|---|---|---|---|---|---|"]
    for name, s in res["systems"].items():
        sv = s["seed_variation"]
        spread = f"{sv['min'] * 100:.1f}–{sv['max'] * 100:.1f}%" if sv else "n/a"
        flag = " ⚠ constant verdict: trivially consistent" if s["constant_verdict"] else ""
        lines.append(f"| {name}{flag} | {pct(s['consistency_preserving'])} | {pct(s['consistency_validated_only'])} | "
                     f"{pct(s['scam_flip_to_no_strong_signals'])} | {pct(s['scam_lost_detection'])} | "
                     f"{pct(s['parent_scam_moved_to_no_strong_signals'])} | {pct(s['parent_scam_detection_lost'])} | "
                     f"{spread} |")
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
