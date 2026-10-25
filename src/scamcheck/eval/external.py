"""External-author check: the hand-written Hinglish part of bolewara/hinglish-scam-text-dataset (CC-BY-4.0).

Why: every other number in this repository comes from messages written by the author of the rule pack. This set
was written by someone else, so it tests whether the rules transfer beyond their author's phrasing. It is still
SYNTHETIC and small (35 scam / 28 benign per its card): it is not real-world evidence and not a protocol test run
(docs/EVALUATION_PROTOCOL.md §4 requires real data for that).

One-shot procedure (docs/EXTERNAL_CHECK.md):
  1. a human verifies the licence and records it in data/source_register.csv;
  2. `external-plan` selects the rows, freezes code and data by hash, and logs the plan;
  3. the plan is committed (pre-registration);
  4. `external-run` evaluates once and refuses to run again or if anything frozen changed.

Nothing here downloads data, and no message text is ever written out: the source file also contains English
rows derived from UCI SMS Spam, which may hold real personal data. Outputs refer to rows by index only.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import time
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from ..data.io import load_items
from ..data.normalise import content_hash, jaccard, shingles
from ..data.pii import pii_kinds
from ..engine import collect_signals
from ..engine.llm import PROMPT_ID, CachedAdapter, classify
from ..engine.parse import parse
from ..engine.redact import redact
from .baselines import build_systems
from .llm_smoke import _config as model_config
from .metrics import Row, paired_difference, summarise

SOURCE_ID = "src-bolewara-hinglish"
DATASET = "bolewara/hinglish-scam-text-dataset"
REVISION = "743799229923fc80fd7e9f2c764b5e9bd4ab3c9a"   # Hub commit, read 2026-10-25
DOWNLOAD_URL = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/data.json"
REGISTER_STATUS = "PERMITTED-EXTERNAL-EVAL"  # the status prefix a human sets after verifying the licence
EXPECTED = {"scam": 35, "legitimate": 28}    # from the dataset card; any other count stops the plan
SEED = 13

# Selection rule, fixed on 2026-10-25 BEFORE the data was downloaded or read. Rows have no language field, so a
# row counts as Hinglish if it contains Devanagari or at least MIN_MARKERS distinct romanised Hindi words below.
# Two-letter words (ka, ki, ko, se, ho) are left out because they also occur in English SMS slang.
HINGLISH_MARKERS = frozenset("""
hai hain aap aapka aapke aapki aapko apka apke apki apna apne apni karein karo kijiye kariye mein nahi nahin nhi
hoga hogi jayega jayegi raha rahi gaya gayi bhejo bhej paisa paise turant abhi kya liye wala wali aur bhai beta
mummy papa kripya krpya dhanyavaad dhanyawad shukriya aaj yaar accha acha theek thik ghar khata kaise kahan kyun
sabhi tum tera mera meri mere tumhara unko kisi saath jaldi bataye batayein milega milenge jaayega
""".split())
MIN_MARKERS = 2
_DEVANAGARI = re.compile("[ऀ-ॿ]")

# Code and data whose hash is frozen by the plan; any change makes external-run refuse.
FROZEN = ("src/scamcheck/engine", "src/scamcheck/eval/baselines.py", "src/scamcheck/eval/metrics.py",
          "src/scamcheck/eval/external.py", "src/scamcheck/eval/llm_smoke.py", "src/scamcheck/data/normalise.py",
          "benchmarks/synthetic/items.grouped.jsonl", "benchmarks/synthetic/manifest.json")
SYSTEMS = ("B0-unclear", "B0-scam", "B1-rules", "B2-tfidf-lr", "B4-engine")
MODEL_SYSTEMS = ("B3-llm", "B4-engine+llm")  # only when the plan pins a model


class ExternalCheckError(Exception):
    """The check cannot proceed; the message says why and never contains message text."""


def is_hinglish(text: str) -> bool:
    if _DEVANAGARI.search(text):
        return True
    return len(HINGLISH_MARKERS & set(re.findall(r"[a-z]+", text.lower()))) >= MIN_MARKERS


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_rows(raw: Path) -> list[dict]:
    try:
        rows = json.loads(Path(raw).read_text(encoding="utf-8"))["rows"]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise ExternalCheckError(f"{raw} is not the expected format {{'rows': [{{text, label}}]}} ({e})") from None
    for i, r in enumerate(rows):
        if not (isinstance(r, dict) and isinstance(r.get("text"), str) and r.get("label") in (0, 1)):
            raise ExternalCheckError(f"row {i} is not {{text: str, label: 0|1}}")
    return rows


def select(rows: list[dict]) -> list[dict]:
    """Hinglish rows as {row, label, text}; 1 → scam, 0 → legitimate (the card's only two classes)."""
    return [{"row": i, "label": "scam" if r["label"] == 1 else "legitimate", "text": r["text"]}
            for i, r in enumerate(rows) if is_hinglish(r["text"])]


def selection_hash(selected: list[dict]) -> str:
    return _sha(json.dumps([[s["row"], s["label"], _sha(s["text"].encode("utf-8"))] for s in selected]).encode())


def freeze_hash(root: Path) -> str:
    """SHA-256 over the frozen files (path + contents, line endings normalised so Windows and Linux agree)."""
    h = hashlib.sha256()
    for entry in FROZEN:
        p = root / entry
        files = sorted(p.rglob("*.py")) if p.is_dir() else [p]
        for f in files:
            h.update(f.relative_to(root).as_posix().encode() + b"\0")
            h.update(f.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def check_register(register: Path) -> dict:
    with open(register, encoding="utf-8-sig", newline="") as f:
        row = next((r for r in csv.DictReader(f) if r["source_id"] == SOURCE_ID), None)
    if row is None:
        raise ExternalCheckError(f"{SOURCE_ID} is not in {register}")
    if not (row.get("licence_verified_by") or "").strip() or not (row.get("status") or "").startswith(REGISTER_STATUS):
        raise ExternalCheckError(
            f"{SOURCE_ID} is not authorised for this check: a person must read the licence and the dataset card, "
            f"then fill licence_verified_by and set status to start with {REGISTER_STATUS} in {register} "
            "(docs/EXTERNAL_CHECK.md step 1)")
    return {"licence_verified_by": row["licence_verified_by"].strip(), "status": row["status"],
            "verified_on": row.get("verified_on", "")}


def campaigns(texts: list[str], threshold: float = 0.6) -> list[str]:
    """Group exact and near duplicates (as in data/grouping.py) so the bootstrap resamples whole templates."""
    parent = list(range(len(texts)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    hashes, sh = [content_hash(t) for t in texts], [shingles(t) for t in texts]
    for i in range(len(texts)):
        for j in range(i):
            if hashes[i] == hashes[j] or jaccard(sh[i], sh[j]) >= threshold:
                parent[find(i)] = find(j)
    return [f"x-{find(i):04d}" for i in range(len(texts))]


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def plan_committed(root: Path, plan: Path) -> bool:
    """True when the plan is tracked by git and unchanged since its last commit (the pre-registration record)."""
    rel = Path(plan).resolve().relative_to(Path(root).resolve()).as_posix()
    return _git(root, "ls-files", "--error-unmatch", rel).returncode == 0 and \
        _git(root, "diff", "--quiet", "HEAD", "--", rel).returncode == 0


def _log(log: Path, line: str) -> None:
    with open(log, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


def model_digest(model) -> str | None:
    """Ollama's content digest for the pinned model, so a re-pulled or replaced model is detected. Local only."""
    parts = urlsplit(getattr(model, "url", "") or "")
    if parts.hostname not in ("localhost", "127.0.0.1", "::1"):
        return None
    try:
        with urllib.request.urlopen(f"{parts.scheme}://{parts.netloc}/api/tags", timeout=5) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    name = getattr(model, "model", None)
    return next((m.get("digest") for m in tags.get("models", []) if m.get("name") in (name, f"{name}:latest")), None)


def _model_record(model) -> dict:
    return {"model_id": model.model_id, "prompt_id": PROMPT_ID, "config": model_config(model),
            "digest": model_digest(model)}


def make_plan(raw: Path, root: Path, register: Path, today: date, model=None) -> dict:
    authorisation = check_register(register)
    rows = load_rows(raw)
    selected = select(rows)
    counts = dict(Counter(s["label"] for s in selected))
    if counts != EXPECTED:
        raise ExternalCheckError(
            f"the pre-registered selection rule found {counts or 'no rows'}, but the dataset card states {EXPECTED}. "
            "The rule must not be adjusted after seeing the data without recording a deviation; stop and review "
            "(docs/EXTERNAL_CHECK.md, 'If the counts do not match').")
    pii = Counter(k for s in selected for k in pii_kinds(s["text"]))
    commit = _git(root, "rev-parse", "HEAD")
    groups = campaigns([s["text"] for s in selected])
    reading = [
        "Synthetic and small: report as an external-author check only, never as real-world accuracy.",
        "Scam recall (n=35) is interpretable under protocol §5 (n >= 30); legitimate rates (n=28) are counts only.",
        "B4-engine runs in rule-only mode, so it cannot return NO_STRONG_SIGNALS; its legitimate items can only be "
        "LIKELY_SCAM (false alarm) or UNCLEAR.",
        "A B4-engine recall clearly below its own-author synthetic recall (9/12) would indicate the rules are fitted "
        "to their author's phrasing; 'clearly' means the two Wilson intervals do not overlap.",
        "No rule, threshold, prompt or code is changed in response to the result; findings feed the next rule-pack "
        "version, which needs a different evaluation set.",
    ]
    if model is not None:
        reading += [
            "Primary comparison (protocol §6): B4-engine+llm vs B3-llm on dangerous misses and false alarms, paired "
            "campaign bootstrap at 97.5%; a difference is claimed only if its interval excludes 0.",
            "The model is a small local model chosen for privacy and hardware, not for accuracy; B3's result describes "
            "this model and prompt only, not LLMs in general.",
        ]
    return {
        "check": "external-author synthetic check (not real-world evidence, not a protocol test run)",
        "planned_on": today.isoformat(),
        "dataset": {"id": DATASET, "revision": REVISION, "url": DOWNLOAD_URL,
                    "file_sha256": _sha(Path(raw).read_bytes()), "rows_in_file": len(rows), "licence": "CC-BY-4.0",
                    "attribution": "Anuj Bolewar (dataset card)"},
        "authorisation": authorisation,
        "selection": {"rule": f"Devanagari present, or >= {MIN_MARKERS} distinct HINGLISH_MARKERS (fixed before "
                              "the data was seen)", "counts": counts, "rows": [s["row"] for s in selected],
                      "sha256": selection_hash(selected), "campaigns": len(set(groups)),
                      "label_mapping": {"1": "scam", "0": "legitimate"},
                      "identifier_shapes_seen": dict(sorted(pii.items()))},
        "frozen": {"files": list(FROZEN), "sha256": freeze_hash(root),
                   "git_commit": commit.stdout.strip() if commit.returncode == 0 else None},
        "model": _model_record(model) if model is not None else None,
        "systems": list(SYSTEMS) + (list(MODEL_SYSTEMS) if model is not None else []),
        "b2_training": "train split of benchmarks/synthetic (frozen above); never the external rows",
        "seed": SEED,
        "primary": ["scam_recall", "dangerous_miss_rate", "false_alarm_rate_legitimate"],
        "pre_stated_reading": reading,
    }


def write_plan(raw: Path, root: Path, register: Path, plan_path: Path, log: Path, today: date, model=None) -> dict:
    if plan_path.exists():
        raise ExternalCheckError(f"{plan_path} already exists; a plan is written once")
    plan = make_plan(raw, root, register, today, model)
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    s = plan["selection"]
    _log(log, f"| {today.isoformat()} | `{DATASET}` @ {REVISION[:12]} (SYNTHETIC, external author; Hinglish part "
              f"{s['counts']['scam']} scam / {s['counts']['legitimate']} legitimate) | all selected rows | "
              f"{', '.join(plan['systems'])} | frozen {plan['frozen']['sha256'][:12]} | **PLANNED** external-author "
              f"check{'; model ' + plan['model']['model_id'] if plan['model'] else ''}; plan `{plan_path.as_posix()}`. "
              "Must be committed before `external-run`; runs once. |")
    return plan


def run_check(raw: Path, root: Path, register: Path, plan_path: Path, out_dir: Path, log: Path, today: date,
              model=None) -> dict:
    results_path = out_dir / "results.json"
    if results_path.exists():
        raise ExternalCheckError(f"{results_path} exists: this check has already run once and is not repeated")
    if not plan_path.exists():
        raise ExternalCheckError(f"no plan at {plan_path}; run `scamcheck external-plan` first")
    if not plan_committed(root, plan_path):
        raise ExternalCheckError(f"{plan_path} is not committed (or changed since): commit the plan before running, "
                                 "so the pre-registration is on record")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    check_register(register)
    if _sha(Path(raw).read_bytes()) != plan["dataset"]["file_sha256"]:
        raise ExternalCheckError("the data file differs from the one in the plan")
    selected = select(load_rows(raw))
    if selection_hash(selected) != plan["selection"]["sha256"]:
        raise ExternalCheckError("the selected rows differ from the plan")
    if freeze_hash(root) != plan["frozen"]["sha256"]:
        raise ExternalCheckError("frozen code or training data changed since the plan; the check cannot run")
    planned = plan.get("model")
    if bool(planned) != (model is not None):
        raise ExternalCheckError("the plan " + ("names a model but none is configured" if planned else
                                                "has no model but one was given") + "; run exactly as planned")
    if planned:
        if model.model_id != planned["model_id"]:
            raise ExternalCheckError(f"configured model {model.model_id} is not the planned {planned['model_id']}")
        if planned["digest"] and model_digest(model) != planned["digest"]:
            raise ExternalCheckError("the local model's digest changed since the plan (re-pulled or replaced)")

    items = load_items(root / "benchmarks/synthetic/items.grouped.jsonl").items
    manifest = json.loads((root / "benchmarks/synthetic/manifest.json").read_text(encoding="utf-8"))
    split_of = {r["id"]: r["split"] for r in manifest["items"]}
    train = [it for it in items if split_of.get(it.id) == "train" and it.gold.label != "ambiguous"]
    texts, labels = [it.text for it in train], [it.gold.label == "scam" for it in train]
    systems = [s for s in build_systems(texts, labels, SEED) if s.name in SYSTEMS]
    cached = None
    if planned:
        cached = CachedAdapter(model)  # B3 and B4+llm see the same answer for each message
        for s in build_systems(texts, labels, SEED, cached):
            if s.name == "B3-llm":
                systems.append(s)
            elif s.name == "B4-engine":
                s.name = "B4-engine+llm"
                systems.append(s)
    groups = campaigns([s["text"] for s in selected])
    rows_of, results = {}, {}
    started = time.perf_counter()
    for s in systems:
        rows = rows_of[s.name] = [Row(f"row-{x['row']}", x["label"], None, "hinglish", g, s.predict(x["text"]))
                                  for x, g in zip(selected, groups)]
        results[s.name] = {"description": s.description, "metrics": summarise(rows, SEED),
                           "predictions": {r.id: r.verdict for r in rows}}
    elapsed = time.perf_counter() - started

    def errors_for(name: str) -> list[dict]:
        verdicts, out = {r.id: r.verdict for r in rows_of[name]}, []
        for x in selected:
            v = verdicts[f"row-{x['row']}"]
            if (x["label"] == "scam" and v != "LIKELY_SCAM") or (x["label"] == "legitimate" and v == "LIKELY_SCAM"):
                out.append({"row": x["row"], "label": x["label"], "verdict": v,
                            "signals": sorted({sig.id for sig in collect_signals(x["text"])[2]})})
        return out

    comparisons = {f"B4-engine vs {n}": {"role": "exploratory", **paired_difference(rows_of["B4-engine"], rows_of[n],
                                                                                     SEED)}
                   for n in ("B1-rules", "B2-tfidf-lr")}
    model_rows = None
    if planned:
        comparisons["B4-engine+llm vs B3-llm"] = {"role": "primary", **paired_difference(
            rows_of["B4-engine+llm"], rows_of["B3-llm"], SEED, level=0.975)}
        comparisons["B4-engine vs B3-llm"] = {"role": "exploratory", **paired_difference(
            rows_of["B4-engine"], rows_of["B3-llm"], SEED)}
        # Per-row model outcome from the cache (no new calls). Labels and counts only: quotes are message text.
        model_rows = {}
        for x in selected:
            r = classify(cached, redact(parse(x["text"]).text)[0])
            model_rows[f"row-{x['row']}"] = {"status": r.status, "label": r.label, "error_type": r.error_type,
                                             "grounded_quotes": len(r.evidence), "dropped_quotes": r.dropped_evidence}
    out = {
        "meta": {"data_label": "EXTERNAL-AUTHOR SYNTHETIC CHECK. Hand-written by the dataset author, not by the rule "
                               "author; still synthetic and small. Not real-world accuracy.",
                 "plan_sha256": _sha(plan_path.read_bytes()), "ran_on": today.isoformat(),
                 "dataset": plan["dataset"], "frozen": plan["frozen"], "model": planned, "n": len(selected),
                 "campaigns": len(set(groups)), "model_calls": cached.calls if cached else 0,
                 "wall_seconds": round(elapsed, 1)},
        "systems": results,
        "comparisons": comparisons,
        "model_rows": model_rows,
        "errors": {name: errors_for(name) for name in ("B4-engine", "B4-engine+llm") if name in rows_of},
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (out_dir / "results.md").write_text(to_markdown(out), encoding="utf-8", newline="\n")
    summary = "; ".join(
        f"{n} recall {results[n]['metrics']['overall']['scam_recall']['k']}/"
        f"{results[n]['metrics']['overall']['scam_recall']['n']}, false alarms "
        f"{results[n]['metrics']['overall']['false_alarm_rate_legitimate']['k']}/"
        f"{results[n]['metrics']['overall']['false_alarm_rate_legitimate']['n']}"
        for n in ("B4-engine", "B3-llm", "B4-engine+llm") if n in results)
    _log(log, f"| {today.isoformat()} | `{DATASET}` @ {REVISION[:12]} (SYNTHETIC, external author) | all selected "
              f"rows ({len(selected)}) | {', '.join(results)} | frozen {plan['frozen']['sha256'][:12]} | **RUN** once "
              f"as planned. {summary}. Results `{results_path.as_posix()}`. |")
    return out


def to_markdown(res: dict) -> str:
    def pct(m):
        if m["rate"] is None:
            return "n/a"
        return f"{m['k']}/{m['n']} ({m['rate'] * 100:.1f}%, 95% CI {m['lo'] * 100:.1f}–{m['hi'] * 100:.1f})" + \
            ("" if m["interpretable"] else " †")

    m = res["meta"]
    lines = ["# External-author check", "", f"> **{m['data_label']}**", "",
             f"`{m['dataset']['id']}` @ `{m['dataset']['revision']}`, {m['n']} Hinglish rows in {m['campaigns']} "
             f"campaigns. Frozen code `{m['frozen']['sha256'][:12]}` (commit {m['frozen']['git_commit']}). "
             "† = n < 30, counts only.", "",
             "| System | Scam recall | Dangerous misses | False alarms (legitimate) | Unclear (all) |",
             "|---|---|---|---|---|"]
    for name, s in res["systems"].items():
        o = s["metrics"]["overall"]
        lines.append(f"| {name} | {pct(o['scam_recall'])} | {pct(o['dangerous_miss_rate'])} | "
                     f"{pct(o['false_alarm_rate_legitimate'])} | {pct(o['unclear_rate_non_ambiguous'])} |")
    lines += ["", "## Paired comparisons (first − second, campaign bootstrap; negative favours the first)", ""]
    for label, c in res["comparisons"].items():
        if "skipped" in c:
            lines.append(f"- {label} ({c['role']}): skipped — {c['skipped']}")
        else:
            lines.append(f"- {label} ({c['role']}, {c['level'] * 100:g}%): " + "; ".join(
                f"{k} {v['diff'] * 100:+.1f} pts [{v['lo'] * 100:+.1f}, {v['hi'] * 100:+.1f}] → {v['conclusion']}"
                for k, v in c.items() if isinstance(v, dict)))
    if m.get("model"):
        md = m["model"]
        statuses = Counter(r["status"] for r in (res.get("model_rows") or {}).values())
        lines += ["", "## Model", "",
                  f"- `{md['model_id']}` (digest `{(md.get('digest') or 'n/a')[:19]}`), prompt `{md['prompt_id']}`, "
                  f"timeout {md['config'].get('timeout_s')} s, endpoint local: {md['config'].get('endpoint_is_local')}",
                  f"- {m['model_calls']} model calls, shared by B3 and B4+llm; statuses: "
                  + ", ".join(f"{k} {v}" for k, v in sorted(statuses.items())),
                  f"- wall time for all systems: {m['wall_seconds']} s"]
    for name, errs in res["errors"].items():
        lines += ["", f"## {name} misses and false alarms (row index, signals that fired)", ""]
        lines += [f"- row {e['row']} ({e['label']}): {e['verdict']}; signals: {', '.join(e['signals']) or 'none'}"
                  for e in errs] or ["- none"]
    return "\n".join(lines) + "\n"
