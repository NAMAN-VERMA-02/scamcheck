import runpy

from conftest import FIXTURES, INVALID, VALID

from scamcheck.cli import main
from scamcheck.data.io import load_items

EXPECTED_ERRORS = {  # line number -> substring of the error that line must produce
    2: "not valid for label",
    3: "consent_id",
    4: "defanged",
    5: "outside the text",
    6: "must be adjudicated",
    7: "requires a synthetic block",
    8: "unknown evidence type",
    9: "must not have a category",
    10: "defanged",
    11: "source_url",
    12: "Extra inputs are not permitted",
    13: "already used on line 1",
    14: "invalid JSON",
}


def test_valid_fixtures_load_cleanly(items):
    assert len(items) == 20
    assert all(it.is_synthetic for it in items)  # fixtures are synthetic by construction


def test_each_invalid_line_fails_for_its_reason():
    res = load_items(INVALID)
    assert [it.id for it in res.items] == ["ok-001"]
    for line, needle in EXPECTED_ERRORS.items():
        hits = [e for e in res.errors if e.startswith(f"line {line}:")]
        assert hits, f"line {line} produced no error"
        assert any(needle in e for e in hits), f"line {line}: {hits}"
    assert {int(e.split(":")[0].split()[1]) for e in res.errors} == set(EXPECTED_ERRORS)


def test_warnings_flag_exact_duplicates_and_pending():
    res = load_items(VALID)
    assert any("exact duplicate text" in w and "fx-008" in w and "fx-009" in w for w in res.warnings)
    assert any(w.startswith("fx-018: no gold") for w in res.warnings)


def test_validate_cli_exit_codes(capsys):
    assert main(["validate", str(VALID)]) == 0
    assert main(["validate", str(VALID), "--strict"]) == 1  # fixtures deliberately contain warnings
    assert main(["validate", str(INVALID)]) == 1


def test_committed_schema_matches_models():
    assert main(["schema", "--check", "--out", str(FIXTURES.parent.parent / "schema" / "item.schema.json")]) == 0


def test_committed_fixtures_match_builder(tmp_path):
    builder = runpy.run_path(str(FIXTURES / "build_fixtures.py"))
    builder["write"](tmp_path / "v.jsonl", builder["VALID"])
    assert (tmp_path / "v.jsonl").read_text(encoding="utf-8") == VALID.read_text(encoding="utf-8")
