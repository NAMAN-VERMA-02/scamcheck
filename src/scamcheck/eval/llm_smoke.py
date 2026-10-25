"""B3 smoke test: does the configured LLM endpoint answer, in the expected format, and how fast?

Inputs are ONLY the built-in synthetic demo examples (`scamcheck.examples`); there is no way to pass other text,
so no real message can reach a provider through this command. It measures plumbing (status, format, latency,
grounding), not accuracy: the examples are few, synthetic and hand-picked, so no score is computed from them.
"""

from __future__ import annotations

import statistics
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlsplit

from ..engine.llm import PROMPT_ID, PROMPT_VERSION, ChatAdapter, classify
from ..engine.parse import parse
from ..engine.redact import redact
from ..examples import EXAMPLES

SMOKE_VERSION = "llm-smoke-1"
_B3 = {"scam": "LIKELY_SCAM", "not_scam": "NO_STRONG_SIGNALS"}


def _config(adapter: ChatAdapter) -> dict:
    """What was called, without credentials: scheme/host/port/path only, and whether a key was set."""
    url = getattr(adapter, "url", None)
    parts = urlsplit(url) if url else None
    return {
        "endpoint": f"{parts.scheme}://{parts.hostname}{f':{parts.port}' if parts.port else ''}{parts.path}"
                    if parts else None,
        "endpoint_is_local": bool(parts and parts.hostname in ("localhost", "127.0.0.1", "::1")),
        "model": getattr(adapter, "model", None), "timeout_s": getattr(adapter, "timeout", None),
        "temperature": 0, "api_key_set": bool(getattr(adapter, "api_key", None)),
    }


def run_smoke(adapter: Optional[ChatAdapter]) -> dict:
    base = {"smoke_version": SMOKE_VERSION, "prompt_version": PROMPT_VERSION, "prompt_id": PROMPT_ID,
            "inputs": "built-in synthetic demo examples only",
            "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if adapter is None:
        return {**base, "status": "skipped", "model_id": None, "cases": [],
                "reason": "no LLM endpoint configured (set SCAMCHECK_LLM_BASE_URL and SCAMCHECK_LLM_MODEL); "
                          "nothing was sent and no result was produced"}
    cases = []
    for ex in EXAMPLES:
        if "Synthetic" not in ex["note"]:  # defence in depth: the example list must stay synthetic
            raise ValueError(f"example {ex['id']} is not marked synthetic; refusing to send it")
        redacted, residual = redact(parse(ex["text"]).text)
        if residual:
            cases.append({"example_id": ex["id"], "status": "skipped_residual_pii", "latency_ms": None})
            continue
        start = time.perf_counter()
        r = classify(adapter, redacted)
        cases.append({"example_id": ex["id"], "language": ex["language"], "status": r.status,
                      "error_type": r.error_type, "label": r.label, "b3_verdict": _B3.get(r.label or "", "UNCLEAR"),
                      "grounded_quotes": len(r.evidence), "dropped_quotes": r.dropped_evidence,
                      "latency_ms": round((time.perf_counter() - start) * 1000)})
    called = [c for c in cases if c["latency_ms"] is not None]
    lat = sorted(c["latency_ms"] for c in called)
    statuses: dict[str, int] = {}
    for c in cases:
        statuses[c["status"]] = statuses.get(c["status"], 0) + 1
    return {**base, "status": "ok" if statuses == {"ok": len(cases)} else "completed_with_errors",
            "model_id": adapter.model_id, "config": _config(adapter), "statuses": statuses,
            "latency_ms": {"n": len(lat), "median": statistics.median(lat) if lat else None,
                           "max": lat[-1] if lat else None},
            "cases": cases}
