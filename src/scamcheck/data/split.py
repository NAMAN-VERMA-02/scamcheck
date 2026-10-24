"""Group-aware, stratified train/dev/test split plus independent leakage checks."""

from __future__ import annotations

import hashlib
import random
from collections import Counter
from itertools import combinations

from .grouping import linking_domains
from .normalise import content_hash, jaccard, shingles
from .schema import Item

SPLITS = ("train", "dev", "test")
DEFAULT_RATIOS = {"train": 0.60, "dev": 0.15, "test": 0.25}


def item_sha256(item: Item) -> str:
    return hashlib.sha256(item.model_dump_json(exclude_none=True).encode("utf-8")).hexdigest()


def allowed_in_test(item: Item, allow_synthetic_in_test: bool) -> bool:
    if not item.provenance.releasable:
        return False
    return allow_synthetic_in_test or not item.is_synthetic


def split_items(
    items: list[Item],
    ratios: dict[str, float] = DEFAULT_RATIOS,
    seed: int = 13,
    allow_synthetic_in_test: bool = False,
) -> dict:
    if abs(sum(ratios.values()) - 1) > 1e-9 or set(ratios) != set(SPLITS):
        raise ValueError("ratios must cover train/dev/test and sum to 1")
    missing = [it.id for it in items if it.campaign_id is None]
    if missing:
        raise ValueError(f"run `scamcheck group` first; no campaign_id on: {', '.join(missing[:5])}")

    excluded = [{"id": it.id, "reason": "no gold label"} for it in items if it.gold is None]
    # Adversarial variants are evaluation-only: they follow their parent and never constrain where it goes.
    adversarial = [it for it in items if it.gold is not None and it.adversarial is not None]
    labelled = [it for it in items if it.gold is not None and it.adversarial is None]

    groups: dict[str, list[Item]] = {}
    for it in labelled:
        groups.setdefault(it.campaign_id, []).append(it)

    strata: dict[tuple, list[str]] = {}
    for gid, members in groups.items():
        key = Counter((m.gold.label, m.language) for m in members).most_common()
        key = sorted(key, key=lambda kv: (-kv[1], kv[0]))[0][0]
        strata.setdefault(key, []).append(gid)

    rng = random.Random(seed)
    assignment: dict[str, str] = {}
    test_blocked: list[str] = []
    for key in sorted(strata):
        gids = sorted(strata[key])
        rng.shuffle(gids)
        gids.sort(key=lambda g: -len(groups[g]))  # stable: big groups first, ties keep shuffled order
        total = sum(len(groups[g]) for g in gids)
        counts = dict.fromkeys(SPLITS, 0)
        for g in gids:
            eligible = [allowed_in_test(m, allow_synthetic_in_test) for m in groups[g]]
            allowed = [s for s in SPLITS if s != "test" or all(eligible)]
            if not all(eligible):
                test_blocked += [m.id for m, ok in zip(groups[g], eligible) if ok]
            best = max(allowed, key=lambda s: ratios[s] * total - counts[s])
            assignment[g] = best
            counts[best] += len(groups[g])

    split_of = {it.id: assignment[it.campaign_id] for it in labelled}
    rows = sorted(
        ({"id": it.id, "split": split_of[it.id], "campaign_id": it.campaign_id, "sha256": item_sha256(it)}
         for it in labelled),
        key=lambda r: r["id"],
    )
    return {
        "manifest_version": 2,
        "params": {"ratios": ratios, "seed": seed, "allow_synthetic_in_test": allow_synthetic_in_test},
        "counts": dict(Counter(r["split"] for r in rows)),
        "items": rows,
        "adversarial": sorted(
            ({"id": a.id, "parent_id": a.adversarial.parent_id, "parent_split": split_of.get(a.adversarial.parent_id)}
             for a in adversarial), key=lambda r: r["id"]),
        # real, eligible items kept out of test only because a synthetic/unlicensed item shares their group
        "test_blocked_by_group": sorted(test_blocked),
        "excluded": sorted(excluded, key=lambda e: e["id"]),
    }


def check_leakage(
    items: list[Item],
    manifest: dict,
    near_dup_threshold: float,
    decisions: dict[frozenset, str] | None = None,
) -> list[str]:
    """Re-derive every leakage condition from item content rather than trusting the splitter or campaign ids."""
    decisions = decisions or {}
    by_id = {it.id: it for it in items}
    split_of = {r["id"]: r["split"] for r in manifest["items"]}
    problems: list[str] = []

    unknown = sorted(set(split_of) - set(by_id))
    if unknown:
        problems.append(f"manifest references ids missing from the data: {', '.join(unknown[:5])}")
    for r in manifest["items"]:
        it = by_id.get(r["id"])
        if it and item_sha256(it) != r["sha256"]:
            problems.append(f"{it.id}: content changed since the manifest was written")

    split_items_ = [by_id[i] for i in split_of if i in by_id]
    allow_syn = manifest["params"]["allow_synthetic_in_test"]
    for it in split_items_:
        if split_of[it.id] == "test" and not allowed_in_test(it, allow_syn):
            problems.append(f"{it.id}: in test but synthetic or licence not verified")
        if it.adversarial is not None:
            problems.append(f"{it.id}: adversarial variant placed in {split_of[it.id]}; it must be evaluation-only")
        for ref in (it.synthetic and it.synthetic.seed_id,):
            if ref in split_of and split_of[ref] != split_of[it.id]:
                problems.append(f"lineage: {it.id} ({split_of[it.id]}) derives from {ref} ({split_of[ref]})")
    for a in manifest.get("adversarial", []):
        actual = split_of.get(a["parent_id"])
        if a["parent_split"] != actual:
            problems.append(f"lineage: adversarial {a['id']} recorded with parent split {a['parent_split']}, "
                            f"parent {a['parent_id']} is in {actual}")

    def across(key_fn, what):
        seen: dict[str, tuple[str, str]] = {}
        for it in split_items_:
            for key in key_fn(it):
                prev = seen.setdefault(key, (split_of[it.id], it.id))
                if prev[0] != split_of[it.id]:
                    problems.append(f"{what} {key!r} in {prev[0]} ({prev[1]}) and {split_of[it.id]} ({it.id})")

    links = linking_domains(items)
    across(lambda it: [it.campaign_id] if it.campaign_id else [], "campaign")
    across(lambda it: [content_hash(it.text)[:12]], "exact text hash")
    across(lambda it: links.get(it.id, []), "scam domain")
    across(lambda it: it.scammer_ids if it.gold and it.gold.label == "scam" else [], "scammer id")

    sh = {it.id: shingles(it.text) for it in split_items_}
    for a, b in combinations(sorted(sh), 2):
        if split_of[a] == split_of[b] or decisions.get(frozenset((a, b))) == "different":
            continue
        sim = jaccard(sh[a], sh[b])
        if sim >= near_dup_threshold:
            problems.append(f"near duplicate ({sim:.2f}) across splits: {a} ({split_of[a]}) / {b} ({split_of[b]})")
    return problems
