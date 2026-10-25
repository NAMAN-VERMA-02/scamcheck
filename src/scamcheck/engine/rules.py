"""Versioned deterministic rule pack (English + romanised Hinglish).

Design constraints, each covered by tests in tests/test_engine_rules.py:
  * ordinary OTP messages, amounts and transaction references never fire a rule by themselves;
  * a request is negation-aware ("do not share your OTP", "share na karein" do not fire);
  * every signal carries the exact quote that triggered it.
Bump RULE_PACK_VERSION whenever a pattern changes, so reports stay comparable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Signal

RULE_PACK_VERSION = "rules-2026.10.1"

_F = re.I
_S = r"[^.!?\n]"            # stay inside one sentence
_SEP = r"[\s.\-_*]?"        # tolerate O T P, O.T.P, K-Y-C


def _spaced(word: str) -> str:
    return _SEP.join(word)


SECRET = (rf"(?:{_spaced('otp')}|one[\s-]?time[\s-]?pass(?:word|code)?|verification\s+code|security\s+code|"
          rf"{_spaced('cvv')}|\bm?pin\b(?!\s*code)|p[\s.\-]i[\s.\-]n|password|passcode|"
          r"\b(?:\d|six|four|chhe|char)[\s-]?digit\s+code|ओटीपी|पिन)")
_NEG_BEFORE = re.compile(r"(?:\bnever\b|\bnot\b|\bdon'?t\b|\bdont\b|\bno\s+need\b|\bkabhi\b|\bmat\b|\bnahi\w*\b|"
                         r"\bmana\b|\bavoid\b|\brefuse\b|\bwithout\b)[^.!?\n]{0,20}$", _F)
_NEG_AFTER = re.compile(r"^\s*(?:na|mat|nahi\w*|nahin)\b", _F)
_ADVISORY = re.compile(r"\b(?:beware|be\s+aware|be\s+careful|saavdhan|savdhan|sawdhan|awareness|fraud\w*\s+se\s+"
                       r"bach\w*|report\w*\s+(?:it\s+)?(?:at|on|to)\s+1930|cybercrime[.\s]gov[.\s]in|"
                       r"never\s+(?:ask|call|arrest)\w*)", _F)


@dataclass(frozen=True)
class Rule:
    id: str
    severity: str
    evidence_type: str | None
    pattern: re.Pattern
    negatable: bool = False           # skip matches preceded/followed by a negation of the `verb` group
    requires: re.Pattern | None = None  # must also occur somewhere in the message
    exempt: re.Pattern | None = None    # a match is skipped when this occurs within 80 characters of it
    blocks_reassurance: bool = False
    demote_if_advisory: bool = False    # warnings that quote scam wording drop to MEDIUM, never vanish


def _r(p: str) -> re.Pattern:
    return re.compile(p, _F)


_SHARE_VERB = (r"share|send|tell|give|provide|forward|reply\s+with|read\s+out|batao|bataiye|bata|btao|bhejo|bhej|"
               r"bhejiye|de\s+do|dedo|dijiye|bolo|bol\s+do")
_REWARD = _r(r"\b(?:prize|lottery|lucky\s+draw|winner|won|jeet\w*|inaam|reward|gift|cashback|loan|job|naukri|"
             r"salary|selected|kbc|refund|bonus|earn\w*|kamai|kamao|income|part[\s-]?time|milega|milenge)\b")
_THREAT = (r"\b(?:account|a/c|acct|khata|card|sim|kyc|pan|aadhaar|electricity|bijli|connection|wallet|number|"
           r"service|net\s?banking|yono|meter)\b" + _S + r"{0,40}?\b(?:block\w*|suspend\w*|deactivat\w*|band|"
           r"disconnect\w*|cut|kaat\w*|frozen|freeze|closed?|terminat\w*|expire\w*|hold)\b")
_FUTURE = _r(r"\b(?:will\s+be|will\s+get|ho\s+ja(?:y|)eg[ai]|kar\s+di(?:ya|)\s+ja(?:y|)eg[ai]|hoga|hogi|today|tonight|"
             r"aaj|within|in\s+\d+\s*(?:hours?|hrs?|ghante|minutes?|mins?)|shortly|soon|turant|immediately)\b")
_CALL_TO_ACTION = _r(r"\b(?:call|contact|whatsapp|click|tap|visit|update\s+(?:now|here|at|via)|sampark|"
                     r"call\s+kar\w*|<PHONE>)\b|\b(?:\+?91[\s-]?)?[6-9]\d{9}\b")

RULES: tuple[Rule, ...] = (
    Rule("R-OTP-REQUEST", "HIGH", "otp_or_pin_request",
         # "we will send you an OTP" is the service talking, not a request: the verb may not be followed by "you".
         _r(rf"\b(?P<verb>{_SHARE_VERB})\b(?!\s+(?:you|u|aapko)\b){_S}{{0,40}}?{SECRET}|{SECRET}{_S}{{0,40}}?\b(?P<verb2>{_SHARE_VERB})\b"),
         negatable=True,
         # Delivery OTPs are legitimately shared with the courier at the door.
         exempt=_r(r"\bdelivery\s+(?:agent|executive|associate|partner|boy|person)\b")),
    Rule("R-PIN-TO-RECEIVE", "HIGH", "collect_request",
         _r(rf"\b(?P<verb>enter|daal\w*|dal(?:o|en|iye)|type|put)\b{_S}{{0,25}}?(?:upi\s+)?(?:\bm?pin\b|p\s?i\s?n)"
            rf"{_S}{{0,50}}?\b(?:receive|get|credit\w*|claim|refund|cashback|paane|pane|lene|milega|milenge|aayega)\b"
            rf"|\b(?:receive|claim|paane|pane|lene)\b{_S}{{0,50}}?(?:upi\s+)?\bm?pin\b{_S}{{0,20}}?"
            rf"\b(?P<verb2>daal\w*|dal(?:o|en|iye)|enter|type|dale)\b"),
         negatable=True),
    Rule("R-COLLECT-REQUEST", "HIGH", "collect_request",
         _r(rf"\b(?P<verb>accept|approve|pay)\b{_S}{{0,30}}?\b(?:collect\s+)?request\b{_S}{{0,50}}?"
            rf"\b(?:receive|refund|cashback|prize|credit\w*|paane|milega)\b"),
         negatable=True),
    Rule("R-CREDENTIAL-REQUEST", "HIGH", "credential_request",
         _r(rf"\b(?P<verb>{_SHARE_VERB}|enter|fill|update|confirm|verify)\b{_S}{{0,30}}?\b(?:your\s+|apna\s+|apne\s+)?"
            r"(?:net\s?banking\s+(?:id|password|login|details)|card\s+(?:number|details)|debit\s+card\s+details|"
            r"atm\s+pin|cvv|expiry\s+date|login\s+(?:id|details|password)|bank\s+details)\b"
            r"|\b(?:card\s+number|expiry\s+date|bank\s+details|net\s?banking\s+(?:id|password))\b" + _S + r"{0,30}?"
            rf"\b(?P<verb2>{_SHARE_VERB}|message|bhar\w*|likh\w*)\b"),
         negatable=True),
    Rule("R-REMOTE-ACCESS", "HIGH", "remote_access_app",
         _r(r"\b(?P<verb>install|download|open|use|kholo|khol\w*|chalao|daalo)\b" + _S + r"{0,30}?"
            r"\b(?:any\s?desk|team\s?viewer|quick\s?support|rust\s?desk|airdroid|ultra\s?viewer|screen\s?shar\w*)\b"
            r"|\b(?:any\s?desk|team\s?viewer|quick\s?support|rust\s?desk|airdroid)\b" + _S + r"{0,25}?"
            r"\b(?P<verb2>install|download|kholo|open)\b"),
         negatable=True),
    Rule("R-APK-INSTALL", "HIGH", "remote_access_app",
         _r(r"\.apk\b|\bapk\s+(?:file|download|install)|\b(?P<verb>download|install)\b" + _S + r"{0,25}?\bapk\b"),
         negatable=True),
    Rule("R-AUTHORITY-THREAT", "HIGH", "authority_threat",
         _r(r"\bdigital\s+arrest\b|\b(?:cbi|police|cyber\s*cell|cyber\s*crime\s+(?:branch|department)|customs|"
            r"narcotics|ncb|enforcement\s+directorate|trai|crime\s+branch|court|income\s*tax\s+officer)\b"
            r"[\s\S]{0,160}?\b(?:arrest\w*|warrant|giraftar\w*|video\s+call|drugs?|money\s+laundering|illegal|"
            r"fir|case\s+(?:registered|darj|filed)|jail|legal\s+action)\b"),
         demote_if_advisory=True),
    Rule("R-FEE-FOR-REWARD", "HIGH", "fee_for_reward",
         _r(r"\b(?P<verb>pay|deposit|transfer|send|bhejo|bhej\w*|jama|bharo|bhar\w*|submit)\b" + _S + r"{0,40}?"
            r"\b(?:registration|processing|activation|release|clearance|gst|tax|verification|joining|security|"
            r"insurance|courier|handling|unlock|withdrawal|token|file\s+charge)\s*(?:fee|fees|charges?|amount|deposit)"
            r"|\b(?:registration|processing|activation|release|clearance|gst|joining|security|unlock|withdrawal|"
            r"token)\s*(?:fee|fees|charges?)" + _S + r"{0,40}?\b(?:pay|deposit|bhejo|bhej\w*|jama|bharo|bhar\w*|"
            r"transfer|send)\b"
            r"|\b(?:fee|fees|charges?|tax|gst)\s+(?:bharo|bhejo|bhej\s+do|jama\s+kar\w*|pay\s+kar\w*)\b"),
         negatable=True, requires=_REWARD),
    Rule("R-TASK-EARNING", "HIGH", "fee_for_reward",
         _r(r"\b(?:earn|kamao|kamaye\w*|kamai|income)\b[\s\S]{0,80}?\b(?:lik(?:e|ing)\w*|subscrib\w*|rating|"
            r"rate|review\w*|tasks?|follow\w*)\b"
            r"|\b(?:lik(?:e|ing)|subscrib\w*|rating|rate|review\w*|tasks?)\b[\s\S]{0,80}?\b(?:earn|kamao|"
            r"kamaye\w*|kamai)\b"),
         requires=_r(r"\b(?:daily|per\s+day|a\s+day|roz|rozana|per\s+task|per\s+like|ghar\s+baithe|from\s+home|"
                     r"part[\s-]?time|weekly)\b")),
    Rule("R-GUARANTEED-RETURNS", "HIGH", "guaranteed_returns",
         _r(r"\b(?:guarantee\w*|assured|pakka|risk[\s-]?free|100\s*%\s*(?:safe|sure))\b" + _S + r"{0,40}?"
            r"\b(?:returns?|profit\w*|munafa|income)\b"
            r"|\b(?:returns?|profit|munafa)\b" + _S + r"{0,20}?\b(?:guaranteed|pakka|assured)\b"
            r"|\bdouble\s+(?:your\s+)?(?:money|paisa|amount|investment)|\bpaisa\s+double|\bdoguna\b"),
         requires=_r(r"(?<![\d.])\d{2,4}\s*%|\bdouble\b|\bdoguna\b|\bvip\b|\btips\b|\bsignals?\b|\bgroup\b|"
                     r"\btelegram\b|\bdaily\b|\bper\s+day\b")),
    Rule("R-NEW-NUMBER-PAYMENT", "HIGH", "personal_payment_handle",
         _r(r"\b(?:new\s+number|naya\s+number|lost\s+my\s+phone|phone\s+(?:kho|kharab|broke|toot)\w*)\b"),
         requires=_r(r"\b(?:send|pay|transfer|bhejo|bhej\w*|paise|money|rupees|rs\.?|upi|<UPI>)\b")),
    # MEDIUM: suspicious, never enough on their own.
    Rule("R-RETURNS-PROMISE", "MEDIUM", "guaranteed_returns",
         _r(r"\b(?:guarantee\w*|assured|pakka|risk[\s-]?free)\b" + _S + r"{0,40}?\b(?:returns?|profit\w*|munafa)\b")),
    Rule("R-ACCOUNT-THREAT", "MEDIUM", "account_block_threat", _r(_THREAT)),
    Rule("R-KYC-UPDATE", "MEDIUM", "credential_request",
         _r(rf"\b{_spaced('kyc')}\b{_S}{{0,40}}?\b(?:update|verify|complete|pending|expired?|upgrade|link)\b|"
            rf"\b(?:update|verify|complete)\b{_S}{{0,20}}?\b{_spaced('kyc')}\b")),
    Rule("R-AUTHORITY-CLAIM", "MEDIUM", "authority_threat",
         _r(r"\b(?:cbi|cyber\s*cell|customs|narcotics|ncb|enforcement\s+directorate|crime\s+branch|"
            r"income\s*tax\s+officer)\b")),
    Rule("R-PERSONAL-PAYMENT", "MEDIUM", "personal_payment_handle",
         _r(r"\b(?P<verb>pay|send|transfer|bhejo|bhej\s+do|bhejiye|jama)\b" + _S + r"{0,40}?(?:<UPI>|<PHONE>|"
            r"\bupi\s*id\b|[\w.-]+@(?:ybl|okaxis|oksbi|okhdfcbank|okicici|paytm|upi|ibl|axl|apl|fbl)\b|"
            r"\bthis\s+number\b|\bis\s+number\b|\bmy\s+number\b|\bmere\s+number\b)"),
         negatable=True),
    Rule("R-PRIZE-CLAIM", "MEDIUM", None,
         _r(r"\b(?:you\s+(?:have\s+)?won|winner|lottery|lucky\s+draw|jackpot|kbc|kaun\s+banega|jeet\s+liya|"
            r"jeeta\s+hai|jeete\s+hain|inaam)\b")),
    Rule("R-PROMPT-INJECTION", "MEDIUM", "prompt_injection",
         _r(r"\bignore\s+(?:all\s+|any\s+)?(?:previous|prior|above|earlier)\s+instructions\b|"
            r"\bnote\s+to\s+(?:the\s+)?(?:ai|assistant|model|checker|classifier|system)\b|"
            r"\b(?:ai|scam|spam|fraud)\s+(?:checker|detector|filter|classifier)\b|"
            r"\b(?:classify|mark|label|treat)\s+(?:this|it)\s+as\s+(?:safe|legit\w*|genuine|not\s+(?:a\s+)?scam)\b|"
            r"\byou\s+are\s+(?:now\s+)?(?:an?\s+)?(?:ai|assistant|chatbot|language\s+model)\b|"
            r"(?:^|[.!?]\s*)(?:system|assistant)\s*:|\bno_strong_signals\b|\bnot_scam\b|\brespond\s+with\b"),
         blocks_reassurance=True),
    Rule("R-SELF-CERTIFIED", "MEDIUM", None,
         _r(r"\b(?:this\s+(?:message|sms|link)\s+is\s+(?:verified|certified|confirmed|100%)\s*(?:safe|genuine|"
            r"legit\w*|official)|(?:this\s+is\s+)?not\s+a\s+(?:scam|fraud)|yeh\s+(?:fraud|scam)\s+nahi|"
            r"100\s*%\s+(?:safe|genuine|legit\w*))\b"),
         blocks_reassurance=True),
    # LOW: context only; never changes a verdict.
    Rule("R-URGENCY", "LOW", "urgency",
         _r(r"\b(?:urgent\w*|immediately|turant|jaldi|right\s+now|last\s+chance|final\s+(?:notice|warning|reminder)|"
            r"within\s+\d+\s*(?:hours?|hrs?|minutes?|mins?)|aaj\s+raat|tonight|expires?\s+today)\b")),
)
RULE_IDS = tuple(r.id for r in RULES) + ("R-THREAT-WITH-ACTION",)
_REQUESTED = re.compile(r"\bas\s+(?:per\s+)?(?:your\s+)?request(?:ed)?\b|\bat\s+your\s+request\b", _F)


def _negated(text: str, m: re.Match) -> bool:
    for g in ("verb", "verb2"):
        if m.groupdict().get(g):
            s, e = m.span(g)
            if _NEG_BEFORE.search(text[max(0, s - 30):s]) or _NEG_AFTER.search(text[e:e + 15]):
                return True
    return False


def _first_match(rule: Rule, text: str) -> re.Match | None:
    if rule.requires and not rule.requires.search(text):
        return None
    for m in rule.pattern.finditer(text):
        if rule.negatable and _negated(text, m):
            continue
        if rule.exempt and rule.exempt.search(text[max(0, m.start() - 80):m.end() + 80]):
            continue
        return m
    return None


def run_rules(text: str, *, unofficial_link: bool = False) -> list[Signal]:
    """Signals for `text` (already passed through parse()). `unofficial_link`: the message carries a URL that is
    not a known official brand domain, used by the threat-plus-action composite."""
    out: list[Signal] = []
    advisory = bool(_ADVISORY.search(text))
    for rule in RULES:
        m = _first_match(rule, text)
        if m is None:
            continue
        severity = "MEDIUM" if (rule.demote_if_advisory and advisory and rule.severity == "HIGH") else rule.severity
        out.append(Signal(id=rule.id, severity=severity, source="rule", evidence_type=rule.evidence_type,
                          quote=m.group(), start=m.start(), end=m.end(),
                          blocks_reassurance=rule.blocks_reassurance))
    # Composite: a future block/disconnect threat that pushes the reader to a link or a phone call.
    threat = re.search(_THREAT, text, _F)
    if threat and _FUTURE.search(text) and (unofficial_link or _CALL_TO_ACTION.search(text)) \
            and not advisory and not _REQUESTED.search(text):
        out.append(Signal(id="R-THREAT-WITH-ACTION", severity="HIGH", source="rule",
                          evidence_type="account_block_threat", quote=threat.group(),
                          start=threat.start(), end=threat.end()))
    return out
