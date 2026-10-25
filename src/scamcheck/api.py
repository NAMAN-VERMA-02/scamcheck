"""HTTP API for the Research Workbench. Run: `uvicorn scamcheck.api:app` from the repository root.

Privacy: request bodies are never stored or logged. The only log line per request is method, path, status and
latency. Validation errors are returned without echoing the submitted input.
"""

from __future__ import annotations

import json
import logging
import os
import time
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

log = logging.getLogger("scamcheck.api")
app = FastAPI(title="ScamCheck Research Workbench API", version=ENGINE_VERSION,
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
_MODEL = from_env()


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
    if length is not None and (not length.isdigit() or int(length) > MAX_BODY_BYTES):
        response = JSONResponse({"detail": "request body too large"}, status_code=413)
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
            "llm_model_id": _MODEL.model_id if _MODEL else None}


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
