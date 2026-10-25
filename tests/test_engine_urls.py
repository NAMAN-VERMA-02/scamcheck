"""Static URL analysis. A guard makes any network use during these tests fail loudly."""

import socket

import pytest

from scamcheck.engine import analyse
from scamcheck.engine.parse import extract_urls, refang
from scamcheck.engine.urls import analyse_url, is_official, registered_domain


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)


def ids(raw):
    return analyse_url(raw)[0].signal_ids


@pytest.mark.parametrize("text,expected", [
    ("go to hxxps://sbi-kyc[.]in/x now", "https://sbi-kyc.in/x"),
    ("visit example(.)com/login", "example.com/login"),
    ("visit example[dot]top", "example.top"),
    ("see https://a.b.example.co.in/path?x=1.", "https://a.b.example.co.in/path?x=1"),
    ("ip http://192.168.10.5/pay here", "http://192.168.10.5/pay"),
])
def test_defanged_and_plain_urls_are_extracted(text, expected):
    assert expected in extract_urls(text)


def test_amounts_and_names_are_not_urls():
    assert extract_urls("Rs.500 paid to Mr.Sharma at 10.30 am") == []


def test_registered_domain_handles_indian_multi_label_suffixes():
    assert registered_domain("echallan.parivahan.gov.in") == "parivahan.gov.in"
    assert registered_domain("www.sbi.co.in") == "sbi.co.in"
    assert registered_domain("evil.web.app") == "evil.web.app"


@pytest.mark.parametrize("raw,signal", [
    ("https://sbi-kyc-update.in/verify", "U-BRAND-LOOKALIKE"),
    ("https://sbi.co.in.verify-kyc.top/login", "U-BRAND-LOOKALIKE"),
    ("https://amaz0n-offers.com", "U-BRAND-LOOKALIKE"),
    ("https://flipkrat.com/sale", "U-BRAND-LOOKALIKE"),
    ("https://xn--sbi-xyz.com", "U-PUNYCODE"),
    ("https://www.sbi.co.in@evil.example/login", "U-USERINFO-TRICK"),
    ("http://203.0.113.9/kyc", "U-IP-HOST"),
    ("https://bit.ly/abc", "U-SHORTENER"),
    ("https://my-bank.web.app", "U-FREE-HOSTING"),
    ("https://refund.example.com/app.apk", "U-APK-DOWNLOAD"),
    ("https://claim.example.xyz", "U-SUSPICIOUS-TLD"),
    ("https://t.me/somechannel", "U-CHAT-HANDOFF"),
])
def test_structural_signals(raw, signal):
    assert signal in ids(raw)


@pytest.mark.parametrize("raw", ["https://www.sbi.co.in/web/personal-banking", "https://www.amazon.in/orders",
                                 "https://apply-careers.com", "https://www.example-courier.com/track"])
def test_official_or_unrelated_domains_raise_no_lookalike(raw):
    assert "U-BRAND-LOOKALIKE" not in ids(raw)


def test_official_list_never_vouches_for_a_link():
    assert is_official("www.sbi.co.in")
    res = analyse("Check hxxps://www.sbi.co[.]in/x for details")
    assert res.verdict == "UNCLEAR" and "url_destination_not_verified" in res.reasons


def test_reports_say_what_was_not_checked_and_are_defanged():
    report, _ = analyse_url("https://example.com/x")
    assert "domain age" in report.not_checked and "reputation lists" in report.not_checked
    assert "://" not in report.display.replace("hxxps://", "") and "[.]" in report.display


@pytest.mark.parametrize("raw", ["http://[::1", "http://exa mple.com", "https://example.com:99999/x", "x" * 3000])
def test_malformed_urls_do_not_crash(raw):
    analyse_url(raw)


def test_refang_is_pure_text():
    assert refang("hxxps://a[.]b(.)c{.}d[dot]e") == "https://a.b.c.d.e"
