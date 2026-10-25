"""HTTP API: validation, bounds, response shape, and privacy (no message text in logs, responses or files)."""

import logging

import pytest
from fastapi.testclient import TestClient

import scamcheck.api as api
from scamcheck.engine.models import Analysis
from scamcheck.engine.parse import MAX_TEXT_CHARS

client = TestClient(api.app)
MARKER = "zqxj-unique-marker-9876543210"


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok" and "rules" in r.json()["versions"]


def test_analyse_returns_a_valid_analysis():
    r = client.post("/api/analyse", json={"text": "Please share the OTP you received", "language": "hinglish"})
    assert r.status_code == 200
    a = Analysis.model_validate(r.json())
    assert a.verdict == "LIKELY_SCAM" and a.language == "hinglish"
    assert "probability" not in r.text and "confidence" not in r.text
    assert r.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("body", [
    {}, {"text": ""}, {"text": "   "}, {"text": "x" * (MAX_TEXT_CHARS + 1)}, {"text": 5},
    {"text": "hi", "language": "french"}, {"text": "hi", "extra": 1}, {"text": "hi", "url": "u" * 3000},
])
def test_invalid_requests_are_rejected(body):
    assert client.post("/api/analyse", json=body).status_code == 422


def test_malformed_json_and_oversized_bodies():
    assert client.post("/api/analyse", content=b"{not json", headers={"content-type": "application/json"}
                       ).status_code == 422
    big = b'{"text": "' + b"a" * 40_000 + b'"}'
    assert client.post("/api/analyse", content=big, headers={"content-type": "application/json"}).status_code == 413


def test_validation_errors_do_not_echo_input():
    r = client.post("/api/analyse", json={"text": MARKER, "language": "french"})
    assert r.status_code == 422 and MARKER not in r.text


def test_no_message_text_reaches_logs_or_disk(caplog, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    caplog.set_level(logging.DEBUG)
    r = client.post("/api/analyse", json={"text": f"Call {MARKER} and share your OTP", "url": f"http://{MARKER}.xyz"})
    assert r.status_code == 200
    assert MARKER not in caplog.text and "OTP" not in caplog.text
    assert any("/api/analyse" in rec.getMessage() for rec in caplog.records)
    assert list(tmp_path.iterdir()) == []


def test_examples_are_labelled_synthetic():
    ex = client.get("/api/examples").json()
    assert ex and all("Synthetic" in e["note"] for e in ex)


def test_reports_are_served_or_404(monkeypatch, tmp_path):
    r = client.get("/api/reports/benchmark")
    assert r.status_code in (200, 404)
    monkeypatch.setattr(api, "REPORTS_DIR", tmp_path)
    assert client.get("/api/reports/robustness").status_code == 404
    assert client.get("/api/reports/../../etc").status_code in (404, 422)


@pytest.fixture(autouse=True)
def fresh_limiter(monkeypatch):
    monkeypatch.setattr(api, "_LIMITER", api.RateLimiter(10_000))


def test_rate_limit_returns_429_with_retry_after(monkeypatch):
    monkeypatch.setattr(api, "_LIMITER", api.RateLimiter(3))
    codes = [client.post("/api/analyse", json={"text": "hello"}).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    r = client.post("/api/analyse", json={"text": "hello"})
    assert r.status_code == 429 and int(r.headers["retry-after"]) >= 1 and "hello" not in r.text
    assert client.get("/api/health").status_code == 200          # only analysis is limited


def test_limiter_window_slides_and_clients_are_separate():
    lim = api.RateLimiter(2)
    assert lim.allow("a", 0)[0] and lim.allow("a", 1)[0] and not lim.allow("a", 2)[0]
    assert lim.allow("b", 2)[0]
    assert lim.allow("a", 61)[0]                                    # the first hit has left the window


class _Model:
    model_id = "fake:budget"

    def complete(self, system, user):
        return '{"label": "not_scam", "evidence": []}'


def test_llm_budget_fails_closed_and_resets_daily(monkeypatch):
    from datetime import date

    from scamcheck.engine import analyse
    day = {"d": date(2026, 10, 25)}
    budget = api.BudgetedAdapter(_Model(), daily_calls=1, today=lambda: day["d"])
    first = analyse("Mom, reached the hostel.", model=budget, llm_opt_in=True)
    assert first.model.status == "ok" and first.verdict == "NO_STRONG_SIGNALS"
    second = analyse("Mom, reached the hostel.", model=budget, llm_opt_in=True)
    assert second.model.status == "error" and second.model.error_type == "LLMBudgetExhausted"
    assert second.verdict == "UNCLEAR"                              # never reassurance without the model
    day["d"] = date(2026, 10, 26)
    assert analyse("Mom, reached the hostel.", model=budget, llm_opt_in=True).model.status == "ok"
