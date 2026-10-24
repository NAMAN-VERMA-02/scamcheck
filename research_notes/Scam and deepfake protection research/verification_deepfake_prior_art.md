# Prior art: family/trusted-contact verification, deepfake detection, and scam transaction interruption (as of Oct 2026)

## Q1. Does family / trusted-contact out-of-band verification already exist? ("Caller claims to be your son; you tap verify; the real son confirms on an enrolled device")

### Takeaway
The core idea is NOT novel as of Oct 2026. Google shipped an automatic version on Android in June 2026 (Phone by Google "fake call detection": the recipient's phone silently checks with the real contact's device over RCS whether that device is actually calling). At least one small app (Rooky) offers exactly the manual "tap verify, relative confirms with Face ID on their registered phone" flow, and another (KinConfirm) is reported to do the same. Free low-tech alternatives (a family safe word plus calling back on a known number) are the mainstream advice. Remaining room: cross-platform coverage (iOS, WhatsApp, other dialers), callers who use a new or unknown number ("I lost my phone, this is a friend's phone"), and getting both relatives to enrol before the scam happens.

### Cited Findings
**Platform-level (launched)**
- Google Android "fake call detection" (blog dated 2 June 2026): when a contact calls and both people use Phone by Google, "their device sends a silent confirmation signal in real time to your device to verify the call is legitimate". If the signal is missing, your device contacts the real device. If that device reports no active call, you get "a warning on your screen advising you to hang up immediately". It runs over end-to-end encrypted RCS and is on by default — [Google blog](https://blog.google/security/android-fake-call-detection/)
- Requirements: Android 12+, Phone by Google, Contacts and Google Messages installed, RCS enabled, and BOTH parties on Phone by Google. Rolling out "globally", starting with Pixel. Google says it is built on the open RCS standard so other apps could adopt it; no other adopters are named — [Google blog](https://blog.google/security/android-fake-call-detection/); [TechCrunch, 2 Jun 2026](https://techcrunch.com/2026/06/02/google-rolls-out-fake-call-detection-to-protect-against-ai-deepfake-impersonation-scams/)
- Neither source covers what happens if the contact's phone is offline, false positives, or calls from unknown or new numbers. Google presents the feature as one layer alongside "verified financial calls" and call scam detection — [TechCrunch](https://techcrunch.com/2026/06/02/google-rolls-out-fake-call-detection-to-protect-against-ai-deepfake-impersonation-scams/); [Google blog](https://blog.google/security/android-fake-call-detection/)
- Truecaller family protection: a free group feature in which an admin gets alerts about fraud calls that members receive. On Android, the admin can remotely end a member's call. The admin can also share blocklists and see Android members' status (battery, driving). It launched Dec 2025 in Sweden, Chile, Malaysia and Kenya, and has since gone worldwide, including India. Truecaller is exploring AI that screens calls and hangs up on phrases like "digital arrest". This is guardian intervention, not identity verification — [TechCrunch, 12 Mar 2026](https://techcrunch.com/2026/03/12/truecallers-now-lets-you-hang-up-on-scammers-on-behalf-of-your-family/)

**Startup apps (launched but small; no adoption data or independent review)**
- Rooky (Rooky, Inc., © 2026): a free iOS/Android app. You choose a contact and send a request to the phone that person registered with Rooky, "not to the number, account, or meeting that raised your concern". They confirm with Face ID, fingerprint or passcode. Results are Verified, Denied or Expired. It has two modes: "Verify Person", and "Verify Request", which confirms a specific amount, change and time. Both parties need the app. It works alongside calls, SMS, WhatsApp, email, Zoom, Meet and Teams. The page gives no launch date, user numbers or third-party audit — [rooky.app](https://www.rooky.app/)
- KinConfirm (iOS): reported as a one-tap identity check sent to the relative's phone, confirmed by Face ID, fingerprint or a backup question, and returning yes/no before money is sent. Free with in-app purchases. This comes from a search-result summary only; I did not fetch the listing or verify the company — [search lead: App Store listing id6751080203](https://apps.apple.com/us/app/-/id6751080203) (unverified mapping)
- SureMark (iOS): reportedly "verifies identity and authorization at the source" across calls, video, text and web, rather than detecting fakes. Unverified beyond the App Store snippet — [App Store](https://apps.apple.com/ee/app/suremark/id6753729698)
- Safewords.io: a free tool to set up a family safe word in about 5 minutes, with "no app to install". It suggests agreeing which situations require the word, such as wire instructions or urgent requests — [safewords.io](https://safewords.io/)

**Non-product guidance (safe words / callback)**
- National Cybersecurity Alliance (StaySafeOnline) "Safe Word" campaign: a pre-agreed code word or phrase known only to the trusted group, asked for when an urgent call or message arrives — [StaySafeOnline](https://www.staysafeonline.org/campaigns/safeword)
- Standard advice pairs the code word with hanging up and calling back on a number you already trust — [Making Sense of Security](https://makingsenseofsecurity.com/how-to/awareness/set-a-family-code-word-to-beat-voice-cloning-scams/)

**Caller-ID authentication standards**
- STIR/SHAKEN (US): evidence on effectiveness is mixed. One 2023 paper notes robocalls hit a record 5.5bn in Oct 2022, after the mandate. The FCC triennial efficacy proceeding shows commenters split on whether to judge it by authentication or by robocall reduction — [arXiv 2306.06198](https://arxiv.org/pdf/2306.06198); [FCC triennial report](https://docs.fcc.gov/public/attachments/DOC-416732A1.pdf)
- India CNAP (Calling Name Presentation, KYC-registered name shown by default): the timeline slipped. DoT set a March 2026 nationwide deadline, and an Oct 2026 report says CNAP becomes mandatory from 1 Nov 2026 on supported 4G/5G handsets. Sources conflict on dates — [Business Standard](https://www.business-standard.com/industry/news/cnap-service-nationwide-rollout-by-march-2026-dot-trai-telecom-125102901190_1.html); [News Karnataka, Oct 2026](https://newskarnataka.com/technology/india-makes-caller-name-display-mandatory-from-nov-1/15102026/)
- Note: STIR/SHAKEN and CNAP authenticate the number or registered subscriber name, not the person. A scammer on their own number with a cloned voice saying "I'm on a friend's phone" is not addressed by either.

**Evidence that the threat is real**
- Harvard/Meta survey experiment (n≈4,100 US adults, YouGov, May 2025): the cloned-voice "sister in distress" scenario had the highest self-reported compliance (36.1%). Willingness to comply did not differ significantly between AI and human voices. Participants correctly identified only 32.6% of human voices as human, so they were suspicious rather than accurate. Heavy AI users were no better at detecting AI voices (51.2% vs 54.4%). The authors recommend verifying "caller identity through independent channels" and do not mention code words. Compliance was self-reported — [Heiding et al., arXiv 2607.09970](https://arxiv.org/html/2607.09970v1)
- FBI IC3 2025: adults 60+ reported $7.75bn in losses (up about 59%) across about 201k complaints. IC3 notes voice cloning used to mimic "a loved one in distress" in grandparent scams. More than 3,100 senior complaints referenced AI, with over $352m in losses — [AARP](https://www.aarp.org/money/scams-fraud/fbi-ftc-report-2025-losses.html); [HousingWire](https://www.housingwire.com/articles/fbi-seniors-cybercrime-2025/)

### Inferences
- The "enrolled device of the real relative confirms" pattern is now prior art twice over: Google's automatic version for spoofed known numbers, and Rooky's manual tap-to-verify. A new product would need a differentiator, such as cross-platform/iOS/WhatsApp coverage, handling the "new number" pretext, binding confirmation to a specific transaction (Rooky's "Verify Request" already does this), or distribution through banks or telcos.
- Google's design covers spoofed caller ID from a known contact. It does not cover the commonest pretext of grandparent scams: an unknown number plus "I lost my phone" or "I'm with a lawyer/police officer". A manual verify request to the relative's enrolled device does cover that case, so manual verification still adds value over Google's version.
- Adoption is the main barrier for any two-sided app: both parties must install it and enrol before the emergency. Safe words are free, need no device, and are the incumbent "good enough" alternative.

### Gaps
- Not verified in this session (search budget): Apple Recovery Contacts / Legacy Contact (account recovery, not caller verification); FINRA Rule 4512 trusted-contact person (US broker-dealer rule to contact a named person about suspected exploitation, not caller verification); Starling/Monzo features; Carefull, EverSafe and Charlie (financial monitoring for seniors); Aura/Norton family plans; Life360; "Ask Silver"; any consumer Pindrop. None of these were confirmed in this session to offer relative-device caller verification.
- No adoption numbers, funding or reviews were found for Rooky, KinConfirm or SureMark. No evidence was found of a failed or shut-down family-verification product.
- No academic study found that measures the real-world effectiveness of family code words or out-of-band callbacks against voice-clone scams.
- UK/EU caller-ID spoofing rules (Ofcom, which requires blocking calls from invalid or spoofed UK numbers) were not checked this session.

## Q2. Threats to such a design (SIM swap, account takeover, stolen phones, coercion)

### Takeaway
SIM swap and account takeover are real but small next to impersonation-scam volumes. A design anchored to device biometrics on an app-enrolled phone, rather than to the phone number, avoids the SIM-swap path. Device theft with a known passcode, coercion, and compromised enrolment remain open risks.

### Cited Findings
- FBI IC3: SIM swap complaints fell from 2,026 ($72.7m) in 2022 to 1,075 ($48.8m) in 2023 and 982 ($26.0m) in 2024. The decline may reflect reporting changes, and losses are often booked as account takeover instead. These are secondary sources quoting IC3 — [Deepstrike](https://deepstrike.io/blog/sim-swap-scam-statistics-2025); [Efani](https://www.efani.com/blog/sim-swap-fraud-statistics-2026)
- Cifas (UK): about 3,000 unauthorised SIM swaps in 2024, described as a 1,055% surge. A secondary source claims +38% in 2025 and more than 78,000 UK account-takeover cases (18% of filings); I did not verify these against Cifas Fraudscape 2026 — [Efani](https://www.efani.com/blog/sim-swap-fraud-statistics-2026); [Voxbooster](https://voxbooster.com/blog/telecom-fraud-sim-swap-statistics-2026)
- Rooky confirms via the device biometric or passcode on the registered phone, not the phone number. This sidesteps SIM swap but not phone theft combined with a known passcode — [rooky.app](https://www.rooky.app/)

### Inferences
- Threat model priorities: (1) the relative is unreachable during a real emergency. This is the false-negative / "Expired" case, and the scam script itself claims "my phone is broken". (2) Re-enrolment or account recovery is a takeover path: if a scammer can enrol a new device for "the son", the system fails. (3) Coercion or a socially engineered relative tapping "approve". (4) Stolen unlocked phone.
- A "deny/expired" result must not be read as "scam", or real emergencies get blocked. It should prompt the user to call back on a known number or contact another family member.

### Gaps
- No prevalence data found for coerced approvals or stolen-phone misuse in family-verification flows.
- Primary IC3 2025 and Cifas 2026 SIM-swap figures were not fetched.

## Q3. Deepfake voice/video detection: products and independent evidence

### Takeaway
Detection works well on benchmarks but degrades on unseen generators, compression, telephony codecs and adversarial attacks. The official ASVspoof 5 overview says this directly. Independent product tests are few and vary widely. Vendor accuracy claims of about 99% are not trustworthy for phone-quality calls. Verification by a shared secret or enrolled device avoids depending on detection.

### Cited Findings
- ASVspoof 5 official overview (Wang, Delgado, Evans, Kinnunen, Yamagishi et al.): 53 teams. "Many systems perform well, but performance drops under adversarial attacks and after neural encoding or compression." It uses a crowdsourced, attack-disjoint evaluation — [arXiv 2601.03944](https://arxiv.org/abs/2601.03944)
- A search-snippet summary of the same paper reports the top open-condition minDCF of about 0.075, credited to self-supervised front ends (wav2vec 2.0). A table shows several systems at about 3–4% EER on ASVspoof 5 Track 1 versus about 7–15% EER on In-the-Wild. I could not verify the table mapping because the PDF did not parse — [arXiv PDF 2601.03944](https://arxiv.org/pdf/2601.03944)
- "Does Audio Deepfake Detection Generalize?" (Müller et al. 2022): on real-world In-the-Wild audio, detector EERs deteriorate by about 200–1000% relative to benchmark performance — [arXiv 2203.16263](https://arxiv.org/pdf/2203.16263)
- Müller et al. (Interspeech 2024) attribute the generalisation gap mainly to dataset differences, not task "hardness" — [ISCA archive](https://www.isca-archive.org/interspeech_2024/muller24b_interspeech.pdf)
- A 2025 study found that adding ASVspoof 5 training data helped some test sets but hurt In-the-Wild performance — [arXiv 2507.01750](https://arxiv.org/pdf/2507.01750)
- Products and claims (treat as marketing unless noted):
  - Pindrop claims "independently validated" 99% accuracy — [pindrop.com](https://www.pindrop.com/)
  - An NPR evaluation of 84 short clips reportedly had Pindrop correct on 81 (96.4%), the best of the tools tested. A "Podonos benchmark" (June 2026) reportedly gave Pindrop 95.05% accuracy with 6.2% false positives, and Reality Defender 71.27% with a 53.7% false-positive rate. These come via aggregator sites; I did not verify the NPR or Podonos originals — [fast.io](https://fast.io/resources/ai-voice-detector-tools-2026/); [theexpertranking](https://theexpertranking.com/detection/best-deepfake-detectors/)
  - Hiya claims first place in average accuracy on the Hugging Face Speech Deepfake Arena (unverified). It has consumer offerings (Hiya AI Phone app, a Chrome extension) — [layer3labs](https://www.layer3labs.io/comparisons/ai-voice-detectors-compared)
  - McAfee: no independent test found. One low-quality listing gives "Project Mockingbird 74.3%" with unclear methodology, so it is unreliable — [theairankings](https://theairankings.com/best-deepfake-detectors/)
- Humans are poor detectors: in the Harvard/Meta study, only 32.6% of human voices were correctly judged human, and text-based detection was 53% — [arXiv 2607.09970](https://arxiv.org/html/2607.09970v1)

### Inferences
- A detector-only consumer product would face high false-positive rates on compressed, noisy phone audio and degrade on new generators. False alarms on real family calls would erode trust quickly. Detection works better as a supplementary signal than as the decision.
- The Harvard/Meta finding that compliance tracks persuasiveness, not human-likeness, suggests that defeating the urgency script, for example "pause and verify", matters more than identifying synthetic audio.

### Gaps
- Not verified this session: Resemble AI Detect, Intel FakeCatcher (status/accuracy), Sensity, TrueMedia.org's status (reported to have shut down in early 2025, with an open-source release, but unconfirmed here), Pindrop Pulse consumer availability, and AASIST/RawNet2 baseline numbers on ASVspoof 5.
- Original NPR and Podonos test reports were not fetched, and exact ASVspoof 5 EER/minDCF figures per condition remain unverified.
- No independent evaluation was found of on-device consumer deepfake call detectors on real telephony audio.

## Q4. Transaction interruption: bank and telecom measures — which demonstrably reduce losses?

### Takeaway
The strongest measured result is the UK's mandatory APP reimbursement. An independent review found Faster Payments fraud losses fell about 21% (about £73m/year), and 88% of money lost is now reimbursed. Payee-name checks (UK CoP, EU VoP from 9 Oct 2025, Australia CoP from July 2025) are widely deployed. They stop misdirection, but by design they do not stop a victim paying a correctly named account under social engineering. Australia's losses are down about 30% from the 2022 peak but rose 7.8% in 2025. Telco stunts like O2 Daisy have no loss-reduction evidence.

### Cited Findings
- UK PSR APP reimbursement (in force Oct 2024):
  - 88% (£316m) of money lost reimbursed over the first 18 months. 82% of claims closed within 5 business days, and about 2% rejected for lack of customer caution. UK Finance reported 61% for 2024, though the PSR says the figures are not comparable — [PSR dashboard Q1 2026](https://www.psr.org.uk/information-for-consumers/app-scams-reimbursement-dashboard/)
  - Independent Frontier Economics review (1 July 2026): Faster Payments fraud losses fell about 21% (about £73m a year), reimbursement rates rose from 54% to 65%, and 97% of in-scope claims are reimbursed — [PSR news](https://www.psr.org.uk/news-and-updates/latest-news/news/payment-fraud-falls-by-73m-following-psr-reimbursement-scheme/)
  - Policy: the government proposes folding the PSR into the FCA — [Monek](https://www.monek.com/resources/news/app-fraud-reimbursement-one-year-review-2026/)
- UK Confirmation of Payee: no quantified standalone effectiveness evaluation found in this session — [nhimg guide](https://nhimg.org/authorised-push-payment-app-fraud-guide)
- EU Verification of Payee: mandatory for euro-area PSPs from 9 Oct 2025 under the Instant Payments Regulation; non-euro states by 9 July 2027. The EPC VoP rulebook took effect 5 Oct 2025. An early bank analysis saw no rise in abandoned transactions — [Natixis CIB](https://home.cib.natixis.com/articles/verification-of-payee-a-promising-start); [SurePay](https://www.surepay.eu/verification-of-payee-in-the-eu/)
  - Trustpair notes VoP does not address social-engineering fraud such as CEO fraud — [Trustpair](https://trustpair.com/blog/verification-of-payee/)
- Australia Scam-Safe Accord (Nov 2023; ABA plus COBA): six initiatives, including CoP, biometric checks on new accounts, payment delays, intelligence sharing, and limits on high-risk channels such as crypto — [Lexology](https://www.lexology.com/library/detail.aspx?g=1acef28f-ae7a-4307-85c4-ca0edd22079e); [ABC](https://www.abc.net.au/news/2025-07-03/banks-to-roll-out-confirmation-of-payee-system-to-combat-scams/105485526)
  - CoP launched July 2025 and has been used more than 100m times — [AP+](https://www.auspayplus.com.au/banks-hit-major-milestones-as-scam-fighting-technology-stops-thousands-of-risky-transfers)
  - NASC Targeting Scams 2025: $2.18bn reported losses, up 7.8% on 2024 but down 29.7% from the $3.1bn 2022 peak. Investment scams were the largest category at $837.7m — [NASC report](https://www.nasc.gov.au/system/files/targeting-scams-report-2025.pdf); [ACCC](https://www.accc.gov.au/media-release/continued-action-critical-to-combat-fraud-as-annual-scam-losses-exceed-2-billion)
  - Consumer advocates criticise the lack of a compensation pathway — [Consumer Action](https://consumeraction.org.au/wrong-direction-australians-robbed-of-2-2-billion-in-2025-the-status-quo-on-scams-is-totally-unacceptable-say-consumer-advocates/)
- Singapore Money Lock (DBS/POSB, OCBC, UOB, from Nov 2023): locked funds cannot be moved digitally and need in-person or assisted unlocking. Sources differ on the details — [Yahoo Finance SG](https://sg.finance.yahoo.com/news/customers-singapore-dbs-posb-uob-ocbc-banks-lock-up-money-cant-withdrawn-online-104025182.html); [Seedly](https://blog.seedly.sg/money-lock-singapore/)
- India NPCI: MyUPI on BHIM (Sept 2026) lets users block a linked bank account and includes a scam-awareness assistant. NPCI states AI fraud detection is a priority. SIM-binding claims come from secondary blogs — [IndianWeb2](https://www.indianweb2.com/2026/09/npci-unveils-myupi-conversational-ai.html); [Stockpil](https://stockpil.com/npci-ceo-ai-upi-digital-payments-growth)
- O2 "Daisy" AI granny (Nov 2024): talked to more than 1,000 scammers for up to 40–50 minutes. These are O2's own marketing figures, with no loss-reduction data — [Virgin Media O2](https://news.virginmediao2.co.uk/o2-unveils-daisy-the-ai-granny-wasting-scammers-time/); [Marketing Week](https://www.marketingweek.com/o2-ai-granny-scammers-public/)

### Inferences
- Liability shifts such as UK reimbursement have the clearest measured effect on losses. Name-matching (CoP/VoP) is necessary but structurally blind to a "family emergency" scam where the victim knowingly pays the account the scammer names.
- A family-verification step fits best at the bank's "scam conversation"/delay moment: the bank could prompt "verify with your enrolled family member" before releasing a first-time urgent payment. I found no bank doing this.

### Gaps
- No standalone quantified CoP effectiveness figure. Fall 2025 Australian data broken out by measure (CoP versus delays) was not found.
- Not checked: UK and Australian telco call-blocking statistics (Ofcom/ACMA), Singapore's Shared Responsibility Framework and ScamShield outcomes, primary NPCI circulars, and FTC Consumer Sentinel 2025 family-impersonation figures.

## Q5. What remains unsolved

### Takeaway
After all these measures, the residual gap is an authorised payment under emotional pressure from a caller claiming a relationship, especially from a new or unknown number, on iOS or cross-platform messaging, and across banks, telcos and platforms. No one ties identity proof to the payment moment.

### Cited Findings
- Google's handshake requires both parties on Phone by Google with RCS, and its behaviour when the contact's device is offline is undocumented — [Google blog](https://blog.google/security/android-fake-call-detection/)
- VoP and CoP do not address social-engineering fraud — [Trustpair](https://trustpair.com/blog/verification-of-payee/)
- Australian losses rose 7.8% in 2025 despite the Accord — [NASC](https://www.nasc.gov.au/system/files/targeting-scams-report-2025.pdf)
- Detection degrades under compression, codecs and adversarial attacks — [ASVspoof 5](https://arxiv.org/abs/2601.03944)
- People cannot reliably tell cloned voices from real ones, and compliance in cloned-relative scenarios reached 36% (self-reported) — [arXiv 2607.09970](https://arxiv.org/html/2607.09970v1)

### Inferences
- Verdict on the proposed idea: it is already solved at the concept level (Rooky; Google for spoofed known numbers; safe words as a zero-tech baseline), so it is not novel as a standalone consumer app. It is likely better delivered as (a) a bank- or telco-integrated step at payment time, (b) an open cross-platform protocol extending Google's RCS handshake to iOS and messaging apps, or (c) a combined "safe word + callback + enrolled-device confirm" flow that handles the "relative unreachable" case gracefully.
- Measurable differentiators a student project could still show: confirmation latency, the share of verify requests answered within N minutes (reachability), and false-block rate on real emergencies.

### Gaps
- No public evidence on reachability rates or user drop-off for any two-sided verify app.
- Not verified whether Apple has shipped an equivalent caller-verification feature as of Oct 2026.
