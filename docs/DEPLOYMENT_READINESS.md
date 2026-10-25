# Deployment readiness (status as of 2026-10-25)

**Verdict: not ready for public deployment. Do not expose the API beyond `localhost`.** The app is a local research
tool. This checklist states what would have to be true first. Each status is checked against the code, not
assumed.

Legend: ✅ done and tested · ⚠️ partial · ❌ not done.

## 1. Abuse and capacity

| Item | Status | Evidence / what is missing |
|---|---|---|
| Rate limiting per client | ❌ | No limiter exists. Required because a public checker is an **oracle** for scammers testing evasions (PLAN §7) and because LLM calls cost money. Needed: a per-IP and per-session token bucket at the reverse proxy or in-app (e.g. 10 requests/min, 200/day), returning 429 with no detail |
| LLM spend cap | ❌ | No budget guard in code. Needed: a hard monthly cap at the provider **and** an in-app daily call counter that turns model calls off (fail to rule-only, never to reassurance) |
| Request body bound | ✅ | `MAX_BODY_BYTES = 32,000` → 413 (`api.py`; `test_api.py`). A chunked request without `Content-Length` is bounded only by pydantic after parsing. Add a proxy body limit too |
| Text and URL bounds | ✅ | `text` 1–4,000 chars, not blank; `url` ≤ 2,000; unknown fields rejected (`test_invalid_requests_are_rejected`) |
| Model timeout | ✅ | `SCAMCHECK_LLM_TIMEOUT`, default 10 s. A timeout falls back to rule-only (`test_failures_fail_conservatively`) |
| Worker count / regex cost | ⚠️ | Rules are bounded regexes over ≤ 4,000 chars, and a 400-char property test runs fast. No load test or p95 latency measurement yet (PLAN M6: p95 ≤ 6 s) |

## 2. Privacy

| Item | Status | Evidence / what is missing |
|---|---|---|
| No message storage | ✅ | Nothing is written to disk (`test_no_message_text_reaches_logs_or_disk`) |
| App logs exclude content | ✅ | `scamcheck.api` logs method, path, status and latency only |
| Server access logs | ⚠️ | uvicorn's access log records the **client IP**, which is personal data. Run with `--no-access-log` or drop IPs at the proxy, and set a retention period |
| Validation errors don't echo input | ✅ | Custom 422 handler (`test_validation_errors_do_not_echo_input`) |
| `Cache-Control: no-store` | ✅ | Set on every API response |
| Web security headers | ⚠️ | `Referrer-Policy: no-referrer`, `nosniff` and `X-Frame-Options: DENY` are set. No Content-Security-Policy yet |
| TLS | ❌ | Local HTTP only. A deployment needs TLS at the proxy; the API must not be reachable directly |
| Privacy notice | ❌ | No user-facing notice naming the controller, purpose, retention and contact (DPDP; see `docs/PILOT_READINESS.md` §1) |

## 3. LLM provider opt-in

| Item | Status | Evidence / what is missing |
|---|---|---|
| Off by default | ✅ | Requires operator env vars **and** a per-request `llm_opt_in: true` (`test_no_call_without_opt_in`) |
| Informed consent wording | ⚠️ | The UI says identifiers are replaced, that redaction is imperfect, and names the model. It does not yet name the provider's retention policy, because none is recorded |
| Provider retention terms recorded | ❌ | PLAN §7 requires checking and recording the provider's data-use and retention terms before the first call. Not done; no provider chosen |
| Redaction before sending | ✅ | Placeholders, URL query strings stripped, call skipped when residual identifiers remain (`test_only_redacted_text_is_sent`, `test_residual_pii_blocks_the_call`) |
| Endpoint not user-controlled | ✅ | From operator env only; http(s) only; no redirects. There is no outbound lookup adapter, so no SSRF surface |
| Smoke test | ✅ | `scamcheck llm-smoke` uses synthetic examples only and reports `skipped` without an endpoint. Never run against a real provider yet |

## 4. Product safety

| Item | Status | Evidence / what is missing |
|---|---|---|
| No "safe" verdict; reassurance only with a working model and quiet checks | ✅ | Property tests in `test_engine_combiner.py` |
| Rule details not exposed to users | ❌ | PLAN §7 says rule details and scores should not be shown publicly (oracle risk). The research UI shows rule ids and quotes **by design**. A public build would need a reduced view |
| Explanation comprehension test | ❌ | PLAN M6: ≥ 80% of 12 users restate the verdict and next step correctly. Not run |
| Helpline information | ⚠️ | Guidance cites cybercrime.gov.in and 1930 from the research notes. Re-verify before any deployment |

## 5. Operations

| Item | Status | Evidence / what is missing |
|---|---|---|
| CI | ✅ | Lint, schema, tests, report reproduction and frontend build |
| Dependency pinning | ✅ | `uv.lock`, `web/package-lock.json` |
| Monitoring without content | ❌ | No metrics endpoint; needs counts and latency only |
| Incident / takedown contact | ❌ | None published |

## Minimum before any public deployment

1. Rate limiting and an LLM spend cap.
2. TLS proxy; no client IPs in logs.
3. A privacy notice.
4. Provider terms recorded, if a model is enabled.
5. A reduced public view.
6. A p95 latency test.

Until then, run it locally only.
