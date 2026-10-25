"""The single analysis path shared by the API and the offline benchmark. There is no other scoring code."""

from __future__ import annotations

from typing import Optional

from ..data.pii import pii_kinds
from .combiner import combine
from .explain import GUIDANCE, HEADLINE, explain_signals, notes_for
from .llm import PROMPT_ID, ChatAdapter, classify
from .models import Analysis, ModelResult, Signal
from .parse import parse
from .redact import redact
from .rules import RULE_PACK_VERSION, run_rules
from .urls import NOT_CHECKED, URL_ANALYSER_VERSION, analyse_url, is_official

ENGINE_VERSION = "engine-0.2.0"
VERSIONS = {"engine": ENGINE_VERSION, "rules": RULE_PACK_VERSION, "urls": URL_ANALYSER_VERSION, "prompt": PROMPT_ID}


def collect_signals(text: str, url: Optional[str] = None):
    """Deterministic checks only (input, rules, URL structure). Returns (parsed, url_reports, signals)."""
    parsed = parse(text)
    urls = list(parsed.urls)
    if url and url.strip() and url.strip() not in urls:
        urls.append(url.strip())
    reports, signals = [], []
    if parsed.hidden_chars:
        signals.append(Signal(id="I-HIDDEN-CHARS", severity="MEDIUM", source="input", evidence_type="obfuscation",
                              quote=f"{parsed.hidden_chars} hidden character(s)", blocks_reassurance=True))
    if parsed.confusable_words:
        signals.append(Signal(id="I-CONFUSABLES", severity="MEDIUM", source="input", evidence_type="obfuscation",
                              quote=", ".join(parsed.confusable_words[:5]), blocks_reassurance=True))
    url_signals = []
    for u in urls:
        report, sig = analyse_url(u)
        reports.append(report)
        url_signals += sig
    unofficial = any(not is_official(r.host) for r in reports)
    signals += run_rules(parsed.text, unofficial_link=unofficial) + url_signals
    return parsed, reports, signals


def analyse(text: str, *, url: Optional[str] = None, language: str = "english",
            model: Optional[ChatAdapter] = None, llm_opt_in: bool = False) -> Analysis:
    parsed, reports, signals = collect_signals(text, url)
    if model is None:
        result = ModelResult(status="not_configured")
    elif not llm_opt_in:
        result = ModelResult(status="not_opted_in", model_id=model.model_id, prompt_id=PROMPT_ID)
    else:
        redacted, residual = redact(parsed.text)
        result = (ModelResult(status="skipped_residual_pii", model_id=model.model_id, prompt_id=PROMPT_ID)
                  if residual else classify(model, redacted))
    decision = combine(signals, result, unverified_urls=bool(reports))
    lang = "hinglish" if language == "hinglish" else "english"
    not_checked = (NOT_CHECKED if reports else []) + ["sender identity"]
    return Analysis(
        verdict=decision.verdict, reasons=decision.reasons, headline=HEADLINE[(decision.verdict, lang)],
        signals=explain_signals(signals, lang), urls=reports,
        guidance=notes_for(decision.reasons, lang) + GUIDANCE[(decision.verdict, lang)],
        not_checked=not_checked, pii_detected=pii_kinds(text), model=result, language=lang, versions=VERSIONS)
