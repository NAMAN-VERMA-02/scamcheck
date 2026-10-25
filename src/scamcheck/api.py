"""HTTP API for the Research Workbench. Run: `uvicorn scamcheck.api:app` from the repository root.

Privacy: request bodies are never stored or logged. The only log line per request is method, path, status and
latency. Validation errors are returned without echoing the submitted input.
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .engine import ENGINE_VERSION, VERSIONS, analyse
from .engine.llm import from_env
from .engine.models import Analysis
from .engine.parse import MAX_TEXT_CHARS, MAX_URL_CHARS
from .examples import EXAMPLES

MAX_BODY_BYTES = 32_000
REPORTS_DIR = Path(os.environ.get("SCAMCHECK_REPORTS_DIR", "reports"))
REPORTS = {"benchmark": "benchmark/synthetic/benchmark.json", "robustness": "robustness/synthetic/robustness.json"}
RATE_PER_MINUTE = int(os.environ.get("SCAMCHECK_RATE_PER_MINUTE", "20"))     # analyses per client per minute
LLM_DAILY_CALLS = int(os.environ.get("SCAMCHECK_LLM_DAILY_CALLS", "200"))   # model calls per UTC day, all clients

log = logging.getLogger("scamcheck.api")
app = FastAPI(title="ScamCheck Research Workbench API", version=ENGINE_VERSION,
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)


class RateLimiter:
    """Sliding one-minute window per client address, held in memory only (addresses are never logged).

    shortcut: per process; with several workers or hosts, move this to the reverse proxy or a shared store.
    """

    def __init__(self, per_minute: int, max_clients: int = 10_000):
        self.per_minute, self.max_clients = per_minute, max_clients
        self.hits: dict[str, deque] = defaultdict(deque)

    def allow(self, client: str, now: float) -> tuple[bool, int]:
        q = self.hits[client]
        while q and now - q[0] >= 60:
            q.popleft()
        if len(q) >= self.per_minute:
            return False, max(1, math.ceil(60 - (now - q[0])))
        q.append(now)
        if len(self.hits) > self.max_clients:  # bound memory: forget clients idle for a minute
            for k in [k for k, v in self.hits.items() if not v or now - v[-1] >= 60]:
                del self.hits[k]
        return True, 0


class LLMBudgetExhausted(RuntimeError):
    """Raised instead of calling the model once today's budget is used; classify() then fails closed."""


class BudgetedAdapter:
    """Caps model calls per UTC day across all clients, so a public instance cannot run up an unbounded bill."""

    def __init__(self, inner, daily_calls: int, today=lambda: datetime.now(timezone.utc).date()):
        self.inner, self.model_id, self.daily_calls, self._today = inner, inner.model_id, daily_calls, today
        self.day, self.used = None, 0

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def complete(self, system: str, user: str) -> str:
        if self._today() != self.day:
            self.day, self.used = self._today(), 0
        if self.used >= self.daily_calls:
            raise LLMBudgetExhausted
        self.used += 1
        return self.inner.complete(system, user)


_inner = from_env()
_MODEL = BudgetedAdapter(_inner, LLM_DAILY_CALLS) if _inner else None
_LIMITER = RateLimiter(RATE_PER_MINUTE)


class AnalyseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    url: Optional[str] = Field(None, max_length=MAX_URL_CHARS)
    language: Literal["english", "hinglish"] = "english"
    llm_opt_in: bool = False  # explicit, per request; ignored when no model is configured

    @field_validator("text")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be blank")
        return v


@app.middleware("http")
async def _guard_and_log(request: Request, call_next):
    start = time.perf_counter()
    length = request.headers.get("content-length")
    allowed, retry = True, 0
    if request.method == "POST" and request.url.path == "/api/analyse":
        allowed, retry = _LIMITER.allow(request.client.host if request.client else "unknown", time.monotonic())
    if length is not None and (not length.isdigit() or int(length) > MAX_BODY_BYTES):
        response = JSONResponse({"detail": "request body too large"}, status_code=413)
    elif not allowed:
        response = JSONResponse({"detail": "rate limit exceeded; try again shortly"}, status_code=429,
                                headers={"Retry-After": str(retry)})
    else:
        response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    log.info("%s %s %s %.0fms", request.method, request.url.path, response.status_code,
             (time.perf_counter() - start) * 1000)
    return response


@app.exception_handler(RequestValidationError)
async def _validation_error(request: Request, exc: RequestValidationError):
    # FastAPI's default echoes the submitted value; drop it so error responses never repeat a message.
    errors = [{"loc": list(e.get("loc", [])), "msg": e.get("msg", ""), "type": e.get("type", "")} for e in exc.errors()]
    return JSONResponse({"detail": errors}, status_code=422)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "versions": VERSIONS, "llm_configured": _MODEL is not None,
            "llm_model_id": _MODEL.model_id if _MODEL else None, "rate_limit_per_minute": _LIMITER.per_minute}


@app.post("/api/analyse", response_model=Analysis)
def analyse_endpoint(req: AnalyseRequest) -> Analysis:
    try:
        return analyse(req.text, url=req.url, language=req.language, model=_MODEL, llm_opt_in=req.llm_opt_in)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/api/examples")
def examples() -> list[dict]:
    return EXAMPLES


@app.get("/api/reports/{name}")
def report(name: Literal["benchmark", "robustness"]) -> dict:
    path = REPORTS_DIR / REPORTS[name]
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{name} report not generated yet; see README")
    return json.loads(path.read_text(encoding="utf-8"))
