"""`scamcheck` command line: validate → group → split → check-leakage → report, plus analyse/benchmark/robustness."""

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
from .data.pii import scan_item
from .data.pilot import (
    ADJ_COLUMNS,
    SHEET_COLUMNS,
    CsvEncodingError,
    apply_adjudication,
    export_sheet,
    import_sheet,
    intake_from_rows,
    pseudo_id,
    read_csv,
    resolve,
    write_csv,
)
from .data.report import build_report
from .data.schema import RECORDED_PERMISSIONS, Item, load_register
from .data.split import TemporalSplitError, check_leakage, split_items


def _load_or_exit(path: str):
    res = load_items(Path(path))
    if res.errors:
        print(f"{path}: {len(res.errors)} error(s)", file=sys.stderr)
        for e in res.errors:
            print(f"  ERROR {e}", file=sys.stderr)
        sys.exit(1)
    return res


class UsageError(Exception):
    """A mistake in how the command was called or in its input files; reported without a traceback."""


def _load_manifest(path: str) -> dict:
    try:
        m = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise UsageError(f"manifest {path} is not valid JSON ({e.msg}); regenerate it with `scamcheck split`")
    if not (isinstance(m, dict) and isinstance(m.get("items"), list) and isinstance(m.get("params"), dict)):
        raise UsageError(f"manifest {path} is not a `scamcheck split` manifest (needs 'items' and 'params')")
    return m


def _write_json(path: str, obj) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    # LF on every OS, so manifests and reports are byte-identical wherever they are regenerated.
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


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
    Path(a.review).parent.mkdir(parents=True, exist_ok=True)
    with open(a.review, "w", encoding="utf-8", newline="\n") as f:
        for p in pairs:
            f.write(json.dumps(p.to_json()) + "\n")
    n_groups = len({it.campaign_id for it in grouped})
    pending = sum(p.status == "needs_review" for p in pairs)
    print(f"{len(grouped)} items → {n_groups} groups; {len(pairs)} candidate pairs ({pending} need review) → {a.review}")
    return 0


def cmd_split(a) -> int:
    res = _load_or_exit(a.file)
    if any(it.campaign_id is None for it in res.items):
        raise UsageError(f"{a.file} has items without campaign_id; run `scamcheck group` first and split its --out file")
    cutoff = None
    if a.temporal_cutoff:
        try:
            cutoff = date.fromisoformat(a.temporal_cutoff)
        except ValueError:
            raise UsageError(f"--temporal-cutoff must be a date like 2026-12-31, got {a.temporal_cutoff!r}")
    try:
        manifest = split_items(res.items, seed=a.seed, allow_synthetic_in_test=a.allow_synthetic_in_test,
                               temporal_cutoff=cutoff)
    except TemporalSplitError as e:
        raise UsageError(f"temporal split not possible: {e} No manifest was written.")
    _write_json(a.out, manifest)
    print(f"split counts {manifest['counts']}, excluded {len(manifest['excluded'])} → {a.out}")
    if "temporal" in manifest:
        t = manifest["temporal"]
        print(f"temporal hold-out: train/dev up to {t['train_dev_latest']}, test campaigns reach past {t['cutoff']}; "
              f"{len(t['straddling_campaigns'])} campaign(s) straddle the cutoff and were placed wholly in test")
    return 0


def cmd_check_leakage(a) -> int:
    res = _load_or_exit(a.file)
    manifest = _load_manifest(a.manifest)
    problems = check_leakage(res.items, manifest, a.threshold, load_decisions(a.decisions))
    for p in problems:
        print(f"LEAK  {p}")
    print("leakage check: " + ("PASS" if not problems else f"FAIL ({len(problems)})"))
    return 1 if problems else 0


def cmd_report(a) -> int:
    res = _load_or_exit(a.file)
    manifest = _load_manifest(a.manifest) if a.manifest else None
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


def _pii_gate(a, before: list, after: list) -> list[str] | None:
    """New possible-PII warnings introduced by this step (all fields scanned). None means: stop, nothing written."""
    old = {w for it in before for w in scan_item(it)}
    new = [w for it in after for w in scan_item(it) if w not in old]
    for w in new:
        print(f"WARN  {w}", file=sys.stderr)
    if new and not a.allow_pii_warnings:
        print("nothing written; fix redaction, or re-run with --allow-pii-warnings after a human checked each one",
              file=sys.stderr)
        return None
    return new


def cmd_pilot_intake(a) -> int:
    if Path(a.out).exists():
        raise UsageError(f"{a.out} already exists; intake never overwrites (it may hold annotations)")
    items, basis, errors = intake_from_rows(read_csv(Path(a.csv)))
    for e in errors:
        print(f"ERROR {e}", file=sys.stderr)
    if errors:
        print("nothing written; fix the intake CSV and re-run", file=sys.stderr)
        return 1
    pii = _pii_gate(a, [], items)
    if pii is None:
        return 1
    write_items(Path(a.out), items)
    write_csv(Path(a.basis_out), [{"id": k, "basis": v} for k, v in sorted(basis.items())], ["id", "basis"])
    _audit(a, [a.csv], [a.out, a.basis_out], items=len(items), pii_warnings=len(pii))
    print(f"{len(items)} item(s) → {a.out}; basis for {len(basis)} → {a.basis_out}")
    return 0


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
    pii = _pii_gate(a, res.items, items)  # annotator notes are free text too
    if pii is None:
        return 1
    write_items(Path(a.out), items)
    added = sum(len(n.annotations) - len(o.annotations) for n, o in zip(items, res.items))
    _audit(a, [a.file, a.sheet], [a.out], annotator=a.annotator, guideline=a.guideline, annotations_added=added,
           pii_warnings=len(pii))
    print(f"imported {added} annotation(s) from {a.annotator} → {a.out}")
    return 0


def cmd_pilot_resolve(a) -> int:
    res = _load_or_exit(a.file)
    basis = {r["id"]: r["basis"] for r in read_csv(Path(a.basis))} if a.basis else {}
    items, adj = resolve(res.items, basis=basis)
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
    pii = _pii_gate(a, res.items, items)  # adjudication rationales are free text too
    if pii is None:
        return 1
    write_items(Path(a.out), items)
    _audit(a, [a.file, a.sheet], [a.out], adjudicator=a.adjudicator, pii_warnings=len(pii))
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
        if not path.exists():
            print(f"{path} does not exist; run from the repository root or pass --out <path to item.schema.json>")
            return 1
        ok = path.read_text(encoding="utf-8") == generated
        print("schema up to date" if ok else f"{path} is stale; run `scamcheck schema --out {path}`")
        return 0 if ok else 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generated, encoding="utf-8")
    print(f"schema → {path}")
    return 0


def cmd_analyse(a) -> int:
    from .engine import analyse
    from .engine.llm import from_env

    text = sys.stdin.read() if a.text == "-" else a.text
    model = from_env() if a.llm_opt_in else None
    if a.llm_opt_in and model is None:
        raise UsageError("--llm-opt-in needs SCAMCHECK_LLM_BASE_URL and SCAMCHECK_LLM_MODEL to be set")
    try:
        res = analyse(text, url=a.url, language=a.language, model=model, llm_opt_in=a.llm_opt_in)
    except ValueError as e:
        raise UsageError(str(e))
    print(res.model_dump_json(indent=2))
    return 0


def _eval_inputs(a):
    res = _load_or_exit(a.file)
    if any(it.campaign_id is None for it in res.items):
        raise UsageError(f"{a.file} has items without campaign_id; run `scamcheck group` and `split` first")
    manifest = _load_manifest(a.manifest)
    problems = check_leakage(res.items, manifest, DEFAULT_THRESHOLD)
    if problems:
        raise UsageError(f"leakage check failed ({len(problems)} problem(s)); run `scamcheck check-leakage`")
    model = None
    if a.with_llm:
        from .engine.llm import CachedAdapter, from_env
        model = from_env()
        if model is None:
            raise UsageError("--with-llm needs SCAMCHECK_LLM_BASE_URL and SCAMCHECK_LLM_MODEL to be set")
        model = CachedAdapter(model)  # B3 and B4 see the same answer per message
    return res.items, manifest, model


def cmd_benchmark(a) -> int:
    from .eval.benchmark import run_benchmark, to_markdown

    items, manifest, model = _eval_inputs(a)
    result = run_benchmark(items, manifest, split=a.split, seed=a.seed, dataset_path=Path(a.file),
                           manifest_path=Path(a.manifest), model=model)
    out = Path(a.out_dir)
    _write_json(str(out / "benchmark.json"), result)
    (out / "benchmark.md").write_text(to_markdown(result), encoding="utf-8", newline="\n")
    for name, s in result["systems"].items():
        o = s["metrics"]["overall"]
        print(f"{name:12} recall {o['scam_recall']['rate']}  dangerous-miss {o['dangerous_miss_rate']['rate']}  "
              f"false-alarm {o['false_alarm_rate_legitimate']['rate']}  unclear {o['unclear_rate_non_ambiguous']['rate']}")
    print(f"{result['meta']['data_label']}\nreport → {out / 'benchmark.md'}")
    return 0


def cmd_robustness(a) -> int:
    from .eval.mutate import replay
    from .eval.robustness import run_robustness, to_markdown

    items, manifest, model = _eval_inputs(a)
    if a.replay:
        records = [json.loads(line) for line in Path(a.replay).read_text(encoding="utf-8").splitlines() if line.strip()]
        problems = replay(records, {it.id: it.text for it in items})
        for p in problems:
            print(f"REPLAY  {p}")
        print(f"replayed {len(records)} variant(s): " + ("PASS" if not problems else f"FAIL ({len(problems)})"))
        return 1 if problems else 0
    reviews = _load_reviews(a.reviews) if a.reviews else []
    result, records = run_robustness(items, manifest, seeds=tuple(a.seeds), model=model, reviews=reviews)
    out = Path(a.out_dir)
    _write_json(str(out / "robustness.json"), result)
    (out / "robustness.md").write_text(to_markdown(result), encoding="utf-8", newline="\n")
    with open(out / "variants.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps(result["meta"]["counts"]))
    for name, s in result["systems"].items():
        tag = " (provisional: unvalidated families)" if s["consistency_provisional"] else ""
        print(f"{name:12} consistency {s['consistency_preserving']['rate']}{tag}  "
              f"parent-scam→NO_STRONG_SIGNALS {s['parent_scam_moved_to_no_strong_signals']['rate']}  "
              f"confirmed-label scam→NO_STRONG_SIGNALS {s['scam_flip_to_no_strong_signals']['rate']}")
    print(f"{result['meta']['data_label']}\nreport → {out / 'robustness.md'}")
    return 0


def _load_jsonl(path: str) -> list[dict]:
    try:
        return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    except json.JSONDecodeError as e:
        raise UsageError(f"{path} is not valid JSONL ({e.msg} on line {e.lineno})")


def _load_reviews(path: str) -> list[dict]:
    from .eval.review import LABELS, MEANING

    reviews = _load_jsonl(path)
    for n, r in enumerate(reviews, start=1):
        if not (r.get("variant_id") and r.get("reviewer") and r.get("meaning_preserved") in MEANING
                and r.get("label", "scam") in LABELS):
            raise UsageError(f"{path} line {n}: a review needs variant_id, reviewer, meaning_preserved "
                             f"({'/'.join(MEANING)}) and an optional label ({'/'.join(LABELS)}); "
                             "create it with `scamcheck review-import`")
    return reviews


def cmd_review_sheet(a) -> int:
    from .data.pilot import write_csv
    from .eval.review import SHEET_COLUMNS, export_sheet

    res = _load_or_exit(a.file)
    records = _load_jsonl(a.variants)
    rows = export_sheet(records, {it.id: it.text for it in res.items}, _load_reviews(a.reviews) if a.reviews else [],
                        a.per_family, a.seed)
    write_csv(Path(a.out), rows, SHEET_COLUMNS)
    print(f"{len(rows)} variant(s) across {len({r['transform'] for r in rows})} famil(ies) → {a.out}. Fill "
          "meaning_preserved (yes/no/unsure) for every row, and label for meaning-changing families.")
    return 0


def cmd_review_import(a) -> int:
    from .data.pilot import read_csv
    from .eval.review import import_sheet

    existing = _load_reviews(a.out) if Path(a.out).exists() else []
    new, errors = import_sheet(read_csv(Path(a.sheet)), _load_jsonl(a.variants), a.reviewer, existing, date.today())
    for e in errors:
        print(f"ERROR {e}", file=sys.stderr)
    if errors:
        print(f"nothing imported ({len(errors)} error(s))", file=sys.stderr)
        return 1
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "a", encoding="utf-8", newline="\n") as f:
        for r in new:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"appended {len(new)} review decision(s) by {a.reviewer} → {a.out}")
    return 0


def cmd_external(a) -> int:
    from .engine.llm import from_env
    from .eval.external import ExternalCheckError, run_check, write_plan

    try:
        if a.cmd == "external-plan":
            model = from_env() if a.with_llm else None
            if a.with_llm and model is None:
                raise UsageError("--with-llm needs SCAMCHECK_LLM_BASE_URL and SCAMCHECK_LLM_MODEL to be set")
            plan = write_plan(Path(a.raw), Path("."), Path(a.register), Path(a.plan), Path(a.log), date.today(),
                              model)
            print(f"plan → {a.plan}: {plan['selection']['counts']} in {plan['selection']['campaigns']} campaigns, "
                  f"frozen {plan['frozen']['sha256'][:12]}"
                  + (f", model {plan['model']['model_id']}" if plan["model"] else "")
                  + ". Commit the plan, then run `scamcheck external-run` once.")
        else:
            planned = Path(a.plan).exists() and json.loads(Path(a.plan).read_text(encoding="utf-8")).get("model")
            res = run_check(Path(a.raw), Path("."), Path(a.register), Path(a.plan), Path(a.out_dir), Path(a.log),
                            date.today(), from_env() if planned else None)
            print(f"{res['meta']['data_label']}\nresults → {Path(a.out_dir) / 'results.md'}")
    except ExternalCheckError as e:
        raise UsageError(str(e))
    return 0


def cmd_llm_smoke(a) -> int:
    from .engine.llm import from_env
    from .eval.llm_smoke import run_smoke

    try:
        adapter = from_env()
    except ValueError as e:
        raise UsageError(str(e))
    result = run_smoke(adapter)
    if a.out:
        _write_json(a.out, result)
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))
    if result["status"] == "skipped":
        print("SKIPPED: " + result["reason"], file=sys.stderr)
    return 1 if result["status"] == "completed_with_errors" else 0


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
    s.add_argument("--temporal-cutoff", metavar="YYYY-MM-DD",
                   help="temporal hold-out: campaigns with any item collected after this date form the test split; "
                        "earlier campaigns are split train/dev")
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
    s = sub.add_parser("pilot-intake", help="convert the collector's intake CSV into unlabelled items")
    s.add_argument("csv")
    s.add_argument("--out", required=True, help="items JSONL to create (never overwritten)")
    s.add_argument("--basis-out", required=True, help="CSV of id,basis for pilot-resolve --basis")
    s.add_argument("--allow-pii-warnings", action="store_true",
                   help="write even if redaction warnings remain (only after a human checked each one)")
    s.add_argument("--log", default=log_default)
    s.set_defaults(fn=cmd_pilot_intake)

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
    s.add_argument("--allow-pii-warnings", action="store_true",
                   help="import even if notes look like they contain identifiers (only after a human checked)")
    s.add_argument("--log", default=log_default)
    s.set_defaults(fn=cmd_pilot_import)

    s = sub.add_parser("pilot-resolve", help="set gold on agreements, write an adjudication sheet for disagreements")
    s.add_argument("file")
    s.add_argument("--out", required=True)
    s.add_argument("--adjudication", required=True)
    s.add_argument("--basis", help="id,basis CSV written by pilot-intake")
    s.add_argument("--log", default=log_default)
    s.set_defaults(fn=cmd_pilot_resolve)

    s = sub.add_parser("pilot-adjudicate", help="apply a filled adjudication sheet (all-or-nothing)")
    s.add_argument("file")
    s.add_argument("--sheet", required=True)
    s.add_argument("--adjudicator", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--allow-pii-warnings", action="store_true",
                   help="apply even if rationales look like they contain identifiers (only after a human checked)")
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

    s = sub.add_parser("analyse", help="analyse one message with the evidence-first engine (prints JSON)")
    s.add_argument("text", help="message text, or - to read stdin")
    s.add_argument("--url", help="an extra URL to analyse statically (never fetched)")
    s.add_argument("--language", choices=["english", "hinglish"], default="english")
    s.add_argument("--llm-opt-in", action="store_true",
                   help="send the REDACTED text to the configured LLM endpoint (SCAMCHECK_LLM_*)")
    s.set_defaults(fn=cmd_analyse)

    for name, fn in (("benchmark", cmd_benchmark), ("robustness", cmd_robustness)):
        s = sub.add_parser(name, help="run baselines B0–B4 on a split" if name == "benchmark"
                           else "seeded mutation lab on dev/test parents")
        s.add_argument("file", help="grouped items JSONL")
        s.add_argument("--manifest", required=True)
        s.add_argument("--out-dir", required=True)
        s.add_argument("--with-llm", action="store_true",
                       help="include the configured LLM (B3, and B4 with model); sends redacted dataset text")
        if name == "benchmark":
            s.add_argument("--split", choices=["dev", "test"], default="test")
            s.add_argument("--seed", type=int, default=13, help="bootstrap and B2 seed")
        else:
            s.add_argument("--seeds", type=int, nargs="+", default=[11, 23, 37])
            s.add_argument("--reviews", help="review decisions JSONL written by `scamcheck review-import`")
            s.add_argument("--replay", help="variants.jsonl to regenerate and verify by hash")
        s.set_defaults(fn=fn)

    s = sub.add_parser("review-sheet", help="CSV of sampled mutation variants for human meaning review (mr1)")
    s.add_argument("file", help="grouped items JSONL (for parent texts)")
    s.add_argument("--variants", required=True, help="variants.jsonl from `scamcheck robustness`")
    s.add_argument("--out", required=True)
    s.add_argument("--per-family", type=int, default=30, help="variants sampled per transform family")
    s.add_argument("--seed", type=int, default=1)
    s.add_argument("--reviews", help="existing decisions; already-reviewed variants are not sampled again")
    s.set_defaults(fn=cmd_review_sheet)

    s = sub.add_parser("review-import", help="validate a filled review sheet and append decisions (all-or-nothing)")
    s.add_argument("--sheet", required=True)
    s.add_argument("--variants", required=True)
    s.add_argument("--reviewer", required=True)
    s.add_argument("--out", required=True, help="review decisions JSONL (appended)")
    s.set_defaults(fn=cmd_review_import)

    ext = "data/raw/external/bolewara-hinglish-scam-text-dataset.json"
    for name, helptext in (("external-plan", "freeze and log the one-shot external-author check (docs/EXTERNAL_CHECK.md)"),
                           ("external-run", "run the committed external-author check once")):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("--raw", default=ext, help="downloaded data.json at the pinned revision (kept out of git)")
        s.add_argument("--register", default="data/source_register.csv")
        s.add_argument("--plan", default="reports/external/bolewara/plan.json")
        s.add_argument("--log", default="reports/test_runs.md")
        if name == "external-run":
            s.add_argument("--out-dir", default="reports/external/bolewara")
        else:
            s.add_argument("--with-llm", action="store_true",
                           help="pin the configured SCAMCHECK_LLM_* model in the plan (adds B3 and B4 with model)")
        s.set_defaults(fn=cmd_external)

    s = sub.add_parser("llm-smoke", help="B3 smoke test on the built-in SYNTHETIC examples only (status, latency, "
                                         "errors; no accuracy)")
    s.add_argument("--out", help="write the full JSON record here")
    s.set_defaults(fn=cmd_llm_smoke)

    a = p.parse_args(argv)
    try:
        register = Path("data/source_register.csv")  # run from the repository root, like every other path
        if register.exists():
            load_register(register)
        else:
            RECORDED_PERMISSIONS.clear()  # no register → no permission counts as granted
        return a.fn(a)
    except FileNotFoundError as e:
        print(f"error: file not found: {e.filename}", file=sys.stderr)
    except PermissionError as e:  # on Windows, a CSV open in Excel is locked
        print(f"error: cannot access {e.filename}; close it in Excel or any other program and re-run",
              file=sys.stderr)
    except (UsageError, CsvEncodingError) as e:
        print(f"error: {e}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
