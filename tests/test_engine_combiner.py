"""Verdict-combiner invariants, checked exhaustively over random signal sets and model results."""

from hypothesis import given
from hypothesis import strategies as st

from scamcheck.engine.combiner import combine
from scamcheck.engine.models import VERDICTS, ModelEvidence, ModelResult, Signal

signals = st.lists(st.builds(
    Signal, id=st.sampled_from(["R-X", "U-Y", "I-Z"]), severity=st.sampled_from(["HIGH", "MEDIUM", "LOW"]),
    source=st.sampled_from(["rule", "url", "input"]), blocks_reassurance=st.booleans()), max_size=6)
models = st.builds(
    ModelResult,
    status=st.sampled_from(["ok", "not_configured", "not_opted_in", "timeout", "error", "invalid_output",
                            "skipped_residual_pii"]),
    label=st.sampled_from([None, "scam", "not_scam", "unsure"]),
    evidence=st.lists(st.builds(ModelEvidence, quote=st.text(min_size=1, max_size=10)), max_size=2))


@given(signals, models, st.booleans())
def test_verdict_is_one_of_three(sig, model, urls):
    assert combine(sig, model, unverified_urls=urls).verdict in VERDICTS


@given(signals, models, st.booleans())
def test_high_signal_cannot_be_overruled(sig, model, urls):
    if any(s.severity == "HIGH" for s in sig):
        assert combine(sig, model, unverified_urls=urls).verdict == "LIKELY_SCAM"


@given(signals, models, st.booleans())
def test_no_strong_signals_needs_every_check_quiet(sig, model, urls):
    d = combine(sig, model, unverified_urls=urls)
    if d.verdict == "NO_STRONG_SIGNALS":
        assert model.status == "ok" and model.label == "not_scam"
        assert all(s.severity == "LOW" and not s.blocks_reassurance for s in sig)
        assert not urls


@given(signals, st.sampled_from(["not_configured", "not_opted_in", "timeout", "error", "invalid_output",
                                 "skipped_residual_pii"]), st.booleans())
def test_model_failure_behaves_like_no_model(sig, status, urls):
    failed = combine(sig, ModelResult(status=status, label="not_scam"), unverified_urls=urls)
    absent = combine(sig, ModelResult(status="not_configured"), unverified_urls=urls)
    assert failed.verdict == absent.verdict
    assert failed.verdict != "NO_STRONG_SIGNALS"


@given(signals, st.booleans())
def test_without_model_engine_abstains_unless_high(sig, urls):
    d = combine(sig, ModelResult(status="not_configured"), unverified_urls=urls)
    assert d.verdict == ("LIKELY_SCAM" if any(s.severity == "HIGH" for s in sig) else "UNCLEAR")


def test_model_scam_needs_a_grounded_quote():
    no_quote = combine([], ModelResult(status="ok", label="scam", evidence=[]), unverified_urls=False)
    assert no_quote.verdict == "UNCLEAR" and "model_scam_without_grounded_quote" in no_quote.reasons
    quoted = combine([], ModelResult(status="ok", label="scam", evidence=[ModelEvidence(quote="pay")]),
                     unverified_urls=False)
    assert quoted.verdict == "LIKELY_SCAM"


def test_model_not_scam_with_quiet_checks_is_the_only_reassurance():
    assert combine([], ModelResult(status="ok", label="not_scam"), unverified_urls=False).verdict == "NO_STRONG_SIGNALS"
    low = [Signal(id="R-URGENCY", severity="LOW", source="rule")]
    assert combine(low, ModelResult(status="ok", label="not_scam"), unverified_urls=False).verdict == "NO_STRONG_SIGNALS"
    assert combine(low, ModelResult(status="ok", label="unsure"), unverified_urls=False).verdict == "UNCLEAR"
