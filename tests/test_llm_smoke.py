"""LLM smoke workflow: skipped without an endpoint; records ids, config, latency and error types; synthetic only.

The HTTP tests talk to a stub server on 127.0.0.1 started by the test, never to a real provider.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import scamcheck.eval.llm_smoke as smoke
from scamcheck.cli import main
from scamcheck.engine.llm import PROMPT_ID, OpenAICompatibleAdapter
from scamcheck.examples import EXAMPLES


class Fake:
    model_id = "fake:smoke"
    url = "https://user:secret@llm.example/v1/chat/completions?key=abc"
    model, timeout, api_key = "m", 5.0, "sk-not-a-real-key"

    def __init__(self):
        self.calls = 0

    def complete(self, system, user):
        self.calls += 1
        if self.calls == 2:
            raise ConnectionRefusedError("boom: contains prompt text")
        if self.calls == 3:
            return "not json"
        return json.dumps({"label": "unsure", "evidence": []})


def test_skipped_without_endpoint(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("SCAMCHECK_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("SCAMCHECK_LLM_MODEL", raising=False)
    out = tmp_path / "smoke.json"
    assert main(["llm-smoke", "--out", str(out)]) == 0
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert rec["status"] == "skipped" and rec["cases"] == [] and rec["model_id"] is None
    assert rec["prompt_id"] == PROMPT_ID and "SKIPPED" in capsys.readouterr().err


def test_records_ids_config_latency_and_error_types_without_secrets():
    rec = smoke.run_smoke(Fake())
    assert rec["status"] == "completed_with_errors" and rec["model_id"] == "fake:smoke"
    assert rec["prompt_id"] == PROMPT_ID and rec["smoke_version"] == smoke.SMOKE_VERSION
    assert len(rec["cases"]) == len(EXAMPLES)
    by_status = {c["status"] for c in rec["cases"]}
    assert {"ok", "error", "invalid_output"} <= by_status
    err = next(c for c in rec["cases"] if c["status"] == "error")
    assert err["error_type"] == "ConnectionRefusedError" and err["b3_verdict"] == "UNCLEAR"
    assert all(isinstance(c["latency_ms"], int) for c in rec["cases"])
    text = json.dumps(rec)
    assert "secret" not in text and "sk-not-a-real-key" not in text and "key=abc" not in text and "boom" not in text
    assert rec["config"]["endpoint"] == "https://llm.example/v1/chat/completions"
    assert rec["config"]["api_key_set"] is True and rec["config"]["endpoint_is_local"] is False


def test_refuses_non_synthetic_inputs(monkeypatch):
    monkeypatch.setattr(smoke, "EXAMPLES", [{"id": "real-1", "text": "hi", "language": "english", "note": ""}])
    with pytest.raises(ValueError, match="not marked synthetic"):
        smoke.run_smoke(Fake())


@pytest.fixture
def stub_server():
    state = {"delay": 0.0, "body": json.dumps({"choices": [{"message": {"content": json.dumps(
        {"label": "scam", "evidence": [{"quote": "UPI PIN", "reason": "r"}]})}}]})}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            time.sleep(state["delay"])
            body = state["body"].encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except OSError:
                pass  # the client may already have timed out

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv, state
    srv.shutdown()


def test_real_http_round_trip_to_local_stub(stub_server):
    srv, _ = stub_server
    rec = smoke.run_smoke(OpenAICompatibleAdapter(f"http://127.0.0.1:{srv.server_port}/v1", "stub-model"))
    assert rec["config"]["endpoint_is_local"] and rec["model_id"] == "openai-compatible:stub-model"
    upi = next(c for c in rec["cases"] if c["example_id"] == "ex-upi-hi")
    assert upi["status"] == "ok" and upi["grounded_quotes"] == 1 and upi["b3_verdict"] == "LIKELY_SCAM"
    others = [c for c in rec["cases"] if c["example_id"] != "ex-upi-hi" and c["status"] == "ok"]
    assert all(c["dropped_quotes"] == 1 for c in others)   # the stub's quote is not in those messages


def test_timeout_is_recorded_as_timeout(stub_server):
    srv, state = stub_server
    state["delay"] = 1.0
    adapter = OpenAICompatibleAdapter(f"http://127.0.0.1:{srv.server_port}/v1", "stub-model", timeout=0.2)
    rec = smoke.run_smoke(adapter)
    assert rec["statuses"].get("timeout", 0) >= 1 and rec["status"] == "completed_with_errors"
    assert all(c["b3_verdict"] == "UNCLEAR" for c in rec["cases"] if c["status"] == "timeout")
