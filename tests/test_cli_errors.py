"""User mistakes must produce a one-line error and exit code 2, never a traceback (Phase 1.5 smoke test)."""

import pytest

from conftest import VALID

from scamcheck.cli import main


def run(capsys, *argv):
    code = main(list(argv))
    err = capsys.readouterr().err
    return code, err


def test_missing_input_file(capsys, tmp_path):
    code, err = run(capsys, "validate", str(tmp_path / "items.jsonl"))
    assert code == 2
    assert "not found" in err and "items.jsonl" in err


def test_split_before_group(capsys, tmp_path):
    code, err = run(capsys, "split", str(VALID), "--out", str(tmp_path / "m.json"))
    assert code == 2
    assert "scamcheck group" in err
    assert not (tmp_path / "m.json").exists()


@pytest.mark.parametrize("content", ["{}", "not json", '{"items": "x", "params": {}}'])
def test_malformed_manifest(capsys, tmp_path, content):
    grouped = tmp_path / "g.jsonl"
    assert main(["group", str(VALID), "--out", str(grouped), "--review", str(tmp_path / "p.jsonl")]) == 0
    capsys.readouterr()
    bad = tmp_path / "bad.json"
    bad.write_text(content, encoding="utf-8")
    code, err = run(capsys, "check-leakage", str(grouped), "--manifest", str(bad))
    assert code == 2
    assert "manifest" in err


def test_group_creates_missing_review_directory(tmp_path):
    review = tmp_path / "pilot" / "new" / "pairs.jsonl"
    assert main(["group", str(VALID), "--out", str(tmp_path / "g.jsonl"), "--review", str(review)]) == 0
    assert review.exists()


def test_schema_check_reports_missing_file_not_stale(capsys, tmp_path):
    code = main(["schema", "--check", "--out", str(tmp_path / "item.schema.json")])
    out = capsys.readouterr().out
    assert code == 1
    assert "does not exist" in out and "stale" not in out
