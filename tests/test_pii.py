"""Missed-redaction detector: regression tests for review findings H1, M1 and M2.

All values below are invented test inputs. Items use source_name "unit-test-only-not-real" and live in memory only.
"""

import pytest
from pydantic import ValidationError

from scamcheck.data.pii import pii_kinds, scan_item
from scamcheck.data.schema import Item

NOT_REAL = {"source_type": "donated", "source_name": "unit-test-only-not-real", "licence": "consent-v1",
            "licence_verified": True, "consent_id": "c-0000", "collected_at": "2026-10-25"}


def item(**over):
    base = {"id": "dn-0001", "text": "Your KYC is pending", "channel": "sms", "language": "english",
            "script": "latin", "provenance": NOT_REAL, "redaction": {"version": "r1", "checked_by": "R2"}}
    return Item.model_validate({**base, **over})


# --- M1: identifiers that must be flagged (every bypass demonstrated in the review) -------------

@pytest.mark.parametrize("text, kind", [
    ("Call 9876543210", "phone number"),
    ("Call +91 98765 43210", "phone number"),
    ("+91-98765-43210", "phone number"),
    ("0091 9876543210", "phone number"),
    ("(+91) 9876543210", "phone number"),
    ("call 09876543210", "phone number"),               # review bypass: leading 0
    ("call 987 654 3210", "phone number"),              # review bypass: 3-3-4 grouping
    ("call 98765.43210", "phone number"),               # review bypass: dots
    ("9 8 7 6 5 4 3 2 1 0", "phone number"),            # review bypass: spaced digits
    ("कॉल करें ९८७६५४३२१०", "phone number"),              # review bypass: Devanagari digits
    ("call ９８７６５４３２１０", "phone number"),            # review bypass: full-width digits
    ("call 011-23456789", "phone number"),              # review bypass: landline
    ("pay 9876543210@ybl", "UPI id"),
    ("hxxps://wa[.]me/919876543210", "phone number"),
    ("mail a.b@gmail.com", "email address"),
    ("MAIL A.B@GMAIL.COM", "email address"),
    ("x@rediffmail.co.in", "email address"),
    ("name [at] gmail [dot] com", "email address"),     # review bypass: obfuscated email
    ("pay ravi.k@okhdfcbank", "UPI id"),
    ("Aadhaar 1234 5678 9012 linked", "12-digit ID"),
    ("ID 234567890123", "12-digit ID"),
    ("PAN ABCDE1234F", "PAN"),                          # review bypass
    ("A/c 50100123456789", "bank account number"),      # review bypass: 14-digit account
    ("card 4111 1111 1111 1111 blocked", "card number"),
    ("card 3782 822463 10005", "card number"),          # review bypass: 15-digit Amex
    ("IFSC HDFC0001234", "IFSC"),                       # review bypass
    ("passport J8369854", "passport number"),           # review bypass
    ("challan for MH12AB1234", "vehicle registration"), # review bypass
    ("Your OTP is 482913", "OTP or PIN value"),
    ("482913 is your OTP", "OTP or PIN value"),
    ("Your verification code is 482913", "OTP or PIN value"),  # review bypass
    ("आपका ओटीपी 482913 है", "OTP or PIN value"),          # review bypass: Hindi
    ("Your UPI PIN is 1234", "OTP or PIN value"),       # review bypass
    ("OTP for login to your XYZ Bank account ending XX12 is 482913", "OTP or PIN value"),  # review bypass: far
])
def test_identifiers_are_flagged(text, kind):
    assert any(kind in k for k in pii_kinds(text)), pii_kinds(text)


# --- M2: ordinary transactional numbers must not be flagged ------------------------------------

@pytest.mark.parametrize("text", [
    "Rs 2,500 debited from A/c XX1234 on 12-10-26 to VPA <UPI>.",
    "<OTP> is your OTP. Do not share it.",
    "Call <PHONE> or 1800 1234 567",
    "Order #48213 shipped",
    "Order ID 6123456789 shipped",                      # review false positive
    "AWB 123456789012 out for delivery",                # review false positive
    "UPI Ref 612345678901 for Rs 450",                  # review false positive
    "UPI Ref No. 612345678901",
    "UTR: 412345678901 credited",
    "Txn ID 7123456789 successful",
    "Tracking number 512345678901",
    "Rs 6,00,000 loan approved",
    "SMS STOP to 56161",
    "since 2026 over 9000 users",
    "Recharge successful: Rs 299 plan active till 24-11-26.",
    "Valid till 24-11-26 10:45",
])
def test_transactional_numbers_are_not_flagged(text):
    assert pii_kinds(text) == []


def test_reference_keyword_does_not_hide_a_phone_number_later_in_the_message():
    assert "phone number" in pii_kinds("Ref 612345678901. Call 9876543210 now")


def test_names_and_addresses_are_not_claimed_to_be_detected():
    # Documented limitation: these depend on the human redaction check.
    assert pii_kinds("Hi Rahul Sharma, Flat 12, MG Road") == []


# --- H1: every user-supplied field is scanned, not just text --------------------------------------

def test_url_query_and_encoded_values_are_scanned():
    it = item(urls=[{"raw": "hxxps://kyc[.]in/?ph=9876543210&mail=a.b%40gmail.com", "registered_domain": "kyc.in"}])
    warnings = " ".join(scan_item(it))
    assert "urls.0.raw" in warnings and "phone number" in warnings and "email address" in warnings


def test_annotation_notes_rationale_and_provenance_are_scanned():
    it = item(annotations=[{"annotator": "A1", "label": "scam", "category": "other_scam", "confidence": 2,
                            "guideline_version": "g1", "note": "donor said call 9876543210"}],
              provenance={**NOT_REAL, "source_name": "from ravi@example.com"})
    warnings = " ".join(scan_item(it))
    assert "annotations.0.note" in warnings and "provenance.source_name" in warnings


def test_clean_item_has_no_warnings():
    assert scan_item(item(sender={"type": "phone", "value": "<PHONE>"})) == []


@pytest.mark.parametrize("sender", [
    {"type": "phone", "value": "+919876543210"},        # review demonstrated bypass
    {"type": "phone", "value": "98765 43210"},
    {"type": "email", "value": "ravi@example.com"},
    {"type": "unknown", "value": "9876543210"},
    {"type": "dlt_header", "value": "9876543210"},
])
def test_real_sender_identifiers_are_rejected(sender):
    with pytest.raises(ValidationError, match="sender"):
        item(sender=sender)


@pytest.mark.parametrize("sender", [
    {"type": "phone", "value": "<PHONE>"},
    {"type": "phone", "value": "PHONE_5f2c9a1b77aa"},
    {"type": "phone", "value": "56161"},                # short code
    {"type": "email", "value": "<EMAIL>"},
    {"type": "dlt_header", "value": "VM-HDFCBK"},
    {"type": "dlt_header", "value": "JD-SBIINB-S"},
    {"type": "unknown"},
])
def test_redacted_or_public_sender_identifiers_are_accepted(sender):
    item(sender=sender)
