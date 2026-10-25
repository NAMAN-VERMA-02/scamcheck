"""Data shapes shared by the engine, the API and the evaluation harness."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

Verdict = Literal["LIKELY_SCAM", "UNCLEAR", "NO_STRONG_SIGNALS"]
VERDICTS: tuple[str, ...] = ("LIKELY_SCAM", "UNCLEAR", "NO_STRONG_SIGNALS")
Severity = Literal["HIGH", "MEDIUM", "LOW"]


class Signal(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str                       # stable rule id, e.g. R-OTP-REQUEST, U-BRAND-LOOKALIKE
    severity: Severity
    source: Literal["rule", "url", "input"]
    evidence_type: Optional[str] = None  # a schema EVIDENCE_TYPES value when one fits
    quote: str = ""               # the exact text that triggered it (from the normalised input)
    start: Optional[int] = None
    end: Optional[int] = None
    # Obfuscation and injection never prove a scam, but they make reassurance unsafe.
    blocks_reassurance: bool = False


class ModelEvidence(BaseModel):
    quote: str
    reason: str = ""


class ModelResult(BaseModel):
    status: Literal["ok", "not_configured", "not_opted_in", "timeout", "error", "invalid_output",
                    "skipped_residual_pii"]
    label: Optional[Literal["scam", "not_scam", "unsure"]] = None
    evidence: list[ModelEvidence] = []   # only quotes found verbatim in the input survive
    dropped_evidence: int = 0            # quotes the model claimed that are not in the input
    model_id: Optional[str] = None
    prompt_id: Optional[str] = None
    error_type: Optional[str] = None     # exception class name only, never its message


class Decision(BaseModel):
    verdict: Verdict
    reasons: list[str]   # machine-readable reason codes, in order of precedence


class UrlReport(BaseModel):
    display: str              # defanged, so the UI never renders a live link
    host: Optional[str]
    registered_domain: Optional[str]
    signal_ids: list[str]
    not_checked: list[str]


class ExplainedSignal(BaseModel):
    id: str
    severity: Severity
    source: str
    title: str
    detail: str
    quote: str
    start: Optional[int] = None
    end: Optional[int] = None


class Analysis(BaseModel):
    verdict: Verdict
    reasons: list[str]
    headline: str
    signals: list[ExplainedSignal]
    urls: list[UrlReport]
    guidance: list[str]
    not_checked: list[str]
    pii_detected: list[str]   # kinds of identifier seen in the input; the input itself is not stored
    model: ModelResult
    language: Literal["english", "hinglish"]
    versions: dict[str, str]
