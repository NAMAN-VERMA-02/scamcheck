"""Text normalisation used for duplicate detection (not for the user-facing engine)."""

from __future__ import annotations

import hashlib
import re
import unicodedata

_INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤﻿]")
_URL = re.compile(r"\b(?:hxxps?|https?)://\S+|\b[\w-]+(?:\[\.\]|\.)(?:com|in|net|org|co|info|xyz|top|link|app|site)\b\S*", re.I)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
_UPI = re.compile(r"\b[\w.-]+@[a-z]{2,}\b", re.I)
_PLACEHOLDER = re.compile(r"<[a-z_]+>", re.I)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_SPACE = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Collapse surface variation so template copies of one campaign look identical."""
    t = unicodedata.normalize("NFKC", text)
    t = _INVISIBLE.sub("", t).lower()
    t = _URL.sub(" <url> ", t)
    t = _EMAIL.sub(" <email> ", t)
    t = _UPI.sub(" <upi> ", t)
    t = _PLACEHOLDER.sub(lambda m: f" {m.group(0).lower()} ", t)
    t = _NUMBER.sub(" <num> ", t)
    return _SPACE.sub(" ", t).strip()


def content_hash(text: str) -> str:
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()


def shingles(text: str, k: int = 5) -> set[str]:
    t = normalise(text)
    return {t[i : i + k] for i in range(max(1, len(t) - k + 1))}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)
