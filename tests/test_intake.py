"""Collector intake CSV and the missed-redaction safety net.

Rows here are invented test inputs. They use source_type "donated" because intake only accepts real-world sources,
so they carry source_name "unit-test-only-not-real" and consent_id "c-0000" (reserved for tests); they exist only in tmp dirs.
"""

import pytest

from scamcheck.cli import main
from scamcheck.data.io import load_items
from scamcheck.data.pilot import INTAKE_COLUMNS, intake_from_rows, read_csv, write_csv

from conftest import VALID


def row(**over):
    base = {"id": "sy-0001", "text": "Your KYC is pending, update at hxxps://kyc-upd[.]in now", "channel": "sms",
            "language": "english", "script": "latin", "sender_type": "phone", "sender_value": "<PHONE>",
            "urls": "hxxps://kyc-upd[.]in", "registered_domains": "kyc-upd.in", "scammer_ids": "",
            "source_type": "donated", "source_name": "unit-test-only-not-real", "source_url": "",
            "licence": "consent-v1", "licence_verified": "no", "consent_id": "c-0000",
            "collected_at": "2026-10-25", "redaction_version": "r1",
            "redaction_checked_by": "R2", "basis": ""}
    return {**base, **over}


# Pattern coverage (positive and negative) lives in tests/test_pii.py.

def test_committed_fixtures_raise_no_pii_warnings():
    assert not [w for w in load_items(VALID).warnings if "unredacted" in w]


def test_intake_template_matches_columns():
    from pathlib import Path
    template = Path(__file__).parent.parent / "docs" / "templates" / "intake_template.csv"
    with open(template, encoding="utf-8-sig") as f:
        assert f.readline().strip().split(",") == INTAKE_COLUMNS


def test_intake_rows_build_items_and_basis():
    items, basis, err = intake_from_rows([row(), row(id="sy-0002", urls="", registered_domains="", basis="sender_verified")])
    assert err == []
    assert [it.id for it in items] == ["sy-0001", "sy-0002"]
    assert items[0].urls[0].registered_domain == "kyc-upd.in" and items[0].gold is None
    assert basis == {"sy-0002": "sender_verified"}


@pytest.mark.parametrize("bad, needle", [
    ({"registered_domains": ""}, "pair them by position"),
    ({"licence_verified": "maybe"}, "yes or no"),
    ({"consent_id": ""}, "consent_id"),
    ({"basis": "gut_feeling"}, "unknown basis"),
    ({"source_type": "public_dataset", "licence": "Unknown", "source_url": "https://example.invalid/x"},
     "not recognised"),
    ({"source_type": "synthetic"}, "real-world sources only"),
    ({"sender_value": "+919876543210"}, "must be redacted"),  # review H1: real sender number
])
def test_intake_rejects_bad_rows_all_or_nothing(bad, needle):
    items, basis, err = intake_from_rows([row(id="sy-0009"), row(**bad)])
    assert any(needle in e for e in err), err
    assert items == [] and basis == {}


def test_cli_intake_blocks_identifier_hidden_in_url_query(tmp_path, capsys):
    # review H1: this exact row passed intake with zero warnings before the fix
    csv_path = tmp_path / "in.csv"
    write_csv(csv_path, [row(text="Your KYC is pending", urls="hxxps://kyc[.]in/?ph=9876543210&mail=a.b@gmail.com",
                             registered_domains="kyc.in")], INTAKE_COLUMNS)
    out = tmp_path / "items.jsonl"
    code = main(["pilot-intake", str(csv_path), "--out", str(out), "--basis-out", str(tmp_path / "b.csv"),
                 "--log", str(tmp_path / "log.jsonl")])
    err = capsys.readouterr().err
    assert code == 1 and not out.exists()
    assert "[urls.0.raw]" in err and "phone number" in err and "email address" in err


def test_intake_rejects_duplicate_ids():
    _, _, err = intake_from_rows([row(), row()])
    assert any("duplicate id" in e for e in err)


def test_cli_intake_blocks_pii_refuses_overwrite_and_basis_reaches_gold(tmp_path, capsys):
    csv_path, out, basis, log = (tmp_path / n for n in ("in.csv", "items.jsonl", "basis.csv", "log.jsonl"))
    write_csv(csv_path, [row(text="Call 98765 43210 to update KYC", urls="", registered_domains="")], INTAKE_COLUMNS)
    args = ["pilot-intake", str(csv_path), "--out", str(out), "--basis-out", str(basis), "--log", str(log)]
    assert main(args) == 1 and not out.exists()
    assert "possible unredacted phone number" in capsys.readouterr().err

    write_csv(csv_path, [row(basis="donor_confirmed")], INTAKE_COLUMNS)
    assert main(args) == 0 and out.exists()
    assert main(args) == 2  # never overwrites
    assert "already exists" in capsys.readouterr().err

    from scamcheck.data.io import write_items
    from scamcheck.data.schema import Annotation
    items = load_items(out).items
    ann = [Annotation(annotator=a, label="scam", category="bank_kyc_impersonation", confidence=3,
                      guideline_version="g1") for a in ("A1", "A2")]
    write_items(out, [items[0].model_copy(update={"annotations": ann})])
    assert main(["pilot-resolve", str(out), "--out", str(out), "--adjudication", str(tmp_path / "adj.csv"),
                 "--basis", str(basis), "--log", str(log)]) == 0
    assert load_items(out).items[0].gold.basis == "donor_confirmed"
    assert read_csv(basis) == [{"id": "sy-0001", "basis": "donor_confirmed"}]
