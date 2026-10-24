"""Regression tests for review findings S1, S2, S4, S5 and S7 (third review of Phase 1.5).

All values are invented. Items carry source_name "unit-test-only-not-real".
"""

import csv

import pytest
from pydantic import ValidationError

import scamcheck.data.schema as schema
from scamcheck.cli import main
from scamcheck.data.io import _warnings, write_items
from scamcheck.data.pii import pii_kinds
from scamcheck.data.schema import Item, load_register

NOT_REAL = {"source_type": "donated", "source_name": "unit-test-only-not-real", "licence": "consent-v1",
            "licence_verified": False, "consent_id": "c-0000", "collected_at": "2026-10-25"}
ADVISORY = {"source_type": "official_advisory", "source_name": "unit-test-only-not-real",
            "source_url": "https://example.invalid/advisory", "collected_at": "2026-10-25"}
GOLD = {"label": "scam", "category": "other_scam", "basis": "annotator_judgment"}


def item(**over):
    base = {"id": "dn-0001", "text": "Your KYC is pending", "channel": "sms", "language": "english",
            "script": "latin", "provenance": NOT_REAL, "redaction": {"version": "r1", "checked_by": "R2"}}
    return Item.model_validate({**base, **over})


@pytest.fixture(autouse=True)
def empty_register(monkeypatch):
    monkeypatch.setattr(schema, "RECORDED_PERMISSIONS", set())


# --- S1: adjacent numbers joined by spacing must not hide each other ------------------------------------

@pytest.mark.parametrize("text", [
    "Call 9876543210 9123456780",                    # review: two phones, one space
    "Call 1800 1234 5678 9876543210",                # review: toll-free then phone
    "9876543210  9123456780",                        # two spaces
    "Rs 500 9876543210",
])
def test_adjacent_numbers_do_not_hide_a_phone(text):
    assert "phone number" in pii_kinds(text), (text, pii_kinds(text))


def test_back_to_back_grouped_phones_are_flagged():
    # Known limitation: reported as a long number rather than "phone number", but never silently passed.
    assert pii_kinds("Numbers 98765 43210 91234 56780") != []


def test_very_long_joined_run_is_flagged_not_ignored():
    assert pii_kinds("ID 1234 5678 9012 3456 7890 12") != []


@pytest.mark.parametrize("text", [                    # S1 fix must not undo earlier false-positive fixes
    "Never share your PIN. Call 1800-1234-5678 for help",
    "Rs 450 debited via UPI/P2M/412345678901/AMAZON",
    "Order ID 6123456789 shipped",
    "Valid till 24-11-26 10:45",
    "Rs 2,500 debited from A/c XX1234 on 12-10-26 to VPA <UPI>.",
])
def test_legitimate_messages_still_pass(text):
    assert pii_kinds(text) == [], (text, pii_kinds(text))


# --- S2: permission-NNNN is releasable only when the register records it as granted ---------------------

def _register(tmp_path, *rows):
    path = tmp_path / "source_register.csv"
    cols = ["source_id", "name", "status", "licence_verified_by"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    return path


def _advisory(licence="permission-0001"):
    return item(id="oa-0001", provenance={**ADVISORY, "licence": licence, "licence_verified": True})


def test_unrecorded_permission_is_not_releasable():
    it = _advisory()
    assert not it.provenance.releasable
    assert "not recorded as granted" in it.provenance.release_blocker


def test_recorded_and_signed_permission_is_releasable(tmp_path):
    load_register(_register(tmp_path, ["permission-0001", "Bank X letter", "PERMITTED: attribution required", "R3"]))
    assert _advisory().provenance.releasable
    assert not _advisory("permission-0002").provenance.releasable  # a different id stays blocked


@pytest.mark.parametrize("row", [
    ["permission-0001", "Bank X letter", "BLOCKED: withdrawn", "R3"],   # not granted
    ["permission-0001", "Bank X letter", "PERMITTED", ""],              # nobody signed it
    ["src-bank-x", "permission-0001 mentioned in name", "PERMITTED", "R3"],  # id must be the source_id
])
def test_permission_rows_that_do_not_grant_are_ignored(tmp_path, row):
    load_register(_register(tmp_path, row))
    assert not _advisory().provenance.releasable


def test_unrecorded_permission_cannot_enter_test_split(tmp_path):
    from scamcheck.data.grouping import group_items
    from scamcheck.data.split import split_items
    it = item(id="oa-0001", provenance={**ADVISORY, "licence": "permission-0001", "licence_verified": True}, gold=GOLD)
    m = split_items(group_items([it])[0], ratios={"train": 0.0, "dev": 0.0, "test": 1.0})
    assert [r["split"] for r in m["items"]] == ["train"]


def test_cli_loads_register_from_repository(tmp_path, monkeypatch, capsys):
    data = tmp_path / "items.jsonl"
    write_items(data, [_advisory()])
    monkeypatch.chdir(tmp_path)
    assert main(["validate", str(data)]) == 0
    assert "not recorded as granted" in capsys.readouterr().out
    (tmp_path / "data").mkdir()
    _register(tmp_path / "data", ["permission-0001", "Bank X letter", "PERMITTED", "R3"])
    assert main(["validate", str(data)]) == 0
    assert "not recorded as granted" not in capsys.readouterr().out


# --- S4: campaign_id has the generated format -------------------------------------------------------------

@pytest.mark.parametrize("bad", ["9876543210", "g-a", "campaign", "g-98765432100"])
def test_campaign_id_must_be_generated_format(bad):
    with pytest.raises(ValidationError, match="campaign_id"):
        item(campaign_id=bad)


def test_phone_shaped_campaign_id_is_caught_by_the_scanner():
    from scamcheck.data.pii import scan_item
    warnings = " ".join(scan_item(item(campaign_id="g-9876543210")))  # valid hex format, so the scan must catch it
    assert "[campaign_id]" in warnings and "phone number" in warnings


def test_generated_campaign_id_is_valid_and_clean():
    from scamcheck.data.pii import scan_item
    assert scan_item(item(campaign_id="g-0d13221ec7")) == []


# --- S5: ids accept ASCII digits only ---------------------------------------------------------------------

@pytest.mark.parametrize("bad", ["dn-٠٠٠١", "dn-०००१", "dn-００１"])
def test_ids_reject_non_ascii_digits(bad):
    with pytest.raises(ValidationError, match="id"):
        item(id=bad)


def test_consent_ids_reject_non_ascii_digits():
    with pytest.raises(ValidationError, match="consent_id"):
        item(provenance={**NOT_REAL, "consent_id": "c-०००१"})


# --- S7: the release warning names the real reason ------------------------------------------------------

@pytest.mark.parametrize("prov, reason", [
    ({**NOT_REAL, "licence_verified": True}, "pending legal review"),
    ({**NOT_REAL, "licence_verified": False}, "licence not verified"),
])
def test_release_warning_names_the_reason(prov, reason):
    warnings = " ".join(_warnings([item(provenance=prov)]))
    assert reason in warnings, warnings


def test_verified_but_pending_donation_is_not_described_as_unverified():
    warnings = " ".join(_warnings([item(provenance={**NOT_REAL, "licence_verified": True})]))
    assert "licence not verified" not in warnings
