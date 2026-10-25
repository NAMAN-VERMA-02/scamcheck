"""Static URL-structure analysis. Never resolves, fetches, follows redirects or executes anything.

Domain age, certificate transparency and reputation are NOT checked; every report says so instead of guessing.
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

from .models import Signal, UrlReport
from .parse import MAX_URL_CHARS

URL_ANALYSER_VERSION = "urls-2026.10.1"
NOT_CHECKED = ["domain age", "reputation lists", "certificate history", "where the link actually leads"]

# shortcut: a few common multi-label public suffixes instead of the full Public Suffix List; switch to a vendored
# PSL snapshot when real data shows misattributed domains.
_MULTI_SUFFIXES = {"co.in", "gov.in", "org.in", "net.in", "ac.in", "edu.in", "nic.in", "res.in", "firm.in", "gen.in",
                   "ind.in", "co.uk", "org.uk", "gov.uk", "ac.uk", "com.au", "co.jp", "com.br"}
# Free hosting: the registered domain is the customer's subdomain, and the platform itself is no evidence.
_FREE_HOSTING = {"web.app", "firebaseapp.com", "github.io", "netlify.app", "vercel.app", "pages.dev",
                 "blogspot.com", "wixsite.com", "weebly.com", "000webhostapp.com", "herokuapp.com", "glitch.me",
                 "ngrok-free.app", "ngrok.io", "duckdns.org", "wordpress.com"}
SHORTENERS = {"bit.ly", "tinyurl.com", "cutt.ly", "is.gd", "rb.gy", "shorturl.at", "t.co", "goo.gl", "ow.ly",
              "tiny.cc", "s.id", "v.gd", "bitly.ws", "short.gy", "rebrand.ly"}
CHAT_HANDOFF = {"t.me", "telegram.me", "wa.me", "chat.whatsapp.com"}
# shortcut: TLDs over-represented in phishing feeds in our research notes; a weak structural hint, not reputation.
SUSPICIOUS_TLDS = {"xyz", "top", "icu", "buzz", "tk", "ml", "ga", "cf", "gq", "click", "cyou", "sbs", "rest", "vip",
                   "monster", "quest", "cfd", "bond"}
# Brand token → registered domains the brand is known to use. Used ONLY to avoid a lookalike signal on the brand's
# own domain; never to vouch for a link. Hand-maintained and unverified by any lookup.
BRANDS: dict[str, set[str]] = {
    "sbi": {"sbi.co.in", "onlinesbi.sbi", "sbi.bank.in"}, "hdfc": {"hdfcbank.com", "hdfc.com"},
    "icici": {"icicibank.com", "icici.bank.in"}, "axis": {"axisbank.com"}, "kotak": {"kotak.com"},
    "paytm": {"paytm.com", "paytm.in", "paytmmall.com"}, "phonepe": {"phonepe.com"}, "amazon": {"amazon.in", "amazon.com"},
    "flipkart": {"flipkart.com"}, "indiapost": {"indiapost.gov.in"}, "irctc": {"irctc.co.in"},
    "uidai": {"uidai.gov.in"}, "aadhaar": {"uidai.gov.in"}, "incometax": {"incometax.gov.in"},
    "epfo": {"epfindia.gov.in"}, "parivahan": {"parivahan.gov.in"}, "echallan": {"parivahan.gov.in"},
    "airtel": {"airtel.in", "airtel.com"}, "jio": {"jio.com"}, "npci": {"npci.org.in"},
    "bluedart": {"bluedart.com"}, "delhivery": {"delhivery.com"}, "netflix": {"netflix.com"},
    "whatsapp": {"whatsapp.com"}, "google": {"google.com"}, "microsoft": {"microsoft.com"}, "apple": {"apple.com"},
}
_LEET = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})


def registered_domain(host: str) -> str:
    labels = host.lower().rstrip(".").split(".")
    if len(labels) <= 2:
        return ".".join(labels)
    take = 3 if ".".join(labels[-2:]) in _MULTI_SUFFIXES or ".".join(labels[-2:]) in _FREE_HOSTING else 2
    return ".".join(labels[-take:])


def is_official(host: str | None) -> bool:
    if not host:
        return False
    rd = registered_domain(host)
    return any(rd in domains for domains in BRANDS.values())


def defang(url: str) -> str:
    return re.sub(r"^http", "hxxp", url, flags=re.I).replace(".", "[.]")


def _edit1(a: str, b: str) -> bool:
    """True when a and b differ by exactly one substitution, insertion, deletion or adjacent swap."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
        return len(diff) == 1 or (len(diff) == 2 and diff[1] == diff[0] + 1
                                  and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]])
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


def _brand_hits(rd: str, host: str) -> list[str]:
    """Brands a domain imitates: brand token in the name, or (6+ letter brands only, so "apply" is not "apple")
    the brand inside a longer name or one edit away from a name token."""
    if any(rd in domains for domains in BRANDS.values()):
        return []
    hits = []
    name = rd.split(".")[0]
    tokens = set(re.split(r"[^a-z]+", name.translate(_LEET))) | set(re.split(r"[.\-]", host))
    squashed = name.translate(_LEET).replace("-", "")
    for brand in BRANDS:
        if brand in tokens or (len(brand) >= 6 and (brand in squashed or any(_edit1(brand, t) for t in tokens))):
            hits.append(brand)
    return hits


def analyse_url(raw: str) -> tuple[UrlReport, list[Signal]]:
    url = raw if "://" in raw else "http://" + raw
    sig: list[Signal] = []

    def add(id_: str, severity: str, evidence_type: str | None = None):
        sig.append(Signal(id=id_, severity=severity, source="url", evidence_type=evidence_type, quote=defang(raw)))

    if len(url) > MAX_URL_CHARS:
        add("U-UNPARSEABLE", "MEDIUM")
        return UrlReport(display=defang(raw[:80]) + "…", host=None, registered_domain=None,
                         signal_ids=[s.id for s in sig], not_checked=NOT_CHECKED), sig
    try:
        parts = urlsplit(url)
        host = parts.hostname
        _ = parts.port  # raises on a malformed port
    except ValueError:
        host = None
    if not host:
        add("U-UNPARSEABLE", "MEDIUM")
        return UrlReport(display=defang(raw), host=None, registered_domain=None, signal_ids=[s.id for s in sig],
                         not_checked=NOT_CHECKED), sig

    rd: str | None = None
    try:
        ipaddress.ip_address(host.strip("[]"))
        add("U-IP-HOST", "MEDIUM", "lookalike_domain")
    except ValueError:
        rd = registered_domain(host)
        if host.startswith("xn--") or ".xn--" in host or not host.isascii():
            add("U-PUNYCODE", "HIGH", "lookalike_domain")
        if _brand_hits(rd, host):
            add("U-BRAND-LOOKALIKE", "HIGH", "lookalike_domain")
        tld = rd.rsplit(".", 1)[-1]
        if tld in SUSPICIOUS_TLDS:
            add("U-SUSPICIOUS-TLD", "MEDIUM")
        if rd in SHORTENERS:
            add("U-SHORTENER", "MEDIUM", "shortened_url")
        if ".".join(rd.split(".")[1:]) in _FREE_HOSTING:
            add("U-FREE-HOSTING", "MEDIUM")
        if rd in CHAT_HANDOFF or host in CHAT_HANDOFF:
            add("U-CHAT-HANDOFF", "LOW")
        if host.count(".") - rd.count(".") >= 3:
            add("U-DEEP-SUBDOMAIN", "LOW")
    if parts.username or "@" in parts.netloc:
        add("U-USERINFO-TRICK", "HIGH", "lookalike_domain")
    if parts.path.lower().endswith(".apk"):
        add("U-APK-DOWNLOAD", "HIGH", "remote_access_app")
    if parts.scheme == "http" and "://" in raw:
        add("U-NO-TLS", "LOW")
    if parts.port and parts.port not in (80, 443):
        add("U-ODD-PORT", "LOW")
    return UrlReport(display=defang(raw), host=host, registered_domain=rd, signal_ids=[s.id for s in sig],
                     not_checked=NOT_CHECKED), sig
