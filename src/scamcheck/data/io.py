"""JSONL reading/writing and validation with line-numbered errors."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from .normalise import content_hash
from .schema import Item


@dataclass
class LoadResult:
    items: list[Item]
    errors: list[str]    # make the file invalid
    warnings: list[str]  # worth a human look, file still valid


def load_items(path: Path) -> LoadResult:
    items: list[Item] = []
    errors: list[str] = []
    seen_ids: dict[str, int] = {}
    for lineno, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = Item.model_validate(json.loads(line))
        except json.JSONDecodeError as e:
            errors.append(f"line {lineno}: invalid JSON: {e.msg}")
            continue
        except ValidationError as e:
            for err in e.errors():
                loc = ".".join(str(p) for p in err["loc"]) or "<item>"
                errors.append(f"line {lineno}: {loc}: {err['msg']}")
            continue
        if item.id in seen_ids:
            errors.append(f"line {lineno}: id {item.id!r} already used on line {seen_ids[item.id]}")
            continue
        seen_ids[item.id] = lineno
        items.append(item)
    return LoadResult(items, errors, _warnings(items))


def _warnings(items: list[Item]) -> list[str]:
    out = []
    ids = {it.id for it in items}
    by_hash: dict[str, list[Item]] = {}
    for it in items:
        by_hash.setdefault(content_hash(it.text), []).append(it)
        if it.gold is None:
            out.append(f"{it.id}: no gold label yet (excluded from splits)")
        if not it.provenance.releasable:
            out.append(f"{it.id}: licence not verified (excluded from test split, not releasable)")
        for ref in (it.synthetic and it.synthetic.seed_id, it.adversarial and it.adversarial.parent_id):
            if ref and ref not in ids:
                out.append(f"{it.id}: lineage reference {ref!r} is not in this file, so it cannot be grouped with it")
    for dupes in by_hash.values():
        if len(dupes) > 1:
            out.append(f"exact duplicate text: {', '.join(d.id for d in dupes)}")
            labels = {d.gold.label for d in dupes if d.gold}
            if len(labels) > 1:
                out.append(f"conflicting gold labels for identical text ({', '.join(sorted(labels))}): "
                           f"{', '.join(d.id for d in dupes)}; re-adjudicate")
    return out


def write_items(path: Path, items: list[Item]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for it in items:
            f.write(it.model_dump_json(exclude_none=True) + "\n")
