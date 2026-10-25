"""Group-aware, stratified train/dev/test split plus independent leakage checks."""

from __future__ import annotations

import hashlib
import random
from collections import Counter
from datetime import date
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


class TemporalSplitError(ValueError):
    """The data cannot support a valid temporal hold-out; the message says why."""


def _temporal_test(groups: dict[str, list[Item]], cutoff: date, allow_synthetic_in_test: bool):
    """Campaign-level temporal hold-out.

    A campaign with any item collected after `cutoff` is "future": it may only be tested, never trained on, so a
    campaign that straddles the cutoff goes wholly to the test side. Future campaigns that are not test-eligible
    (synthetic, unverified licence) are excluded rather than moved into training. Returns
    (test assignment, excluded rows, temporal summary).
    """
    latest = {g: max(m.provenance.collected_at for m in ms) for g, ms in groups.items()}
    earliest = {g: min(m.provenance.collected_at for m in ms) for g, ms in groups.items()}
    future = sorted(g for g in groups if latest[g] > cutoff)
    past = [g for g in groups if latest[g] <= cutoff]
    dates = sorted({m.provenance.collected_at for ms in groups.values() for m in ms})
    span = f"collected_at spans {dates[0]} to {dates[-1]} ({len(dates)} distinct date(s))" if dates else "no items"
    if not future:
        raise TemporalSplitError(f"no campaign has an item collected after the cutoff {cutoff}; {span}. A temporal "
                                 "hold-out needs data collected after the training period.")
    if not past:
        raise TemporalSplitError(f"every campaign has an item collected after the cutoff {cutoff}; {span}. Nothing "
                                 "is left to train on without using future data.")
    assignment, excluded = {}, []
    for g in future:
        if all(allowed_in_test(m, allow_synthetic_in_test) for m in groups[g]):
            assignment[g] = "test"
        else:
            excluded += [{"id": m.id, "reason": "after the temporal cutoff but not test-eligible (synthetic or "
                                                "licence not verified); never moved into training"}
                         for m in groups[g]]
    if not assignment:
        raise TemporalSplitError(f"{len(future)} campaign(s) fall after the cutoff {cutoff}, but none is "
                                 "test-eligible (synthetic items or unverified licences), so the test split would "
                                 "be empty.")
    summary = {"cutoff": cutoff.isoformat(),
               "train_dev_latest": max(latest[g] for g in past).isoformat(),
               "test_earliest": min(earliest[g] for g in assignment).isoformat(),
               "straddling_campaigns": sorted(g for g in assignment if earliest[g] <= cutoff)}
    return assignment, excluded, summary


def _require_labels(split_items_: list[Item], split: str, needed: set[str], why: str) -> None:
    have = {it.gold.label for it in split_items_}
    missing = sorted(needed - have)
    if missing:
        raise TemporalSplitError(f"temporal {split} split has labels {sorted(have) or 'none'} but no "
                                 f"{', '.join(missing)}; {why}")


def split_items(
    items: list[Item],
    ratios: dict[str, float] = DEFAULT_RATIOS,
    seed: int = 13,
    allow_synthetic_in_test: bool = False,
    temporal_cutoff: date | None = None,
) -> dict:
    """Group-aware stratified split. With `temporal_cutoff`, test = every eligible campaign with an item collected
    after the cutoff, and the remaining (past) campaigns are split train/dev in the ratio train:dev."""
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

    assignment: dict[str, str] = {}
    temporal = None
    splits = SPLITS
    if temporal_cutoff is not None:
        assignment, future_excluded, temporal = _temporal_test(groups, temporal_cutoff, allow_synthetic_in_test)
        excluded += future_excluded
        dropped = {r["id"] for r in future_excluded}
        labelled = [it for it in labelled if it.id not in dropped]
        groups = {g: ms for g, ms in groups.items() if not any(m.id in dropped for m in ms)}
        splits = ("train", "dev")
        ratios = {"train": ratios["train"] / (ratios["train"] + ratios["dev"]),
                  "dev": ratios["dev"] / (ratios["train"] + ratios["dev"]), "test": 0.0}

    strata: dict[tuple, list[str]] = {}
    for gid, members in groups.items():
        if gid in assignment:
            continue
        key = Counter((m.gold.label, m.language) for m in members).most_common()
        key = sorted(key, key=lambda kv: (-kv[1], kv[0]))[0][0]
        strata.setdefault(key, []).append(gid)

    rng = random.Random(seed)
    test_blocked: list[str] = []
    for key in sorted(strata):
        gids = sorted(strata[key])
        rng.shuffle(gids)
        gids.sort(key=lambda g: -len(groups[g]))  # stable: big groups first, ties keep shuffled order
        total = sum(len(groups[g]) for g in gids)
        counts = dict.fromkeys(SPLITS, 0)
        for g in gids:
            eligible = [allowed_in_test(m, allow_synthetic_in_test) for m in groups[g]]
            allowed = [s for s in splits if s != "test" or all(eligible)]
            if not all(eligible) and "test" in splits:
                test_blocked += [m.id for m, ok in zip(groups[g], eligible) if ok]
            best = max(allowed, key=lambda s: ratios[s] * total - counts[s])
            assignment[g] = best
            counts[best] += len(groups[g])

    split_of = {it.id: assignment[it.campaign_id] for it in labelled}
    if temporal is not None:
        by_split = {s: [it for it in labelled if split_of[it.id] == s] for s in SPLITS}
        _require_labels(by_split["test"], "test", {"scam", "legitimate"},
                        "recall and false alarms cannot both be measured on future data.")
        _require_labels(by_split["train"], "train", {"scam", "legitimate"},
                        "a baseline cannot be trained on the past data.")
    rows = sorted(
        ({"id": it.id, "split": split_of[it.id], "campaign_id": it.campaign_id, "sha256": item_sha256(it)}
         for it in labelled),
        key=lambda r: r["id"],
    )
    return {
        "manifest_version": 2,
        "params": {"ratios": ratios, "seed": seed, "allow_synthetic_in_test": allow_synthetic_in_test,
                   **({"temporal_cutoff": temporal_cutoff.isoformat()} if temporal_cutoff else {})},
        **({"temporal": temporal} if temporal else {}),
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

    cutoff = manifest["params"].get("temporal_cutoff")
    if cutoff:
        cut = date.fromisoformat(cutoff)
        future_campaigns = {it.campaign_id for it in split_items_ if it.provenance.collected_at > cut}
        for it in split_items_:
            if split_of[it.id] != "test" and it.campaign_id in future_campaigns:
                problems.append(f"temporal: {it.id} ({split_of[it.id]}) belongs to campaign {it.campaign_id}, "
                                f"which has items collected after the cutoff {cutoff}")
            if split_of[it.id] == "test" and it.campaign_id not in future_campaigns:
                problems.append(f"temporal: {it.id} is in test but its campaign has nothing after the cutoff {cutoff}")

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
