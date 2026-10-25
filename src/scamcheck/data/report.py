"""Dataset quality report (markdown). Describes the data only; contains no model results."""

from __future__ import annotations

from collections import Counter

from .schema import Item

SMALL_N = 50          # below this many gold items, proportions are too noisy to describe the data
GIANT_GROUP_MIN = 5   # a group this large and over GIANT_GROUP_SHARE of items is flagged
GIANT_GROUP_SHARE = 0.05
MIN_KAPPA_PAIRS = 30


def cohen_kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Cohen's kappa over (first annotation, second annotation) label pairs."""
    n = len(pairs)
    if n == 0:
        return None
    observed = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(ca[k] * cb[k] for k in ca) / (n * n)
    if expected == 1:  # both annotators used a single, identical label: agreement beyond chance is undefined
        return None
    return (observed - expected) / (1 - expected)


def _table(title: str, counter: Counter, total: int) -> list[str]:
    lines = [f"### {title}", "", "| value | count | share |", "|---|---:|---:|"]
    for k, v in sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0]))):
        lines.append(f"| {k} | {v} | {v / total:.1%} |")
    return lines + [""]


def build_report(items: list[Item], manifest: dict | None = None, review_pairs: list[dict] | None = None,
                 leakage_problems: list[str] | None = None) -> str:
    total = len(items)
    synthetic = sum(it.is_synthetic for it in items)
    labelled = [it for it in items if it.gold]
    out = ["# Dataset quality report", ""]
    out += ["> This report describes the dataset only. It contains **no model performance results**.", ""]
    if synthetic:
        out += [f"> **{synthetic} of {total} items are SYNTHETIC** (written for testing or augmentation). "
                "They are not real-world evidence and must never be cited as such.", ""]
    if total == 0:
        return "\n".join(out + ["No items. Nothing was grouped, split or checked."])
    if len(labelled) < SMALL_N:
        out += [f"> **Small dataset ({len(labelled)} gold-labelled items):** shares, κ and split balance are "
                "unstable at this size. Use this report to find data problems, not to describe the data.", ""]

    out += ["## Overview", "",
            f"- Items: {total} ({total - synthetic} real-sourced, {synthetic} synthetic)",
            f"- With gold label: {len(labelled)}; pending annotation: {total - len(labelled)}",
            f"- Releasable (licence/consent verified): {sum(it.provenance.releasable for it in items)}",
            f"- Adversarial variants: {sum(it.adversarial is not None for it in items)}",
            ""]

    out += ["## Distributions (gold-labelled items)", ""]
    if labelled:
        n = len(labelled)
        out += _table("Label", Counter(it.gold.label for it in labelled), n)
        out += _table("Label × language", Counter(f"{it.gold.label} / {it.language}" for it in labelled), n)
        out += _table("Category", Counter(f"{it.gold.label} / {it.gold.category or '-'}" for it in labelled), n)
        out += _table("Ground-truth basis", Counter(it.gold.basis for it in labelled), n)
    out += _table("Script", Counter(it.script for it in items), total)
    out += _table("Channel", Counter(it.channel for it in items), total)
    out += _table("Source type", Counter(it.provenance.source_type for it in items), total)
    out += _table("Licence", Counter(f"{it.provenance.licence} (verified={it.provenance.licence_verified})"
                                     for it in items), total)

    pairs = [(it.annotations[0].label, it.annotations[1].label) for it in items if len(it.annotations) >= 2]
    disagreements = [it.id for it in items if len({a.label for a in it.annotations}) > 1]
    kappa = cohen_kappa(pairs)
    out += ["## Annotation quality", "",
            f"- Items with ≥2 annotations: {len(pairs)} of {total}",
            # shortcut: kappa uses annotation order, not fixed rater identity; fine while 2 people annotate.
            f"- Cohen's κ on label (first two annotations): "
            f"{'undefined (no pairs, or both annotators used one identical label)' if kappa is None else f'{kappa:.3f}'}"
            + (f" — fewer than {MIN_KAPPA_PAIRS} pairs, not a stable estimate" if 0 < len(pairs) < MIN_KAPPA_PAIRS else ""),
            f"- Label disagreements: {len(disagreements)} "
            f"(adjudicated: {sum(1 for it in items if it.id in disagreements and it.gold and it.gold.adjudicated)})",
            f"- Mean annotator confidence: "
            f"{_mean([a.confidence for it in items for a in it.annotations])}",
            ""]

    groups = Counter(it.campaign_id for it in items if it.campaign_id)
    out += ["## Duplicates and campaign groups", ""]
    if groups:
        sizes = Counter(groups.values())
        out += [f"- Groups: {len(groups)}; largest: {max(groups.values())} items",
                "- Group size distribution: " + ", ".join(f"{k}×{v}" for k, v in sorted(sizes.items())), ""]
        for gid, n in groups.most_common():
            if n >= GIANT_GROUP_MIN and n > GIANT_GROUP_SHARE * total:
                cats = Counter(f"{it.gold.label}/{it.gold.category or '-'}" for it in items
                               if it.campaign_id == gid and it.gold)
                out.append(f"- **Giant group** {gid}: {n} items ({n / total:.0%}), "
                           f"{', '.join(f'{k}×{v}' for k, v in cats.most_common(4))}. It moves as one unit, so these "
                           "categories cannot be balanced across splits. Check `near_dup_pairs.jsonl` for chained "
                           "merges and record `different` decisions for genuinely distinct templates.")
        out.append("")
    else:
        out += ["- Not grouped yet (run `scamcheck group`).", ""]
    if review_pairs is not None:
        status = Counter(p["status"] for p in review_pairs)
        out += [f"- Near-duplicate candidate pairs: {len(review_pairs)} "
                f"({', '.join(f'{k}: {v}' for k, v in sorted(status.items())) or 'none'})", ""]

    if manifest:
        split_of = {r["id"]: r["split"] for r in manifest["items"]}
        by_id = {it.id: it for it in items}
        out += ["## Splits", "", "| split | items | scam | legitimate | promotional | ambiguous | english | hinglish | synthetic |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for s in ("train", "dev", "test"):
            its = [by_id[i] for i, sp in split_of.items() if sp == s and i in by_id]
            lab = Counter(it.gold.label for it in its)
            lang = Counter(it.language for it in its)
            out.append(f"| {s} | {len(its)} | {lab['scam']} | {lab['legitimate']} | {lab['promotional']} | "
                       f"{lab['ambiguous']} | {lang['english']} | {lang['hinglish']} | "
                       f"{sum(it.is_synthetic for it in its)} |")
        out.append("")
        if manifest["params"]["allow_synthetic_in_test"]:
            out += ["> **WARNING:** this manifest allowed synthetic items in the test split. "
                    "Use it for pipeline testing only, never for reported results.", ""]
        if "temporal" in manifest:
            t = manifest["temporal"]
            out += [f"- Temporal hold-out: cutoff {t['cutoff']}; train/dev collected up to {t['train_dev_latest']}; "
                    f"test campaigns each have an item after the cutoff (earliest test item {t['test_earliest']}); "
                    f"{len(t['straddling_campaigns'])} campaign(s) straddle the cutoff and are wholly in test.", ""]
        if manifest["excluded"]:
            reasons = Counter(e["reason"] for e in manifest["excluded"])
            out += [f"- Excluded from splits: {len(manifest['excluded'])} "
                    f"({'; '.join(f'{r}: {n}' for r, n in sorted(reasons.items()))})", ""]
        adv = manifest.get("adversarial", [])
        if adv:
            orphans = sum(a["parent_split"] is None for a in adv)
            out += [f"- Adversarial variants (evaluation-only, follow their parent): {len(adv)}"
                    + (f"; {orphans} have no split parent" if orphans else ""), ""]
        blocked = manifest.get("test_blocked_by_group", [])
        if blocked:
            out += [f"- Real items kept out of test because a synthetic or unlicensed item shares their group: "
                    f"{len(blocked)} ({', '.join(blocked[:10])}{'…' if len(blocked) > 10 else ''})", ""]
        balance = _split_warnings([by_id[i] for i in split_of if i in by_id], split_of)
        if balance:
            out += ["### Split balance warnings", ""] + [f"- {w}" for w in balance] + [""]

    if leakage_problems is not None:
        out += ["## Leakage check", ""]
        if manifest is not None and not manifest["items"]:
            out += ["- NOT RUN: the manifest contains no items, so there was nothing to check.", ""]
        elif not leakage_problems:
            out += ["- PASS: no campaign, lineage, exact duplicate, scam domain, scammer id or near duplicate "
                    "crosses splits.", ""]
        else:
            out += [f"- FAIL ({len(leakage_problems)}):"] + [f"  - {p}" for p in leakage_problems] + [""]

    warnings = _coverage_warnings(labelled)
    if warnings:
        out += ["## Coverage warnings", ""] + [f"- {w}" for w in warnings] + [""]
    return "\n".join(out)


def _split_warnings(split_items: list[Item], split_of: dict[str, str]) -> list[str]:
    out = []
    if not split_items:
        return out
    by_split = {s: [it for it in split_items if split_of[it.id] == s] for s in ("train", "dev", "test")}
    cats = {f"{it.gold.label}/{it.gold.category or '-'}" for it in split_items}
    overall = Counter(it.gold.label for it in split_items)
    for s, its in by_split.items():
        if not its:
            out.append(f"{s} split is empty")
            continue
        if s != "train":
            missing = sorted(cats - {f"{it.gold.label}/{it.gold.category or '-'}" for it in its})
            if missing:
                out.append(f"{len(missing)} label/category combinations absent from {s}: {', '.join(missing)}")
        if len(its) >= 20:
            share = Counter(it.gold.label for it in its)
            for label, n in overall.items():
                diff = share[label] / len(its) - n / len(split_items)
                if abs(diff) > 0.15:
                    out.append(f"{s}: share of {label} differs from the overall share by {diff:+.0%}")
    return out


def _mean(xs: list[int]) -> str:
    return f"{sum(xs) / len(xs):.2f}" if xs else "n/a"


def _coverage_warnings(labelled: list[Item]) -> list[str]:
    """Flags gaps against the composition targets in docs/PLAN.md §8 (M2)."""
    real = [it for it in labelled if not it.is_synthetic]
    out = []
    for lang in ("english", "hinglish"):
        n = sum(1 for it in real if it.gold.label == "scam" and it.language == lang)
        if n < 120:
            out.append(f"real {lang} scams: {n} (target ≥ 120 before a test split is meaningful)")
    legit = Counter(it.gold.category for it in real if it.gold.label == "legitimate")
    enough = [c for c, n in legit.items() if n >= 75]
    if len(enough) < 4:
        out.append(f"legitimate categories with ≥ 75 real items: {len(enough)} (target ≥ 4)")
    return out
