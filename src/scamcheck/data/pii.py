"""Missed-redaction detector.

A safety net under the mandatory human redaction check, NOT an anonymiser. It looks for identifiers with a
recognisable shape (phones, emails, UPI ids, Aadhaar-like and card numbers, PAN, IFSC, passport, vehicle numbers,
OTP/PIN values). It cannot find names, addresses, or identifiers written in unexpected forms.
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import unquote

from .schema import Item

# Narrow, documented exemptions for transaction references (each is tested with a sensitive counter-example):
_KEY_TAIL = r"(?:\s*(?:id|no|num|number))?\.?\s*[:#.\-]?\s*$"
# Order/shipment/booking/transaction ids: any digit run directly after the keyword.
_STRONG_REF_BEFORE = re.compile(
    r"(?i)\b(?:order|awb|tracking|consignment|shipment|invoice|booking|pnr|txn|transaction)\b" + _KEY_TAIL)
# Generic "ref"/UTR/RRN: exempt unless the number has the shape of an Indian mobile number.
_WEAK_REF_BEFORE = re.compile(r"(?i)\b(?:ref(?:erence)?|utr|rrn)\b" + _KEY_TAIL)
# UPI/IMPS slots (UPI/P2M/…, IMPS/…, UPI Ref No …): exempt only for exactly 12 digits (the RRN length).
_UPI_SLOT_BEFORE = re.compile(
    r"(?i)\b(?:upi|imps)\s*(?:[/:]\s*(?:p2[pma]\s*/\s*)?|ref(?:erence)?" + _KEY_TAIL[:-1] + r")\s*$")
# NEFT/RTGS UTR: bank code + 1 char + digits, written as one token, after NEFT/RTGS/UTR.
_UTR_TOKEN = re.compile(r"[A-Za-z]{4}[A-Za-z0-9]\d{6,17}")
_UTR_CONTEXT = re.compile(r"(?i)\b(?:neft|rtgs|utr)\b")
# Indian toll-free / shared-cost business numbers.
_TOLL_FREE = re.compile(r"(?:1800|1860)\d{6,8}")
_ACCOUNT_BEFORE = re.compile(
    r"(?i)\b(?:a/?c|acct|account|khata|loan)\b(?:\s*(?:a/?c|acct|no|number))?\.?\s*[:#.\-]?\s*$")
_AADHAAR_NEAR = re.compile(r"(?i)aadh?aar|\buid\b|आधार")
_MOBILE = re.compile(r"(?:0091|91|0)?[6-9]\d{9}")
# Currency amounts, masked before looking for OTP values so "OTP … Rs 2,500" is not read as an OTP.
_AMOUNT = re.compile(r"(?i)(?:\brs\.?|\binr\b|₹)\s*\d[\d,]*(?:\.\d+)?")
# Separators people put inside phone/card numbers; joined so "987 654 3210" is seen as one number.
_DIGIT_GAP = re.compile(r"(?<=\d)(?:[ .\-/]|\)\s?|\s?\(){1,2}(?=[\d+])")
_RUN = re.compile(r"\+?\d+")

_TEXT_PATTERNS = {
    "email address": re.compile(r"(?i)\b[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[a-z]{2,}\b"),
    "email address (obfuscated)": re.compile(
        r"(?i)\b[\w.+-]+\s*[\[({]\s*at\s*[\])}]\s*[\w-]+(?:\s*[\[({]\s*dot\s*[\])}]\s*[\w-]+)+"),
    # A sentence-ending period ("pay name@okaxis.") still ends the handle; "name@okaxis.com" is an email.
    "UPI id": re.compile(r"(?i)(?<![\w.])[\w.-]{2,}@[a-z]{2,}(?![\w@-]|\.\w)"),
    "PAN": re.compile(r"(?i)\b[a-z]{5}\d{4}[a-z]\b"),  # any 4th letter: a safety net should over-flag
    "IFSC": re.compile(r"(?i)\b[a-z]{4}0[a-z0-9]{6}\b"),
    "passport number": re.compile(r"(?i)\b[a-pr-wy][1-9]\d\s?\d{4}[1-9]\b"),
    "vehicle registration": re.compile(r"(?i)\b[a-z]{2}[\s-]?\d{1,2}[\s-]?[a-z]{1,3}[\s-]?\d{4}\b"),
    "OTP or PIN value": re.compile(
        r"(?i)(?:\b(?:otp|one[\s-]?time\s+pass(?:word|code)|verification\s+code|security\s+code|"
        r"auth(?:entication)?\s+code|login\s+code|passcode|m?pin|cvv)\b|ओटीपी|पिन)"
        r"[^.!?\n]{0,60}?(?<![\d<])\d{3,8}(?!\d)"
        r"|(?<![\d<])\d{4,8}(?!\d)[^.!?\n]{0,30}?(?:\b(?:otp|verification\s+code|pin)\b|ओटीपी)"),
}


def normalise_digits(text: str) -> str:
    """NFKC (full-width → ASCII) and every Unicode decimal digit (Devanagari etc.) → 0-9."""
    t = unicodedata.normalize("NFKC", text)
    return "".join(str(unicodedata.decimal(c)) if not c.isascii() and unicodedata.decimal(c, None) is not None
                   else c for c in t)


def _luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch) * (2 if i % 2 else 1)
        total += d - 9 if d > 9 else d
    return total % 10 == 0


def _is_reference(joined: str, start: int, end: int, run: str, before: str) -> bool:
    """True only for the documented non-personal formats; an Aadhaar mention near a 12-digit number always wins."""
    if len(run) == 12 and _AADHAAR_NEAR.search(joined[max(0, start - 40):end + 40]):
        return False
    if _TOLL_FREE.fullmatch(run):
        return True
    if len(run) == 12 and _UPI_SLOT_BEFORE.search(before):
        return True
    token_start = start
    while token_start > 0 and joined[token_start - 1].isalnum():
        token_start -= 1
    if (token_start < start and _UTR_TOKEN.fullmatch(joined[token_start:end])
            and _UTR_CONTEXT.search(joined[max(0, token_start - 25):token_start])):
        return True
    if _STRONG_REF_BEFORE.search(before):
        return True
    return bool(_WEAK_REF_BEFORE.search(before)) and not _MOBILE.fullmatch(run)


def _number_kinds(text: str) -> set[str]:
    # Classify runs in the joined text ("987 654 3210" → one number) AND in the original text, so joining two
    # adjacent numbers ("9876543210 9123456780") can never hide either of them.
    return _classify_runs(_DIGIT_GAP.sub("", text), text) | _classify_runs(text, text)


def _classify_runs(s: str, text: str) -> set[str]:
    kinds = set()
    for m in _RUN.finditer(s):
        run = m.group().lstrip("+")
        before = s[max(0, m.start() - 30):m.start()]
        if _is_reference(s, m.start(), m.end(), run, before):
            continue
        if _ACCOUNT_BEFORE.search(before) and 9 <= len(run) <= 18:
            kinds.add("bank account number")
        elif _MOBILE.fullmatch(run) or re.fullmatch(r"0[1-9]\d{8,9}", run):
            kinds.add("phone number")
        elif 13 <= len(run) <= 19 and _luhn(run):
            kinds.add("card number")
        elif len(run) == 12:
            kinds.add("12-digit ID (Aadhaar-like)" if run[0] in "23456789" or _AADHAAR_NEAR.search(text)
                      else "12-digit number (Aadhaar-like or account)")
        elif len(run) >= 13:
            kinds.add("long number (possible account or card)")
    return kinds


def pii_kinds(text: str) -> list[str]:
    """Kinds of identifier that look unredacted in `text` (URL-decoded and digit-normalised first)."""
    kinds: set[str] = set()
    for variant in {text, unquote(text)}:
        t = normalise_digits(variant)
        kinds |= _number_kinds(t)
        for kind, pat in _TEXT_PATTERNS.items():
            target = _AMOUNT.sub(" <AMT> ", t) if kind == "OTP or PIN value" else t
            m = pat.search(target)
            if m and not (kind in ("passport number", "vehicle registration")
                          and (_STRONG_REF_BEFORE.search(target[max(0, m.start() - 30):m.start()])
                               or _WEAK_REF_BEFORE.search(target[max(0, m.start() - 30):m.start()]))):
                kinds.add(kind)
    return sorted(kinds)


# Fields whose values the pipeline generates or constrains to a fixed format; everything else is scanned.
# campaign_id is scanned too: its hex format can't by itself exclude an all-digit value such as g-9876543210.
_SKIP = {"id", "schema_version", "scammer_ids", "seed_id", "parent_id", "consent_id",
         "collected_at", "at", "taken_at", "rdap_created", "ct_first_seen"}


def _strings(value, path=""):
    if isinstance(value, dict):
        for k, v in value.items():
            if k not in _SKIP:
                yield from _strings(v, f"{path}.{k}" if path else k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _strings(v, f"{path}.{i}")
    elif isinstance(value, str):
        yield path, value


def scan_item(item: Item) -> list[str]:
    """Warnings for every user-supplied string field of an item, not just the message text."""
    out = []
    for path, value in _strings(item.model_dump(mode="json", exclude_none=True)):
        for kind in pii_kinds(value):
            out.append(f"{item.id} [{path}]: possible unredacted {kind}; replace it with a placeholder")
    return out


def pii_warnings(item_id: str, text: str) -> list[str]:
    """Text-only variant kept for callers that check a single string."""
    return [f"{item_id}: possible unredacted {kind}; replace it with a placeholder" for kind in pii_kinds(text)]
