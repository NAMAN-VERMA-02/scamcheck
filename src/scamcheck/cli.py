"""`scamcheck` command line: validate → group → split → check-leakage → report."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from .data.grouping import DEFAULT_REVIEW_LOW, DEFAULT_THRESHOLD, group_items, load_decisions
from .data.io import load_items, write_items
from .data.pilot import (ADJ_COLUMNS, SHEET_COLUMNS, apply_adjudication, export_sheet, import_sheet, pseudo_id,
                         read_csv, resolve, write_csv)
from .data.report import build_report
from .data.schema import Item
from .data.split import check_leakage, split_items


def _load_or_exit(path: str):
    res = load_items(Path(path))
    if res.errors:
        print(f"{path}: {len(res.errors)} error(s)", file=sys.stderr)
        for e in res.errors:
            print(f"  ERROR {e}", file=sys.stderr)
        sys.exit(1)
    return res


def _write_json(path: str, obj) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def cmd_validate(a) -> int:
    res = load_items(Path(a.file))
    for e in res.errors:
        print(f"ERROR {e}")
    for w in res.warnings:
        print(f"WARN  {w}")
    print(f"{a.file}: {len(res.items)} valid item(s), {len(res.errors)} error(s), {len(res.warnings)} warning(s)")
    return 1 if res.errors or (a.strict and res.warnings) else 0


def cmd_group(a) -> int:
    res = _load_or_exit(a.file)
    grouped, pairs = group_items(res.items, a.threshold, a.review_low, load_decisions(a.decisions))
    write_items(Path(a.out), grouped)
    with open(a.review, "w", encoding="utf-8", newline="\n") as f:
        for p in pairs:
            f.write(json.dumps(p.to_json()) + "\n")
    n_groups = len({it.campaign_id for it in grouped})
    pending = sum(p.status == "needs_review" for p in pairs)
    print(f"{len(grouped)} items → {n_groups} groups; {len(pairs)} candidate pairs ({pending} need review) → {a.review}")
    return 0


def cmd_split(a) -> int:
    res = _load_or_exit(a.file)
    manifest = split_items(res.items, seed=a.seed, allow_synthetic_in_test=a.allow_synthetic_in_test)
    _write_json(a.out, manifest)
    print(f"split counts {manifest['counts']}, excluded {len(manifest['excluded'])} → {a.out}")
    return 0


def cmd_check_leakage(a) -> int:
    res = _load_or_exit(a.file)
    manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    problems = check_leakage(res.items, manifest, a.threshold, load_decisions(a.decisions))
    for p in problems:
        print(f"LEAK  {p}")
    print("leakage check: " + ("PASS" if not problems else f"FAIL ({len(problems)})"))
    return 1 if problems else 0


def cmd_report(a) -> int:
    res = _load_or_exit(a.file)
    manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8")) if a.manifest else None
    pairs = None
    if a.review and Path(a.review).exists():
        pairs = [json.loads(l) for l in Path(a.review).read_text(encoding="utf-8").splitlines() if l.strip()]
    problems = check_leakage(res.items, manifest, a.threshold, load_decisions(a.decisions)) if manifest else None
    text = build_report(res.items, manifest, pairs, problems)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text + "\n", encoding="utf-8")
        print(f"report → {a.out}")
    else:
        print(text)
    return 0


def _sha(path: str) -> str | None:
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def _audit(a, inputs: list[str], outputs: list[str], **extra) -> None:
    """Append-only, hash-chained log: editing or deleting an earlier line breaks every later `prev`."""
    log = Path(a.log)
    log.parent.mkdir(parents=True, exist_ok=True)
    lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    prev = hashlib.sha256(lines[-1].encode("utf-8")).hexdigest() if lines else None
    entry = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "cmd": a.cmd,
             "inputs": {p: _sha(p) for p in inputs}, "outputs": {p: _sha(p) for p in outputs}, **extra, "prev": prev}
    with open(log, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def cmd_pilot_sheet(a) -> int:
    res = _load_or_exit(a.file)
    rows = export_sheet(res.items, a.annotator, a.seed)
    write_csv(Path(a.out), rows, SHEET_COLUMNS)
    _audit(a, [a.file], [a.out], annotator=a.annotator, rows=len(rows))
    print(f"{len(rows)} items for {a.annotator} → {a.out}")
    return 0


def cmd_pilot_import(a) -> int:
    res = _load_or_exit(a.file)
    items, errors = import_sheet(res.items, read_csv(Path(a.sheet)), a.annotator, a.guideline, date.today())
    for e in errors:
        print(f"ERROR {e}", file=sys.stderr)
    if errors:
        print("nothing imported; fix the sheet and re-run", file=sys.stderr)
        return 1
    write_items(Path(a.out), items)
    added = sum(len(n.annotations) - len(o.annotations) for n, o in zip(items, res.items))
    _audit(a, [a.file, a.sheet], [a.out], annotator=a.annotator, guideline=a.guideline, annotations_added=added)
    print(f"imported {added} annotation(s) from {a.annotator} → {a.out}")
    return 0


def cmd_pilot_resolve(a) -> int:
    res = _load_or_exit(a.file)
    items, adj = resolve(res.items)
    write_items(Path(a.out), items)
    write_csv(Path(a.adjudication), adj, ADJ_COLUMNS)
    agreed = sum(n.gold is not None and o.gold is None for n, o in zip(items, res.items))
    _audit(a, [a.file], [a.out, a.adjudication], agreed=agreed, to_adjudicate=len(adj))
    print(f"gold set on {agreed} agreed item(s); {len(adj)} disagreement(s) → {a.adjudication}")
    return 0


def cmd_pilot_adjudicate(a) -> int:
    res = _load_or_exit(a.file)
    items, errors = apply_adjudication(res.items, read_csv(Path(a.sheet)), a.adjudicator)
    for e in errors:
        print(f"ERROR {e}", file=sys.stderr)
    if errors:
        print("nothing applied; fix the sheet and re-run", file=sys.stderr)
        return 1
    write_items(Path(a.out), items)
    _audit(a, [a.file, a.sheet], [a.out], adjudicator=a.adjudicator)
    print(f"adjudications applied → {a.out}")
    return 0


def cmd_pseudo_id(a) -> int:
    key = os.environ.get("SCAMCHECK_PSEUDO_KEY")
    if not key:
        print("set SCAMCHECK_PSEUDO_KEY (a long random secret kept outside the repo) first", file=sys.stderr)
        return 1
    print(pseudo_id(a.kind, a.value, key.encode("utf-8")))
    return 0


def cmd_schema(a) -> int:
    generated = json.dumps(Item.model_json_schema(), indent=2) + "\n"
    path = Path(a.out)
    if a.check:
        ok = path.exists() and path.read_text(encoding="utf-8") == generated
        print("schema up to date" if ok else f"{path} is stale; run `scamcheck schema --out {path}`")
        return 0 if ok else 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generated, encoding="utf-8")
    print(f"schema → {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252; output contains κ, ≥, →
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="scamcheck")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("validate", help="validate a dataset JSONL file")
    s.add_argument("file")
    s.add_argument("--strict", action="store_true", help="treat warnings as errors")
    s.set_defaults(fn=cmd_validate)

    s = sub.add_parser("group", help="assign duplicate/campaign groups and list near-duplicate pairs")
    s.add_argument("file")
    s.add_argument("--out", required=True, help="grouped items JSONL")
    s.add_argument("--review", required=True, help="near-duplicate candidate pairs JSONL")
    s.add_argument("--decisions", help="reviewer decisions JSONL")
    s.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    s.add_argument("--review-low", type=float, default=DEFAULT_REVIEW_LOW)
    s.set_defaults(fn=cmd_group)

    s = sub.add_parser("split", help="group-aware stratified train/dev/test split")
    s.add_argument("file", help="grouped items JSONL")
    s.add_argument("--out", required=True, help="manifest JSON")
    s.add_argument("--seed", type=int, default=13)
    s.add_argument("--allow-synthetic-in-test", action="store_true",
                   help="pipeline testing only; the manifest and report are marked accordingly")
    s.set_defaults(fn=cmd_split)

    for name, fn in (("check-leakage", cmd_check_leakage), ("report", cmd_report)):
        s = sub.add_parser(name)
        s.add_argument("file", help="grouped items JSONL")
        s.add_argument("--manifest", required=(name == "check-leakage"))
        s.add_argument("--decisions")
        s.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
        if name == "report":
            s.add_argument("--review")
            s.add_argument("--out")
        s.set_defaults(fn=fn)

    log_default = "data/pilot/audit_log.jsonl"
    s = sub.add_parser("pilot-sheet", help="blind annotation sheet (CSV) for one annotator")
    s.add_argument("file")
    s.add_argument("--annotator", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--log", default=log_default)
    s.set_defaults(fn=cmd_pilot_sheet)

    s = sub.add_parser("pilot-import", help="import a filled annotation sheet (all-or-nothing)")
    s.add_argument("file")
    s.add_argument("--sheet", required=True)
    s.add_argument("--annotator", required=True)
    s.add_argument("--guideline", required=True, help="guideline version used, e.g. g1")
    s.add_argument("--out", required=True)
    s.add_argument("--log", default=log_default)
    s.set_defaults(fn=cmd_pilot_import)

    s = sub.add_parser("pilot-resolve", help="set gold on agreements, write an adjudication sheet for disagreements")
    s.add_argument("file")
    s.add_argument("--out", required=True)
    s.add_argument("--adjudication", required=True)
    s.add_argument("--log", default=log_default)
    s.set_defaults(fn=cmd_pilot_resolve)

    s = sub.add_parser("pilot-adjudicate", help="apply a filled adjudication sheet (all-or-nothing)")
    s.add_argument("file")
    s.add_argument("--sheet", required=True)
    s.add_argument("--adjudicator", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--log", default=log_default)
    s.set_defaults(fn=cmd_pilot_adjudicate)

    s = sub.add_parser("pseudo-id", help="stable pseudonymous token for a scammer phone/UPI/email/account")
    s.add_argument("kind", choices=["PHONE", "UPI", "EMAIL", "ACCT"])
    s.add_argument("value")
    s.set_defaults(fn=cmd_pseudo_id)

    s = sub.add_parser("schema", help="export (or --check) the JSON schema generated from the models")
    s.add_argument("--out", default="schema/item.schema.json")
    s.add_argument("--check", action="store_true")
    s.set_defaults(fn=cmd_schema)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
