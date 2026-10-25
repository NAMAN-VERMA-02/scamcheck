"""Redaction assistance applied before any text leaves the machine.

NOT anonymisation. It replaces identifiers with a recognisable shape; it cannot find names, addresses or
identifiers written in unexpected forms. The residual check reuses the dataset pipeline's detector
(`data/pii.py`), and the engine refuses to call a model when that detector still sees something.
"""

from __future__ import annotations

import re

from ..data.pii import _TEXT_PATTERNS, normalise_digits, pii_kinds

_STEPS: list[tuple[re.Pattern, str]] = [
    # URL query strings and fragments often carry tokens or phone numbers; the domain and path stay as evidence.
    (re.compile(r"((?:https?://|www\.)[^\s?#]+)[?#]\S*", re.I), r"\1?<QUERY>"),
    (_TEXT_PATTERNS["email address"], "<EMAIL>"),
    (_TEXT_PATTERNS["UPI id"], "<UPI>"),
    (re.compile(r"(?i)\b[a-z]{5}\d{4}[a-z]\b"), "<ID>"),
    (re.compile(r"(?<![\d<])(?:\+?91[\s-]?|0)?[6-9]\d{2}[\s-]?\d{3}[\s-]?\d{4}(?!\d)"), "<PHONE>"),
    (re.compile(r"(?<![\d<])\d(?:[\s-]?\d){8,18}(?!\d)"), "<NUMBER>"),
    (re.compile(r"(?i)(\b(?:otp|code|m?pin|passcode|password|cvv)\b\D{0,20}?)(?<![\d<])\d{3,8}(?!\d)"), r"\1<OTP>"),
    (re.compile(r"(?i)(?<![\d<])\d{3,8}(?!\d)(?=\s+(?:is|hai)\s+(?:your|the|aapka)\s+(?:otp|code|verification))"),
     "<OTP>"),
]


def redact(text: str) -> tuple[str, list[str]]:
    """(redacted text, kinds the residual detector still sees). An empty list is not a privacy guarantee."""
    t = normalise_digits(text)
    for pat, repl in _STEPS:
        t = pat.sub(repl, t)
    return t, pii_kinds(t)
