"""Dataset item schema. Single source of truth; schema/item.schema.json is generated from it."""

from __future__ import annotations

import re
from datetime import date
from typing import Annotated, Literal, Optional
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0"

Label = Literal["scam", "legitimate", "promotional", "ambiguous"]
Language = Literal["english", "hinglish"]
Script = Literal["latin", "devanagari", "mixed"]
Channel = Literal["sms", "whatsapp", "telegram", "email", "other", "unknown"]
SourceType = Literal["donated", "public_dataset", "official_advisory", "synthetic"]
Basis = Literal["donor_confirmed", "official_advisory", "sender_verified", "annotator_judgment"]

SCAM_CATEGORIES = {
    "phishing_credential", "bank_kyc_impersonation", "govt_impersonation", "delivery_scam",
    "upi_collect_refund", "job_task_scam", "investment_trading", "loan_app", "lottery_prize",
    "other_scam",
}
LEGIT_CATEGORIES = {
    "bank_txn_alert", "otp", "payment_confirmation", "delivery_notification", "govt_notice",
    "service_account", "personal",
}
PROMO_CATEGORIES = {"marketing"}
CATEGORIES_BY_LABEL: dict[str, set[str]] = {
    "scam": SCAM_CATEGORIES,
    "legitimate": LEGIT_CATEGORIES,
    "promotional": PROMO_CATEGORIES,
    "ambiguous": set(),  # ambiguous items carry no category
}

EVIDENCE_TYPES = {
    # scam red flags
    "otp_or_pin_request", "credential_request", "account_block_threat", "urgency",
    "lookalike_domain", "shortened_url", "personal_payment_handle", "remote_access_app",
    "authority_threat", "fee_for_reward", "guaranteed_returns", "collect_request",
    "prompt_injection", "obfuscation",
    # legitimacy indicators
    "verified_sender_header", "official_domain", "standard_template", "do_not_share_warning",
    "no_call_to_action",
}

# Product verdicts each gold label may receive without counting as an error. Promotional is NOT folded into
# legitimate: a LIKELY_SCAM on marketing is a false alarm, but reported as its own slice.
ACCEPTABLE_VERDICTS = {
    "scam": {"LIKELY_SCAM", "UNCLEAR"},          # NO_STRONG_SIGNALS on a scam = dangerous miss
    "legitimate": {"NO_STRONG_SIGNALS", "UNCLEAR"},
    "promotional": {"NO_STRONG_SIGNALS", "UNCLEAR"},
    "ambiguous": {"UNCLEAR"},
}

# Fail closed: a licence must be one a human has deliberately added here. Extend only after reading the terms.
ACCEPTED_LICENCES = {"CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "ODC-By-1.0", "ODbL-1.0", "MIT", "Apache-2.0"}
_CONSENT_LICENCE = re.compile(r"^consent-v\d+$")

_UNDEFANGED_URL = re.compile(r"\bhttps?://", re.IGNORECASE)


def refang_host(raw: str) -> str | None:
    s = re.sub(r"^hxxp", "http", raw.strip(), flags=re.I).replace("[.]", ".")
    if "://" not in s:
        s = "http://" + s
    return urlsplit(s).hostname


class Span(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    type: str

    @model_validator(mode="after")
    def _check(self) -> "Span":
        if self.end <= self.start:
            raise ValueError("span end must be greater than start")
        if self.type not in EVIDENCE_TYPES:
            raise ValueError(f"unknown evidence type {self.type!r}")
        return self


class Sender(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["dlt_header", "phone", "email", "unknown"]
    value: Optional[str] = None


class UrlSnapshot(BaseModel):
    """Lookups taken once at collection time so every evaluation run sees identical signals."""
    model_config = ConfigDict(extra="forbid")
    taken_at: str
    rdap_created: Optional[date] = None
    ct_first_seen: Optional[date] = None
    reputation_hit: Optional[str] = None
    lookup_errors: list[str] = []


class Url(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raw: str  # stored defanged, e.g. hxxps://example[.]com/x
    registered_domain: str
    snapshot: Optional[UrlSnapshot] = None

    @model_validator(mode="after")
    def _check(self) -> "Url":
        if _UNDEFANGED_URL.search(self.raw):
            raise ValueError("url.raw must be defanged (hxxp://, [.])")
        rd = self.registered_domain
        if rd != rd.lower() or "[" in rd:
            raise ValueError("registered_domain must be lowercase and not defanged")
        host = refang_host(self.raw)
        if not host or not (host == rd or host.endswith("." + rd)):
            raise ValueError(f"registered_domain {rd!r} does not match the url host {host!r}")
        return self


class Annotation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    annotator: str
    label: Label
    category: Optional[str] = None
    confidence: int = Field(ge=1, le=3)  # 1 guessing, 2 fairly sure, 3 certain
    evidence: list[Span] = []
    guideline_version: str
    note: str = ""
    at: Optional[date] = None

    @model_validator(mode="after")
    def _check(self) -> "Annotation":
        _check_category(self.label, self.category)
        return self


class Gold(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: Label
    category: Optional[str] = None
    basis: Basis
    adjudicated: bool = False
    rationale: str = ""
    evidence: list[Span] = []

    @model_validator(mode="after")
    def _check(self) -> "Gold":
        _check_category(self.label, self.category)
        if self.adjudicated and not self.rationale.strip():
            raise ValueError("adjudicated gold labels need a rationale")
        return self


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_type: SourceType
    source_name: str
    source_url: Optional[str] = None
    licence: str  # one of ACCEPTED_LICENCES, consent-vN (donations only), or "unknown"
    licence_verified: bool = False  # a human checked the licence/consent text for this source
    consent_id: Optional[str] = None
    collected_at: date

    @model_validator(mode="after")
    def _check(self) -> "Provenance":
        consent = bool(_CONSENT_LICENCE.match(self.licence))
        if not (consent or self.licence == "unknown" or self.licence in ACCEPTED_LICENCES):
            raise ValueError(f"licence {self.licence!r} is not recognised; use an accepted SPDX id, consent-vN or "
                             "'unknown' (add new licences to ACCEPTED_LICENCES only after reading their terms)")
        if self.source_type == "donated" and not consent:
            raise ValueError("donated items must use a consent-vN licence")
        if consent and self.source_type != "donated":
            raise ValueError("consent-vN licences are only valid for donated items")
        return self

    @property
    def releasable(self) -> bool:
        return self.licence_verified and self.licence != "unknown"


class Synthetic(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: Literal["handwritten", "template", "paraphrase", "translate"]
    generator: str  # person or model that produced it
    seed_id: Optional[str] = None


class Adversarial(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["prompt_injection", "zero_width", "homoglyph", "transliteration", "llm_rewrite"]
    parent_id: str


class Redaction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    checked_by: str


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z]{2,4}-[0-9A-Za-z_-]+$")
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    text: str = Field(min_length=1)  # redacted text only
    channel: Channel
    sender: Optional[Sender] = None
    language: Language
    script: Script
    urls: list[Url] = []
    # Scammer phone/UPI/email/account, pseudonymised with a dataset-wide keyed hash so the same number links
    # campaigns across rewording without storing the real identifier.
    scammer_ids: list[Annotated[str, Field(pattern=r"^(PHONE|UPI|EMAIL|ACCT)_[0-9a-f]{8,}$")]] = []
    gold: Optional[Gold] = None  # None = still being annotated; such items are never split
    annotations: list[Annotation] = []
    provenance: Provenance
    synthetic: Optional[Synthetic] = None
    adversarial: Optional[Adversarial] = None
    campaign_id: Optional[str] = None  # assigned by `scamcheck group`, never by hand
    redaction: Redaction

    @model_validator(mode="after")
    def _check(self) -> "Item":
        p = self.provenance
        if p.source_type == "synthetic" and self.synthetic is None:
            raise ValueError("source_type 'synthetic' requires a synthetic block")
        if p.source_type != "synthetic" and self.synthetic is not None:
            raise ValueError("synthetic block is only allowed when source_type is 'synthetic'")
        if self.adversarial is not None and p.source_type != "synthetic":
            raise ValueError("adversarial variants are constructed, so source_type must be 'synthetic' "
                             "(a real message that contains an attack is a normal item with evidence spans)")
        if p.source_type == "donated" and not p.consent_id:
            raise ValueError("donated items require provenance.consent_id")
        if p.source_type in ("public_dataset", "official_advisory") and not p.source_url:
            raise ValueError(f"{p.source_type} items require provenance.source_url")
        if _UNDEFANGED_URL.search(self.text):
            raise ValueError("URLs in text must be defanged (hxxp://, [.])")
        spans = [s for a in self.annotations for s in a.evidence]
        if self.gold:
            spans += self.gold.evidence
        for s in spans:
            if s.end > len(self.text):
                raise ValueError(f"evidence span {s.start}-{s.end} is outside the text")
        labels = {a.label for a in self.annotations}
        if self.gold and len(labels) > 1 and not self.gold.adjudicated:
            raise ValueError("annotators disagree on label; gold must be adjudicated")
        return self

    @property
    def is_synthetic(self) -> bool:
        return self.provenance.source_type == "synthetic"


def _check_category(label: str, category: Optional[str]) -> None:
    allowed = CATEGORIES_BY_LABEL[label]
    if not allowed:
        if category is not None:
            raise ValueError(f"label {label!r} must not have a category")
    elif category not in allowed:
        raise ValueError(f"category {category!r} is not valid for label {label!r}")
