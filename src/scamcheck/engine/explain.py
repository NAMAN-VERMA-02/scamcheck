"""Evidence-grounded explanations in English or Hinglish.

Every sentence comes from a template keyed by a signal id that actually fired, a verdict, or a reason code.
Nothing here can add a red flag that the engine did not find, and no wording calls a message "safe".
"""

from __future__ import annotations

from .models import ExplainedSignal, Signal

# id → (English title, English detail, Hinglish title, Hinglish detail)
TEXT: dict[str, tuple[str, str, str, str]] = {
    "R-OTP-REQUEST": ("Asks you to share an OTP, PIN or password",
                      "Banks, couriers and government offices never ask you to send these codes to anyone.",
                      "OTP, PIN ya password maanga gaya hai",
                      "Bank, courier ya sarkari office kabhi yeh code kisi ko bhejne ko nahi kehte."),
    "R-PIN-TO-RECEIVE": ("Asks for a UPI PIN to receive money",
                         "A UPI PIN is only needed to send money. Entering it never brings money in.",
                         "Paisa paane ke liye UPI PIN maanga gaya hai",
                         "UPI PIN sirf paisa bhejne ke liye lagta hai, paisa lene ke liye kabhi nahi."),
    "R-COLLECT-REQUEST": ("Asks you to approve a payment request to receive money",
                          "Approving a collect request takes money out of your account.",
                          "Paisa paane ke liye request approve karne ko kaha gaya hai",
                          "Collect request approve karne se paisa aapke account se jaata hai."),
    "R-CREDENTIAL-REQUEST": ("Asks for card or net-banking details",
                             "Card numbers, CVV, expiry dates and login details should never be sent by message.",
                             "Card ya net-banking details maangi gayi hain",
                             "Card number, CVV, expiry ya login details message par kabhi mat bhejiye."),
    "R-REMOTE-ACCESS": ("Asks you to install a screen-sharing app",
                        "Apps like AnyDesk or TeamViewer let someone else control your phone and your bank apps.",
                        "Screen-sharing app install karne ko kaha gaya hai",
                        "AnyDesk ya TeamViewer jaise apps se koi aur aapka phone aur bank app chala sakta hai."),
    "R-APK-INSTALL": ("Asks you to install an app file (APK)",
                      "App files sent by message can read your SMS, including OTPs.",
                      "APK file install karne ko kaha gaya hai",
                      "Message se aayi app file aapke SMS aur OTP padh sakti hai."),
    "R-AUTHORITY-THREAT": ("Uses police, CBI or court threats",
                           "Real agencies do not arrest people over video calls or demand payment to close a case.",
                           "Police, CBI ya court ka dar dikhaya gaya hai",
                           "Asli agencies video call par arrest nahi karti aur case band karne ke paise nahi maangti."),
    "R-FEE-FOR-REWARD": ("Asks for a fee before you get a prize, loan, job or refund",
                         "Paying to unlock money you were promised is the core pattern of advance-fee fraud.",
                         "Inaam, loan, naukri ya refund se pehle fee maangi gayi hai",
                         "Pehle fee bharo phir paisa milega — yahi advance-fee fraud ka tareeka hai."),
    "R-TASK-EARNING": ("Promises easy daily earnings for likes, ratings or tasks",
                       "Task-based job offers usually ask for deposits after small first payouts.",
                       "Like/rating/task se roz kamai ka vaada",
                       "Aise task jobs pehle thoda paisa dete hain, phir bada deposit maangte hain."),
    "R-GUARANTEED-RETURNS": ("Promises guaranteed or very high returns",
                             "No real investment can guarantee high or doubled returns.",
                             "Guaranteed ya bahut zyada munafe ka vaada",
                             "Koi asli investment pakka ya double return guarantee nahi karta."),
    "R-NEW-NUMBER-PAYMENT": ("Someone on a 'new number' asks for money",
                             "Call the person on the number you already have before paying anything.",
                             "'Naye number' se paise maange gaye hain",
                             "Paise bhejne se pehle us vyakti ko unke purane number par call kijiye."),
    "R-RETURNS-PROMISE": ("Mentions assured returns", "Assured-return claims need independent checking.",
                          "Pakke return ki baat", "Pakke return ke daavon ko alag se jaanchiye."),
    "R-ACCOUNT-THREAT": ("Says an account, card or service will be blocked or cut",
                         "Threats of blocking are used to rush you. Check in your official app instead.",
                         "Account, card ya service band hone ki baat",
                         "Band hone ka dar jaldi karwane ke liye hota hai. Official app mein khud check kijiye."),
    "R-THREAT-WITH-ACTION": ("Threatens a block or cut-off and pushes you to a link or call",
                             "A deadline plus a link or phone number is a common pattern in impersonation scams.",
                             "Band karne ki dhamki ke saath link ya call",
                             "Deadline ke saath link ya phone number — yeh nakli bank/bijli messages ka pattern hai."),
    "R-KYC-UPDATE": ("Asks you to update KYC", "KYC is updated in the official app or branch, not through message links.",
                     "KYC update karne ko kaha gaya hai", "KYC official app ya branch mein hota hai, message ke link se nahi."),
    "R-AUTHORITY-CLAIM": ("Claims to be from an enforcement agency", "Verify through the agency's official contact.",
                          "Kisi sarkari agency ka naam liya gaya hai", "Agency ke official number se khud confirm kijiye."),
    "R-PERSONAL-PAYMENT": ("Asks for payment to a personal UPI id or number",
                           "Organisations collect payments through their own app or site, not personal handles.",
                           "Personal UPI id ya number par paisa maanga gaya hai",
                           "Companies apne app ya site se paisa leti hain, personal UPI id se nahi."),
    "R-PRIZE-CLAIM": ("Says you won a prize or lottery", "Unexpected prizes are a common lure.",
                      "Inaam ya lottery jeetne ki baat", "Achanak inaam milna aam jaal hai."),
    "R-PROMPT-INJECTION": ("Contains instructions aimed at automated checkers",
                           "Real messages do not address AI checkers. The engine ignores such instructions.",
                           "Automated checker ke liye nirdesh likhe hain",
                           "Asli messages AI checker se baat nahi karte. Engine in nirdeshon ko nahi maanta."),
    "R-SELF-CERTIFIED": ("Claims to be verified, genuine or 'not a scam'",
                         "A message vouching for itself proves nothing.",
                         "Message khud ko genuine ya 'scam nahi' bata raha hai",
                         "Message ka khud ko sahi batana koi saboot nahi hai."),
    "R-URGENCY": ("Creates urgency", "Pressure to act immediately is a common manipulation tactic.",
                  "Jaldi karne ka dabaav", "Turant kuch karne ka dabaav aam chaal hai."),
    "I-HIDDEN-CHARS": ("Contains hidden characters", "Invisible characters are used to slip past keyword filters.",
                       "Chhupe hue characters hain", "Invisible characters filters se bachne ke liye daale jaate hain."),
    "I-CONFUSABLES": ("Uses lookalike letters from other alphabets",
                      "Letters such as Cyrillic 'о' look identical to Latin 'o' and are used to disguise words.",
                      "Doosri lipi ke milte-julte akshar",
                      "Cyrillic 'о' jaise akshar Latin 'o' jaise dikhte hain aur shabd chhupane ke kaam aate hain."),
    "U-BRAND-LOOKALIKE": ("Link imitates a known brand's domain",
                          "The address contains a brand name but is not that brand's domain.",
                          "Link kisi brand jaisa dikhta hai", "Address mein brand ka naam hai par woh brand ka domain nahi hai."),
    "U-PUNYCODE": ("Link uses international characters in the domain",
                   "Such domains can look identical to a real one.",
                   "Domain mein international characters", "Aise domain asli jaise dikh sakte hain."),
    "U-USERINFO-TRICK": ("Link hides its real destination before an '@'",
                         "Everything before '@' is ignored by the browser; the real site comes after it.",
                         "'@' ke peeche asli address chhupa hai", "'@' se pehle ka hissa browser ignore karta hai."),
    "U-APK-DOWNLOAD": ("Link downloads an Android app file", "Do not install apps from message links.",
                       "Link se APK download hota hai", "Message ke link se app install mat kijiye."),
    "U-IP-HOST": ("Link uses a raw IP address", "Legitimate services use named domains.",
                  "Link mein seedha IP address", "Asli services naam wale domain use karti hain."),
    "U-SUSPICIOUS-TLD": ("Link uses a domain ending often seen in phishing",
                         "This is a weak structural hint, not a reputation result.",
                         "Domain ka ending phishing mein aksar dikhta hai",
                         "Yeh sirf structure ka ishaara hai, reputation check nahi."),
    "U-SHORTENER": ("Link is shortened", "The real destination is hidden and was not checked.",
                    "Short link hai", "Asli address chhupa hai aur check nahi hua."),
    "U-FREE-HOSTING": ("Link is on a free hosting platform", "Anyone can create such a site in minutes.",
                       "Free hosting par link", "Aisi site koi bhi minuton mein bana sakta hai."),
    "U-UNPARSEABLE": ("Link could not be read", "Malformed links are a warning sign.",
                      "Link samajh nahi aaya", "Bigda hua link khatre ka ishaara hai."),
    "U-CHAT-HANDOFF": ("Moves the conversation to Telegram or WhatsApp", "Scams often move to private chats.",
                       "Telegram/WhatsApp par le jaata hai", "Scam aksar private chat mein le jaate hain."),
    "U-DEEP-SUBDOMAIN": ("Link has many subdomains", "Long addresses can bury a fake domain.",
                         "Link mein bahut saare subdomain", "Lambe address mein nakli domain chhup sakta hai."),
    "U-NO-TLS": ("Link is not encrypted (http)", "A weak hint only.", "Link encrypted nahi (http)", "Sirf halka ishaara."),
    "U-ODD-PORT": ("Link uses an unusual port", "A weak hint only.", "Link mein alag port", "Sirf halka ishaara."),
}

HEADLINE = {
    ("LIKELY_SCAM", "english"): "Likely scam — strong warning signs found",
    ("UNCLEAR", "english"): "Unclear — we could not confirm either way",
    ("NO_STRONG_SIGNALS", "english"): "No strong scam signals found — this is not a guarantee",
    ("LIKELY_SCAM", "hinglish"): "Shayad scam hai — khatre ke saaf nishaan mile",
    ("UNCLEAR", "hinglish"): "Pakka nahi keh sakte — dono taraf confirm nahi hua",
    ("NO_STRONG_SIGNALS", "hinglish"): "Koi bada scam nishaan nahi mila — yeh guarantee nahi hai",
}

GUIDANCE = {
    ("LIKELY_SCAM", "english"): [
        "Do not click links, share codes, install apps or pay.",
        "Contact the organisation through its official app or the number on your card or bill — not the one in the message.",
        "In India you can report fraud at cybercrime.gov.in or call 1930. If you already paid, call immediately.",
    ],
    ("UNCLEAR", "english"): [
        "Treat it with caution until you verify it independently.",
        "Open the official app or website yourself instead of using any link or number in the message.",
        "Never share an OTP, PIN or password, whoever asks.",
    ],
    ("NO_STRONG_SIGNALS", "english"): [
        "We found no strong warning signs, but that does not prove the message is genuine.",
        "If it later asks for money, codes or an app install, stop and verify.",
    ],
    ("LIKELY_SCAM", "hinglish"): [
        "Link mat kholiye, code mat bataiye, app install mat kijiye, paisa mat bhejiye.",
        "Company se uske official app ya card/bill par likhe number se sampark kijiye — message wale number se nahi.",
        "Fraud ki report cybercrime.gov.in par ya 1930 par call karke kijiye. Paisa chala gaya ho to turant call kijiye.",
    ],
    ("UNCLEAR", "hinglish"): [
        "Khud confirm karne tak saavdhan rahiye.",
        "Message ke link ya number ki jagah official app ya website khud kholiye.",
        "OTP, PIN ya password kisi ko bhi mat bataiye.",
    ],
    ("NO_STRONG_SIGNALS", "hinglish"): [
        "Koi bada khatra nahi dikha, par isse message asli sabit nahi hota.",
        "Agar baad mein paisa, code ya app install maange to ruk kar confirm kijiye.",
    ],
}

REASON_NOTE = {
    "model_not_configured": ("Rule-only mode: no language model is configured, so the engine does not offer reassurance.",
                             "Sirf rules mode: koi language model set nahi hai, isliye engine bharosa nahi dilata."),
    "model_not_opted_in": ("You did not opt in to model analysis, so the engine does not offer reassurance.",
                           "Aapne model analysis chuna nahi, isliye engine bharosa nahi dilata."),
    "model_timeout": ("The model did not answer in time; the result falls back to rules only.",
                      "Model ne samay par jawab nahi diya; sirf rules ka nateeja hai."),
    "model_error": ("The model call failed; the result falls back to rules only.",
                    "Model call fail hua; sirf rules ka nateeja hai."),
    "model_invalid_output": ("The model's answer was not valid; it was ignored.",
                             "Model ka jawab sahi format mein nahi tha; use ignore kiya gaya."),
    "model_skipped_residual_pii": ("Personal details were still visible after redaction, so nothing was sent to the model.",
                                   "Redaction ke baad bhi personal details dikh rahi thi, isliye model ko kuch nahi bheja."),
    "url_destination_not_verified": ("The message contains a link whose destination and reputation were not checked.",
                                     "Message mein link hai jiska destination aur reputation check nahi hua."),
}


def explain_signals(signals: list[Signal], language: str) -> list[ExplainedSignal]:
    hi = language == "hinglish"
    out = []
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    for s in sorted(signals, key=lambda s: order[s.severity]):
        en_t, en_d, hi_t, hi_d = TEXT[s.id]
        out.append(ExplainedSignal(id=s.id, severity=s.severity, source=s.source, title=hi_t if hi else en_t,
                                   detail=hi_d if hi else en_d, quote=s.quote, start=s.start, end=s.end))
    return out


def notes_for(reasons: list[str], language: str) -> list[str]:
    idx = 1 if language == "hinglish" else 0
    return [REASON_NOTE[r][idx] for r in reasons if r in REASON_NOTE]
