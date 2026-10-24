import json

import pytest

from conftest import VALID

from scamcheck.cli import main
from scamcheck.data.report import build_report, cohen_kappa


def test_cohen_kappa_known_values():
    assert cohen_kappa([]) is None
    assert cohen_kappa([("scam", "scam"), ("legitimate", "legitimate")]) == 1.0
    # 2x2 table a=20,b=5,c=10,d=15 -> po=0.70, pe=0.50, kappa=0.40
    pairs = [("s", "s")] * 20 + [("s", "l")] * 5 + [("l", "s")] * 10 + [("l", "l")] * 15
    assert cohen_kappa(pairs) == pytest.approx(0.40)


def test_report_flags_synthetic_and_has_no_results(items):
    text = build_report(items)
    assert "no model performance results" in text
    assert "20 of 20 items are SYNTHETIC" in text
    assert "| scam | 10 |" in text  # 11 scam fixtures minus the pending fx-018
    for word in ("accuracy", "precision", "recall", "f1"):
        assert word not in text.lower()


def test_end_to_end_cli(tmp_path, capsys):
    grouped, review, manifest = tmp_path / "g.jsonl", tmp_path / "pairs.jsonl", tmp_path / "m.json"
    out = tmp_path / "report.md"
    assert main(["group", str(VALID), "--out", str(grouped), "--review", str(review)]) == 0
    assert main(["split", str(grouped), "--out", str(manifest), "--allow-synthetic-in-test"]) == 0
    assert main(["check-leakage", str(grouped), "--manifest", str(manifest)]) == 0
    assert main(["report", str(grouped), "--manifest", str(manifest), "--review", str(review), "--out", str(out)]) == 0
    report = out.read_text(encoding="utf-8")
    assert "Leakage check" in report and "PASS" in report
    assert "WARNING:** this manifest allowed synthetic items in the test split" in report
    m = json.loads(manifest.read_text(encoding="utf-8"))
    assert m["params"]["allow_synthetic_in_test"] is True
