"""Blind double-annotation workflow: per-annotator sheets → import → resolve agreements → adjudicate disagreements.

Sheets are CSV (UTF-8 with BOM so Excel/Sheets keep Devanagari intact). An annotator's sheet never contains gold
labels or anyone else's annotations.
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import random
import re
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from . import schema
from .pii import normalise_digits
from .schema import Annotation, Gold, Item, Span

SHEET_COLUMNS = ["id", "language", "text", "urls", "label", "category", "confidence", "evidence", "note"]
ADJ_COLUMNS = ["id", "text", "annotations", "final_label", "final_category", "basis", "rationale"]
INTAKE_COLUMNS = ["id", "text", "channel", "language", "script", "sender_type", "sender_value", "urls",
                  "registered_domains", "scammer_ids", "source_type", "source_name", "source_url", "licence",
                  "licence_verified", "consent_id", "collected_at", "redaction_version", "redaction_checked_by",
                  "basis"]


def intake_from_rows(rows: list[dict]) -> tuple[list[Item], dict[str, str], list[str]]:
    """Collector CSV → unlabelled items (+ ground-truth basis per id). All-or-nothing, like sheet imports.

    `urls` and `registered_domains` are space-separated and paired by position; `scammer_ids` are
    space-separated tokens from `scamcheck pseudo-id`; `basis` may be blank (= annotator_judgment).
    """
    items, basis, errors, seen = [], {}, [], set()
    for n, row in enumerate(rows, start=2):
        get = lambda k: (row.get(k) or "").strip()  # noqa: E731
        urls, domains = get("urls").split(), get("registered_domains").split()
        if len(urls) != len(domains):
            errors.append(f"row {n}: {len(urls)} url(s) but {len(domains)} registered_domain(s); pair them by position")
            continue
        if get("id") in seen:
            errors.append(f"row {n}: duplicate id {get('id')!r}")
            continue
        if get("source_type") == "synthetic":
            errors.append(f"row {n}: intake is for real-world sources only; synthetic items never enter the pilot")
            continue
        if get("licence_verified").lower() not in ("yes", "no"):
            errors.append(f"row {n}: licence_verified must be yes or no")
            continue
        if (get("licence").startswith("consent-") and get("licence_verified").lower() == "yes"
                and get("licence") not in schema.APPROVED_CONSENT_VERSIONS):
            errors.append(f"row {n}: {get('licence')} is pending legal review; set licence_verified to no until the "
                          "review is recorded in data/source_register.csv")
            continue
        data = {
            "id": get("id"), "text": row.get("text") or "", "channel": get("channel") or "unknown",
            "language": get("language"), "script": get("script"),
            "urls": [{"raw": u, "registered_domain": d} for u, d in zip(urls, domains)],
            "scammer_ids": get("scammer_ids").split(),
            "provenance": {"source_type": get("source_type"), "source_name": get("source_name"),
                           "source_url": get("source_url") or None, "licence": get("licence"),
                           "licence_verified": get("licence_verified").lower() == "yes",
                           "consent_id": get("consent_id") or None, "collected_at": get("collected_at")},
            "redaction": {"version": get("redaction_version"), "checked_by": get("redaction_checked_by")},
        }
        if get("sender_type"):
            data["sender"] = {"type": get("sender_type"), "value": get("sender_value") or None}
        try:
            item = Item.model_validate(data)
        except ValidationError as e:
            errors.append(f"row {n} ({get('id') or '?'}): {_first(e)}")
            continue
        if get("basis") and get("basis") not in ("donor_confirmed", "official_advisory", "sender_verified",
                                                 "annotator_judgment"):
            errors.append(f"row {n} ({item.id}): unknown basis {get('basis')!r}")
            continue
        seen.add(item.id)
        items.append(item)
        if get("basis"):
            basis[item.id] = get("basis")
    return ([], {}, errors) if errors else (items, basis, [])


def export_sheet(items: list[Item], annotator: str, seed: int = 0) -> list[dict]:
    """Unlabelled items this annotator has not annotated yet, in an annotator-specific random order."""
    todo = [it for it in items if it.gold is None and all(a.annotator != annotator for a in it.annotations)]
    todo.sort(key=lambda it: it.id)
    random.Random(f"{seed}:{annotator}").shuffle(todo)  # different order per annotator limits copying/anchoring
    return [{"id": it.id, "language": it.language, "text": it.text,
             "urls": " ".join(u.raw for u in it.urls), "label": "", "category": "", "confidence": "",
             "evidence": "", "note": ""} for it in todo]


def _spans(text: str, cell: str) -> list[Span]:
    """Evidence cell format: `type: exact phrase | type: exact phrase`."""
    spans = []
    for part in filter(None, (p.strip() for p in cell.split("|"))):
        kind, _, phrase = part.partition(":")
        phrase = phrase.strip()
        start = text.find(phrase)
        if start < 0:
            start = text.lower().find(phrase.lower())
        if not phrase or start < 0:
            raise ValueError(f"evidence phrase {phrase!r} not found in text")
        spans.append(Span(start=start, end=start + len(phrase), type=kind.strip()))
    return spans


def import_sheet(items: list[Item], rows: list[dict], annotator: str, guideline_version: str,
                 on: date | None = None) -> tuple[list[Item], list[str]]:
    by_id = {it.id: it for it in items}
    errors, updates = [], {}
    for n, row in enumerate(rows, start=2):  # row 1 is the header
        item = by_id.get(row.get("id", ""))
        if item is None:
            errors.append(f"row {n}: unknown id {row.get('id')!r}")
            continue
        if not row.get("label", "").strip():
            continue  # not annotated yet; leave for a later import
        if row.get("text") != item.text:
            errors.append(f"row {n} ({item.id}): text was edited in the sheet; annotate the original")
            continue
        if any(a.annotator == annotator for a in item.annotations):
            errors.append(f"row {n} ({item.id}): {annotator} already annotated this item")
            continue
        try:
            ann = Annotation(annotator=annotator, label=row["label"].strip(),
                             category=row.get("category", "").strip() or None,
                             confidence=int(row.get("confidence") or 0),
                             evidence=_spans(item.text, row.get("evidence", "")),
                             guideline_version=guideline_version, note=row.get("note", "").strip(), at=on)
        except ValidationError as e:  # subclass of ValueError, so it must come first
            errors.append(f"row {n} ({item.id}): {_first(e)}")
            continue
        except ValueError as e:
            errors.append(f"row {n} ({item.id}): {e}")
            continue
        updates[item.id] = item.model_copy(update={"annotations": [*item.annotations, ann]})
    if errors:
        return items, errors  # all-or-nothing: a sheet with any error changes nothing
    return [updates.get(it.id, it) for it in items], []


def resolve(items: list[Item], min_annotations: int = 2,
            basis: dict[str, str] | None = None) -> tuple[list[Item], list[dict]]:
    """Set gold where annotators fully agree; return adjudication rows for every disagreement.

    `basis` maps item id → ground-truth basis recorded at intake (default annotator_judgment).
    """
    basis = basis or {}
    out, adjudicate = [], []
    for it in items:
        anns = it.annotations
        if it.gold is not None or len(anns) < min_annotations:
            out.append(it)
            continue
        if len({(a.label, a.category) for a in anns}) == 1:
            a = anns[0]
            gold = Gold(label=a.label, category=a.category, basis=basis.get(it.id, "annotator_judgment"),
                        evidence=a.evidence)
            out.append(it.model_copy(update={"gold": gold}))
        else:
            out.append(it)
            adjudicate.append({"id": it.id, "text": it.text,
                               "annotations": " ; ".join(f"{a.annotator}={a.label}/{a.category or '-'}"
                                                         f" (conf {a.confidence})" for a in anns),
                               "final_label": "", "final_category": "",
                               "basis": basis.get(it.id, "annotator_judgment"), "rationale": ""})
    return out, adjudicate


def apply_adjudication(items: list[Item], rows: list[dict], adjudicator: str) -> tuple[list[Item], list[str]]:
    by_id = {it.id: it for it in items}
    errors, updates = [], {}
    for n, row in enumerate(rows, start=2):
        item = by_id.get(row.get("id", ""))
        if item is None:
            errors.append(f"row {n}: unknown id {row.get('id')!r}")
            continue
        if not row.get("final_label", "").strip():
            errors.append(f"row {n} ({item.id}): no final_label; adjudicate every row or remove it")
            continue
        if any(a.annotator == adjudicator for a in item.annotations):
            errors.append(f"row {n} ({item.id}): {adjudicator} annotated this item and cannot adjudicate it")
            continue
        try:
            gold = Gold(label=row["final_label"].strip(), category=row.get("final_category", "").strip() or None,
                        basis=row.get("basis", "").strip() or "annotator_judgment", adjudicated=True,
                        rationale=f"[{adjudicator}] {row.get('rationale', '').strip()}" if row.get("rationale", "").strip() else "")
            updates[item.id] = Item.model_validate({**item.model_dump(), "gold": gold.model_dump()})
        except ValidationError as e:
            errors.append(f"row {n} ({item.id}): {_first(e)}")
    if errors:
        return items, errors
    return [updates.get(it.id, it) for it in items], []


def pseudo_id(kind: str, value: str, key: bytes) -> str:
    """Dataset-wide stable token for a scammer identifier; the real value is never stored."""
    kind = kind.upper()
    if kind == "PHONE":
        norm = re.sub(r"\D", "", normalise_digits(value))[-10:]  # ९८७… and ９８７… give the same token
    else:
        norm = value.strip().lower()
    if not norm:
        raise ValueError("empty identifier")
    return f"{kind}_{hmac.new(key, f'{kind}:{norm}'.encode(), hashlib.sha256).hexdigest()[:12]}"


class CsvEncodingError(ValueError):
    """The CSV is not UTF-8 (e.g. saved by Excel as 'CSV (Comma delimited)', which uses the ANSI code page)."""


def read_csv(path: Path) -> list[dict]:
    """Rows with write_csv's formula escaping undone (and only that escaping)."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            return [{k: unescape_cell(v) for k, v in r.items()} for r in csv.DictReader(f)]
    except UnicodeError as e:
        raise CsvEncodingError(
            f"{path} is not UTF-8 ({e.reason} at byte {e.start}). Re-save it as UTF-8: in Excel use File > Save As > "
            "'CSV UTF-8 (Comma delimited)'; Google Sheets downloads are always UTF-8. Re-saving cannot restore "
            "characters an earlier non-UTF-8 save already replaced (e.g. Devanagari shown as '?'): re-export from "
            "the original file instead.") from None


# Spreadsheet apps execute cells starting with these as formulas (CSV/formula injection).
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def escape_cell(value) -> object:
    """Prefix a quote so spreadsheets show formula-like text as text; a leading quote is doubled so it survives."""
    if isinstance(value, str) and value.startswith(_FORMULA_START + ("'",)):
        return "'" + value
    return value


def unescape_cell(value):
    """Undo exactly what escape_cell added. If the app already dropped the quote, the value is returned as is."""
    if isinstance(value, str) and value.startswith("'") and value[1:].startswith(_FORMULA_START + ("'",)):
        return value[1:]
    return value


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows({k: escape_cell(v) for k, v in r.items()} for r in rows)


def _first(e: ValidationError) -> str:
    err = e.errors()[0]
    loc = ".".join(str(p) for p in err["loc"])
    return f"{loc + ': ' if loc else ''}{err['msg']}"
