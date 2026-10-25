"""Input parsing: Unicode normalisation, hidden-character and confusable detection, defanged-URL recovery.

Pure string work. Nothing here touches the network.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

MAX_TEXT_CHARS = 4000
MAX_URL_CHARS = 2000

# Format/control characters that render as nothing. ZWJ/ZWNJ are legitimate inside Devanagari and emoji sequences,
# so they are only counted when both neighbours are ASCII.
_INVISIBLE = re.compile("[­͏؜ᅟᅠ឴឵᠎​‎‏‪-‮"
                        "⁠-⁤⁦-⁯﻿]")
_JOINERS = re.compile("[‌‍]")

# shortcut: a selected Cyrillic/Greek → Latin subset, not the full Unicode confusables table; extend when the
# mutation lab or real data shows a missed letter.
CONFUSABLES = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s",
    "ԁ": "d", "ɡ": "g", "һ": "h", "к": "k", "м": "m", "т": "t", "в": "b", "н": "h", "ո": "n",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X",
    "ο": "o", "α": "a", "ν": "v", "ι": "i", "κ": "k", "ρ": "p", "τ": "t", "υ": "u", "Ο": "O", "Α": "A", "Β": "B",
    "Ε": "E", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N", "Ρ": "P", "Τ": "T", "Χ": "X", "Ζ": "Z",
}
CONFUSABLES.update({k.upper(): v.upper() for k, v in list(CONFUSABLES.items()) if k.upper() not in CONFUSABLES})
_CONFUSABLE_CHARS = "".join(CONFUSABLES)
_CONFUSABLE_WORD = re.compile(rf"\w*[{_CONFUSABLE_CHARS}]\w*")

# Defanging forms people use: hxxp, [.], (.), {.}, [dot], (dot), [:]
_DEFANG = [
    (re.compile(r"\bhxxp", re.I), "http"),
    (re.compile(r"\s?[\[({]\s*(?:\.|dot)\s*[\])}]\s?", re.I), "."),
    (re.compile(r"\[:\]"), ":"),
]
# Bare domains are only recognised with a known TLD, so "Mr.Sharma" or "Rs.500" never look like links.
_TLDS = ("com|in|net|org|co|info|biz|xyz|top|link|app|site|online|shop|store|club|live|icu|vip|buzz|cc|me|io|ly|"
         "gl|gd|to|ws|tk|ml|ga|cf|gq|ru|cn|pro|website|click|fun|space|tech|sbi|bank|tv|us|uk|cyou|sbs|rest|"
         "today|support|help|services|digital|cloud|dev|page|pages|ai")
URL_RE = re.compile(
    r"(?:\bhttps?://[^\s<>\"']+)"
    r"|(?:\b(?:www\.)?(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:" + _TLDS + r")\b(?::\d{2,5})?(?:/[^\s<>\"']*)?)"
    r"|(?:\b\d{1,3}(?:\.\d{1,3}){3}(?::\d{2,5})?/[^\s<>\"']*)",
    re.I,
)
_TRAILING = ".,;:!?)]}'\""


@dataclass(frozen=True)
class ParsedInput:
    text: str                 # NFKC, invisible characters removed, confusables mapped to Latin
    hidden_chars: int         # invisible characters found between ASCII letters/digits or anywhere unexpected
    confusable_words: tuple[str, ...]  # words using Cyrillic/Greek lookalike letters inside Latin-script text
    script: str               # latin | devanagari | mixed | other
    urls: tuple[str, ...] = field(default=())  # refanged URL strings, in order of appearance, deduplicated


def _strip_invisible(text: str) -> tuple[str, int]:
    count = len(_INVISIBLE.findall(text))
    text = _INVISIBLE.sub("", text)
    out = []
    for i, ch in enumerate(text):
        if _JOINERS.match(ch):
            prev = text[i - 1] if i else " "
            nxt = text[i + 1] if i + 1 < len(text) else " "
            if prev.isascii() and nxt.isascii():
                count += 1
                continue
        out.append(ch)
    return "".join(out), count


def _script(text: str) -> str:
    deva = sum("ऀ" <= c <= "ॿ" for c in text)
    latin = sum(c.isascii() and c.isalpha() for c in text)
    if deva and latin:
        return "mixed"
    if deva:
        return "devanagari"
    return "latin" if latin else "other"


def refang(text: str) -> str:
    for pat, repl in _DEFANG:
        text = pat.sub(repl, text)
    return text


def extract_urls(text: str) -> list[str]:
    seen: list[str] = []
    for m in URL_RE.finditer(refang(text)):
        u = m.group().rstrip(_TRAILING)
        if u and u not in seen:
            seen.append(u)
    return seen


def parse(text: str) -> ParsedInput:
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"text longer than {MAX_TEXT_CHARS} characters")
    t = unicodedata.normalize("NFKC", text)
    t, hidden = _strip_invisible(t)
    # English/Hinglish input is in scope, so lookalike letters in otherwise Latin text are treated as disguise.
    mixed = tuple(_CONFUSABLE_WORD.findall(t)) if re.search("[A-Za-z]", t) else ()
    t = "".join(CONFUSABLES.get(c, c) for c in t)
    # Line breaks in SMS/WhatsApp are formatting, not sentence ends; rules match within sentences.
    t = re.sub(r"\s+", " ", t).strip()
    return ParsedInput(text=t, hidden_chars=hidden, confusable_words=mixed, script=_script(t),
                       urls=tuple(extract_urls(t)))
