"""The verdict combiner: a pure function of signals and the (optional) model result.

Invariants (property-tested in tests/test_engine_combiner.py):
  1. any HIGH signal → LIKELY_SCAM, whatever the model says;
  2. NO_STRONG_SIGNALS needs a working model that said not_scam AND no MEDIUM/HIGH signal AND nothing that blocks
     reassurance AND no URL left unverified — so a model alone can never force it, and rule-only mode never gives it;
  3. a model failure (timeout, error, invalid output) behaves exactly like having no model.
"""

from __future__ import annotations

from .models import Decision, ModelResult, Signal


def combine(signals: list[Signal], model: ModelResult, *, unverified_urls: bool) -> Decision:
    if any(s.severity == "HIGH" for s in signals):
        return Decision(verdict="LIKELY_SCAM", reasons=["high_severity_signal"])
    ok = model.status == "ok"
    if ok and model.label == "scam" and model.evidence:
        return Decision(verdict="LIKELY_SCAM", reasons=["model_grounded_scam"])

    reasons = []
    if not ok:
        reasons.append(f"model_{model.status}")
    elif model.label == "scam":
        reasons.append("model_scam_without_grounded_quote")
    elif model.label != "not_scam":  # "unsure", or a malformed result with no label
        reasons.append("model_unsure")
    if any(s.severity == "MEDIUM" for s in signals):
        reasons.append("medium_signal")
    if any(s.blocks_reassurance for s in signals):
        reasons.append("obfuscation_or_injection")
    if unverified_urls:
        reasons.append("url_destination_not_verified")
    if reasons:
        return Decision(verdict="UNCLEAR", reasons=reasons)
    return Decision(verdict="NO_STRONG_SIGNALS", reasons=["all_checks_quiet"])
