"""Benchmark metrics, baselines and the committed SYNTHETIC benchmark set."""

import json
from pathlib import Path

import pytest

import scamcheck.eval.baselines as baselines
from scamcheck.data.io import load_items
from scamcheck.data.split import check_leakage
from scamcheck.eval.benchmark import run_benchmark
from scamcheck.eval.metrics import Row, auc, bootstrap, summarise, wilson

ROOT = Path(__file__).parents[1]
BENCH = ROOT / "benchmarks" / "synthetic"


def rows(spec):
    return [Row(f"r{i}", lab, cat, lang, f"c{i}", v) for i, (lab, cat, lang, v) in enumerate(spec)]


def test_wilson_known_values():
    assert wilson(0, 0)["rate"] is None
    w = wilson(0, 10)
    assert w["lo"] == 0.0 and abs(w["hi"] - 0.2775) < 1e-3
    w = wilson(5, 10)
    assert abs(w["lo"] - 0.2366) < 1e-3 and abs(w["hi"] - 0.7634) < 1e-3


def test_hand_computed_metrics():
    rs = rows([("scam", "otp_scam", "english", "LIKELY_SCAM"), ("scam", "x", "hinglish", "NO_STRONG_SIGNALS"),
               ("scam", "x", "hinglish", "UNCLEAR"), ("legitimate", "otp", "english", "LIKELY_SCAM"),
               ("legitimate", "otp", "hinglish", "NO_STRONG_SIGNALS"), ("ambiguous", None, "english", "UNCLEAR")])
    m = summarise(rs, seed=1)
    o = m["overall"]
    assert (o["scam_recall"]["k"], o["scam_recall"]["n"]) == (1, 3)
    assert (o["dangerous_miss_rate"]["k"], o["dangerous_miss_rate"]["n"]) == (1, 3)
    assert (o["false_alarm_rate_legitimate"]["k"], o["false_alarm_rate_legitimate"]["n"]) == (1, 2)
    assert (o["unclear_rate_non_ambiguous"]["k"], o["unclear_rate_non_ambiguous"]["n"]) == (1, 5)
    assert m["false_alarm_by_legit_category"]["otp"]["k"] == 1
    assert m["language_gap_hinglish_minus_english"]["scam_recall"] == -1.0
    assert m["confusion"]["overall"]["scam"] == {"LIKELY_SCAM": 1, "UNCLEAR": 1, "NO_STRONG_SIGNALS": 1}
    assert "skipped" in m["bootstrap"]  # 6 campaigns is too few


def test_bootstrap_is_seeded_and_campaign_level():
    rs = rows([("scam", "x", "english", "LIKELY_SCAM" if i % 3 else "UNCLEAR") for i in range(30)])
    a, b = bootstrap(rs, seed=7, resamples=200), bootstrap(rs, seed=7, resamples=200)
    assert a == b and a["campaigns"] == 30
    assert a["scam_recall"]["lo"] <= 20 / 30 <= a["scam_recall"]["hi"]


def test_auc():
    assert auc([0.9, 0.8, 0.1], [True, True, False])["auc"] == 1.0
    assert auc([0.5, 0.5], [True, False])["auc"] == 0.5
    assert auc([0.1], [True])["auc"] is None


@pytest.fixture(scope="module")
def bench():
    items = load_items(BENCH / "items.grouped.jsonl").items
    manifest = json.loads((BENCH / "manifest.json").read_text(encoding="utf-8"))
    return items, manifest


def test_synthetic_benchmark_matches_its_builder_and_is_leak_free(bench):
    import sys
    sys.path.insert(0, str(BENCH))
    import build  # noqa: E402
    committed = [json.loads(line) for line in (BENCH / "items.jsonl").read_text(encoding="utf-8").splitlines()]
    assert committed == build.build()
    items, manifest = bench
    assert all(it.is_synthetic for it in items)
    assert manifest["params"]["allow_synthetic_in_test"] is True
    assert check_leakage(items, manifest, 0.6) == []


def test_b0_controls_and_b2_trains_on_train_only(bench, monkeypatch):
    items, manifest = bench
    seen = {}
    real = baselines.train_b2

    def spy(texts, labels, seed):
        seen["texts"] = set(texts)
        return real(texts, labels, seed)
    monkeypatch.setattr(baselines, "train_b2", spy)
    res = run_benchmark(items, manifest, split="test", seed=13, dataset_path=BENCH / "items.grouped.jsonl",
                        manifest_path=BENCH / "manifest.json")
    split_of = {r["id"]: r["split"] for r in manifest["items"]}
    train_texts = {it.text for it in items if split_of[it.id] == "train"}
    assert seen["texts"] and seen["texts"] <= train_texts
    b0 = res["systems"]["B0-unclear"]["metrics"]["overall"]
    assert b0["unclear_rate_non_ambiguous"]["rate"] == 1.0 and b0["scam_recall"]["rate"] == 0.0
    assert res["systems"]["B0-scam"]["metrics"]["overall"]["false_alarm_rate_legitimate"]["rate"] == 1.0
    assert "B3-llm" not in res["systems"] and "SYNTHETIC" in res["meta"]["data_label"]
    assert res["meta"]["versions"]["rules"] and res["meta"]["manifest"]["sha256"]


def test_refuses_to_evaluate_on_train(bench):
    items, manifest = bench
    with pytest.raises(ValueError):
        run_benchmark(items, manifest, split="train", seed=1, dataset_path=BENCH / "items.grouped.jsonl",
                      manifest_path=BENCH / "manifest.json")


def test_committed_reports_are_reproducible(bench, tmp_path):
    from scamcheck.cli import main
    main(["benchmark", str(BENCH / "items.grouped.jsonl"), "--manifest", str(BENCH / "manifest.json"),
          "--out-dir", str(tmp_path)])
    committed = json.loads((ROOT / "reports/benchmark/synthetic/benchmark.json").read_text(encoding="utf-8"))
    fresh = json.loads((tmp_path / "benchmark.json").read_text(encoding="utf-8"))
    for d in (committed, fresh):  # environment-specific, not results
        d["meta"]["versions"].pop("python")
        d["meta"]["versions"].pop("scikit-learn")
        for k in ("dataset", "manifest"):
            d["meta"][k].pop("path")
    assert committed == fresh
