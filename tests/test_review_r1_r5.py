"""Regression tests for review findings R1–R5 (second independent review of Phase 1.5).

All values are invented. Items carry source_name "unit-test-only-not-real" and the reserved test consent id c-0000.
"""

import pytest
from pydantic import ValidationError

import scamcheck.data.schema as schema
from scamcheck.data.grouping import group_items
from scamcheck.data.pii import pii_kinds
from scamcheck.data.pilot import intake_from_rows
from scamcheck.data.schema import Item
from scamcheck.data.split import split_items

NOT_REAL = {"source_type": "donated", "source_name": "unit-test-only-not-real", "licence": "consent-v1",
            "licence_verified": False, "consent_id": "c-0000", "collected_at": "2026-10-25"}


def item(**over):
    base = {"id": "dn-0001", "text": "Your KYC is pending", "channel": "sms", "language": "english",
            "script": "latin", "provenance": NOT_REAL, "redaction": {"version": "r1", "checked_by": "R2"}}
    return Item.model_validate({**base, **over})


# --- R1: ids and consent ids have a fixed, non-personal format -------------------------------------

@pytest.mark.parametrize("good", ["dn-0001", "fx-001", "sy-0001", "oa-0042", "bad-001", "ok-001", "pd-123456"])
def test_existing_id_shapes_stay_valid(good):
    item(id=good)


@pytest.mark.parametrize("bad", ["dn-9876543210", "dn-98765-43210", "dn-ravi", "dn-0001x", "DN-0001", "dn-12"])
def test_ids_carrying_phone_numbers_or_names_are_rejected(bad):
    with pytest.raises(ValidationError, match="id"):
        item(id=bad)


@pytest.mark.parametrize("bad", ["9876543210", "c-9876543210", "ravi", "test-only", "c-12"])
def test_consent_ids_must_be_c_nnnn(bad):
    with pytest.raises(ValidationError, match="consent_id"):
        item(provenance={**NOT_REAL, "consent_id": bad})


def test_lineage_references_use_the_id_format():
    with pytest.raises(ValidationError):
        item(id="sy-0002", provenance={**NOT_REAL, "source_type": "synthetic", "licence": "CC0-1.0", "consent_id": None},
             synthetic={"method": "paraphrase", "generator": "t", "seed_id": "dn-9876543210"})


# --- R2: precise exemptions; each paired with a sensitive variant that must still be flagged ---------

@pytest.mark.parametrize("legit, sensitive", [
    # redacted OTP message mentioning an amount  vs  a real OTP next to an amount
    ("<OTP> is OTP for txn of Rs 2,500 at Amazon. Valid 10 mins.", "482913 is OTP for txn of Rs 2,500 at Amazon."),
    ("<OTP> is your OTP for INR 4500 payment", "Your OTP is 482913 for INR 4500 payment"),
    ("<OTP> for ₹1,299.00 order", "OTP 4829 for ₹1,299.00 order"),
    # UPI / IMPS 12-digit RRN in the standard slot  vs  a mobile number in that slot
    ("Rs 450 debited via UPI/P2M/412345678901/AMAZON", "Rs 450 sent via UPI/P2A/9876543210/RAVI"),
    ("Rs 450 credited UPI/412345678901/<NAME>", "pay to UPI/9876543210@ybl"),
    ("IMPS/612345678901/credited", "IMPS/P2A/9876543210/credited"),
    ("UPI Ref No 412345678901 for Rs 450", "UPI Ref No 9876543210 for Rs 450"),
    # NEFT / RTGS alphanumeric UTR  vs  a phone after NEFT
    ("NEFT credit of Rs 25,000 ref NEFT-HDFCN52026102512345678", "NEFT to 9876543210 done"),
    ("RTGS UTR SBINR52026102500012345 credited", "RTGS from 9876543210"),
    # masked loan account  vs  an unmasked loan account number (personal financial identifier)
    ("EMI for Loan A/c XX2345 due on 05-11-26", "EMI for Loan No 123456789012345 due"),
    # toll-free support number  vs  a mobile number
    ("Never share your PIN. Call 1800-1234-5678 for help", "Never share your PIN. Call 9876543210 for help"),
    ("Customer care 1860 500 1243", "Customer care 98765 43210"),
])
def test_exemption_is_precise(legit, sensitive):
    assert pii_kinds(legit) == [], (legit, pii_kinds(legit))
    assert pii_kinds(sensitive) != [], sensitive


def test_aadhaar_in_upi_slot_is_still_flagged_when_aadhaar_is_mentioned():
    assert pii_kinds("Aadhaar linked: UPI/P2A/234567890123/RAVI") != []


# --- R3: generic words no longer hide numbers -----------------------------------------------------------

@pytest.mark.parametrize("text", [
    "For complaint 9876543210",
    "request 9876543210",
    "case 9876543210",
    "ticket 9876543210",
    "Ref: 234567890123 (aadhaar)",
    "Aadhaar 234567890123 ref",
    "Ref 234567890123 is your Aadhaar",
])
def test_reported_bypasses_are_flagged(text):
    assert pii_kinds(text) != [], text


@pytest.mark.parametrize("text", [
    "Order ID 6123456789 shipped",
    "AWB 123456789012 out for delivery",
    "Tracking number 512345678901",
    "UTR: 412345678901 credited",
    "Txn ID 7123456789 successful",
    "Complaint no. CMP12345 registered",          # alphanumeric ticket ids stay fine
])
def test_legitimate_reference_numbers_still_pass(text):
    assert pii_kinds(text) == [], (text, pii_kinds(text))


# --- R4: donations are never releasable until their consent version is approved -------------------------

def test_consent_licence_is_not_releasable_while_pending_review():
    assert "consent-v1" not in schema.APPROVED_CONSENT_VERSIONS
    it = item(provenance={**NOT_REAL, "licence_verified": True})
    assert not it.provenance.releasable


def test_intake_refuses_licence_verified_yes_for_unapproved_consent():
    row = {"id": "dn-0001", "text": "Your KYC is pending", "channel": "sms", "language": "english",
           "script": "latin", "source_type": "donated", "source_name": "unit-test-only-not-real",
           "licence": "consent-v1", "licence_verified": "yes", "consent_id": "c-0000",
           "collected_at": "2026-10-25", "redaction_version": "r1", "redaction_checked_by": "R2"}
    _, _, err = intake_from_rows([row])
    assert any("pending legal review" in e for e in err), err
    items, _, err = intake_from_rows([{**row, "licence_verified": "no"}])
    assert err == [] and not items[0].provenance.releasable


def test_pending_donation_cannot_enter_test_split():
    gold = {"label": "scam", "category": "other_scam", "basis": "annotator_judgment"}
    it = item(provenance={**NOT_REAL, "licence_verified": True}, gold=gold)
    grouped = group_items([it])[0]
    m = split_items(grouped, ratios={"train": 0.0, "dev": 0.0, "test": 1.0})
    assert [r["split"] for r in m["items"]] == ["train"]  # would be "test" if it counted as releasable


def test_approved_consent_version_becomes_releasable(monkeypatch):
    monkeypatch.setattr(schema, "APPROVED_CONSENT_VERSIONS", {"consent-v1"})
    assert item(provenance={**NOT_REAL, "licence_verified": True}).provenance.releasable


# --- R5: advisories need a real licence or a recorded permission; unclear rights are not stored -----------

ADVISORY = {"source_type": "official_advisory", "source_name": "unit-test-only-not-real",
            "source_url": "https://example.invalid/advisory", "collected_at": "2026-10-25"}


def test_advisory_with_unclear_rights_cannot_be_stored():
    with pytest.raises(ValidationError, match="reference-only"):
        item(id="oa-0001", provenance={**ADVISORY, "licence": "unknown"})


@pytest.mark.parametrize("licence", ["CC-BY-4.0", "permission-0001"])
def test_advisory_with_licence_or_recorded_permission_is_accepted(licence):
    item(id="oa-0001", provenance={**ADVISORY, "licence": licence})


@pytest.mark.parametrize("bad", ["permission", "permission-x", "permission-9876543210"])
def test_permission_reference_has_fixed_format(bad):
    with pytest.raises(ValidationError):
        item(id="oa-0001", provenance={**ADVISORY, "licence": bad})


def test_permission_licence_is_not_valid_for_donations():
    with pytest.raises(ValidationError):
        item(provenance={**NOT_REAL, "licence": "permission-0001"})
