"""Human review of mutation variants (guideline mr1, see docs/ROBUSTNESS_REVIEW.md).

A transform is labelled "meaning-preserving" by design, but that is a hypothesis. No variant inherits its parent's
label until either
  * a reviewer confirmed that this variant means the same as its parent, or
  * its transform family is VALIDATED: at least MIN_FAMILY_REVIEWS of its variants reviewed, every one "yes".
A single "no" marks the family `meaning_change_observed`; after that only individually reviewed variants count.
Meaning-changing families never inherit; their variants need an explicit label from a reviewer.
"""

from __future__ import annotations

import random
import re
from collections import defaultdict
from datetime import date

from ..data.pii import pii_kinds
from .metrics import wilson
from .mutate import BY_NAME

REVIEW_GUIDELINE = "mr1"
MIN_FAMILY_REVIEWS = 30
LABELS = ("scam", "legitimate", "promotional", "ambiguous")
MEANING = ("yes", "no", "unsure")
SHEET_COLUMNS = ["variant_id", "transform", "parent_text", "variant_text", "meaning_preserved", "label", "note"]
_INVISIBLE = re.compile("[­​-‏‪-‮⁠-⁤﻿]")


def visible(text: str) -> str:
    """Spreadsheets render zero-width characters as nothing; show them so the reviewer can see the change."""
    return _INVISIBLE.sub(lambda m: f"⟨U+{ord(m.group()):04X}⟩", text)


def export_sheet(records: list[dict], parent_text: dict[str, str], reviews: list[dict], per_family: int,
                 seed: int) -> list[dict]:
    """Up to `per_family` not-yet-reviewed variants per transform, sampled with a seeded RNG. The parent's label is
    not shown, so meaning judgements stay blind to it."""
    done = {r["variant_id"] for r in reviews}
    by_family: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r["status"] != "excluded_no_change" and r["variant_id"] not in done:
            by_family[r["transform"]].append(r)
    rows = []
    for name in sorted(by_family):
        pool = sorted(by_family[name], key=lambda r: r["variant_id"])
        for r in random.Random(f"{seed}:{name}").sample(pool, min(per_family, len(pool))):
            rows.append({"variant_id": r["variant_id"], "transform": name,
                         "parent_text": visible(parent_text[r["parent_id"]]), "variant_text": visible(r["text"]),
                         "meaning_preserved": "", "label": "", "note": ""})
    return rows


def import_sheet(rows: list[dict], records: list[dict], reviewer: str, existing: list[dict],
                 today: date) -> tuple[list[dict], list[str]]:
    """All-or-nothing: returns (new review decisions, errors). Blank meaning_preserved = not reviewed (skipped)."""
    if not reviewer.strip():
        return [], ["--reviewer is required"]
    known = {r["variant_id"]: r for r in records}
    seen = {(r["variant_id"], r["reviewer"]) for r in existing}
    out, errors = [], []
    for n, row in enumerate(rows, start=2):
        vid = (row.get("variant_id") or "").strip()
        meaning = (row.get("meaning_preserved") or "").strip().lower()
        label = (row.get("label") or "").strip().lower()
        note = (row.get("note") or "").strip()
        if not meaning and not label:
            continue
        if vid not in known:
            errors.append(f"row {n}: unknown variant_id {vid!r}")
            continue
        if meaning not in MEANING:
            errors.append(f"row {n}: meaning_preserved must be one of {', '.join(MEANING)}, got {meaning!r}")
        if label and label not in LABELS:
            errors.append(f"row {n}: label must be blank or one of {', '.join(LABELS)}, got {label!r}")
        if not BY_NAME[known[vid]["transform"]].preserving and meaning != "unsure" and not label:
            errors.append(f"row {n}: {known[vid]['transform']} may change meaning, so a label is required "
                          "(or mark meaning_preserved 'unsure')")
        if pii_kinds(note):
            errors.append(f"row {n}: note looks like it contains an identifier ({', '.join(pii_kinds(note))})")
        if (vid, reviewer) in seen:
            errors.append(f"row {n}: {reviewer} already reviewed {vid}")
        seen.add((vid, reviewer))
        out.append({"variant_id": vid, "reviewer": reviewer, "meaning_preserved": meaning,
                    **({"label": label} if label else {}), "note": note, "guideline": REVIEW_GUIDELINE,
                    "at": today.isoformat()})
    return ([], errors) if errors else (out, [])


def _consensus(decisions: list[dict]) -> dict | None:
    """One decision per variant; reviewers who disagree on meaning or label give no usable decision."""
    meanings = {d["meaning_preserved"] for d in decisions}
    labels = {d.get("label") for d in decisions}
    if len(meanings) > 1 or len(labels) > 1:
        return None
    return {"meaning_preserved": meanings.pop(), "label": labels.pop()}


def family_status(records: list[dict], reviews: list[dict]) -> dict[str, dict]:
    by_variant: dict[str, list[dict]] = defaultdict(list)
    for d in reviews:
        by_variant[d["variant_id"]].append(d)
    family = {r["variant_id"]: r["transform"] for r in records}
    out = {}
    for name, t in BY_NAME.items():
        decided = [_consensus(by_variant[v]) for v in by_variant if family.get(v) == name]
        counts = {m: sum(1 for d in decided if d and d["meaning_preserved"] == m) for m in MEANING}
        counts["conflict"] = sum(1 for d in decided if d is None)
        reviewed = len(decided)
        if not t.preserving:
            status = "meaning_changing"
        elif counts["no"]:
            status = "meaning_change_observed"
        elif reviewed >= MIN_FAMILY_REVIEWS and counts["yes"] == reviewed:
            status = "validated"
        else:
            status = "pending"
        out[name] = {"preserving_by_design": t.preserving, "status": status, "reviewed": reviewed, **counts,
                     # With r "yes" out of r, the meaning-change rate is below this bound at 95%.
                     "meaning_change_upper_95": wilson(counts["no"], reviewed)["hi"] if reviewed else None}
    return out


def apply_reviews(records: list[dict], reviews: list[dict]) -> dict[str, dict]:
    """Set each record's status/label from reviews and family validation (in place). Returns family status."""
    families = family_status(records, reviews)
    by_variant: dict[str, list[dict]] = defaultdict(list)
    for d in reviews:
        by_variant[d["variant_id"]].append(d)
    for r in records:
        r.pop("label", None)
        r.pop("review_meaning", None)
        if r["status"] == "excluded_no_change":
            continue
        if by_variant.get(r["variant_id"]):
            c = _consensus(by_variant[r["variant_id"]])
            if c is None:
                r["status"] = "review_conflict"
                continue
            r["review_meaning"] = c["meaning_preserved"]
            label = c["label"] or (r["parent_label"] if c["meaning_preserved"] == "yes" else None)
            r["status"] = "human_reviewed" if label else "reviewed_no_label"
            if label:
                r["label"] = label
        elif not r["preserving"]:
            r["status"] = "needs_human_review"
        elif families[r["transform"]]["status"] == "validated":
            r["status"], r["label"] = "label_inherited", r["parent_label"]
        else:
            r["status"] = "unvalidated_family"
    return families
