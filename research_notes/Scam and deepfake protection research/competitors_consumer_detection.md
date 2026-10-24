# Consumer scam, phishing and scam-message detection products: competitor landscape (as of 24 Oct 2026)

Method note: about 16 search/fetch calls. Many sources are secondary (tech press, vendor-run comparison pages). Vendor numbers are labelled as claims. Products I could not verify in this pass are listed under Gaps and are not described as fact.

## Q1. Which products already do "forward a suspicious message, screenshot or link and get a verdict plus explanation", and in which languages and channels?

### Takeaway
The on-demand "paste or forward and get a verdict" pattern is already common. Bitdefender Scamio (web, WhatsApp, Messenger, Discord; screenshots and QR codes; free), Norton Genie (free; also inside ChatGPT and Claude), McAfee, Trend Micro ScamCheck, Malwarebytes Scam Guard, Whoscall "Check", Singapore's ScamShield app and the volunteer bots Checkmate (Singapore, WhatsApp) and Cofacts (Taiwan, LINE) all offer it. The weak spots are replies that are mostly English-only, screenshot/OCR handling that often breaks, vague verdicts, and false positives.

### Cited Findings
**Bitdefender Scamio**
- Channels are web, WhatsApp, Facebook Messenger and Discord. The support page does not mention Telegram. — [Bitdefender support](https://www.bitdefender.com/consumer/support/answer/97320/)
- Inputs are a description of the scam, pasted text, links, QR codes, and pictures or screenshots of emails, texts or IMs. Voice is not mentioned. — [Bitdefender support](https://www.bitdefender.com/consumer/support/answer/97320/)
- It "understands input in any language" but "responds exclusively in English". — [Bitdefender support](https://www.bitdefender.com/consumer/support/answer/97320/)
- It is free but needs a Bitdefender account. — [Bitdefender support](https://www.bitdefender.com/consumer/support/answer/97320/); [Cautellus (competitor blog)](https://cautellus.com/blog/best-scam-checkers-2026)
- In KSL's test (Jan 2026) it "rarely gave a firm verdict" ("likely suspicious"). It called most scam submissions safe-looking, though it correctly cleared the legitimate messages. — [KSL Investigates](https://www.ksl.com/article/news/ksl-investigates/we-tested4popularscamdetection-apps-hereswhatactually-worked/51589869)
- Tom's Guide found Bitdefender's Scam Copilot thorough but slow, taking about 30 s per scam. — [Tom's Guide](https://www.tomsguide.com/computing/online-security/i-tried-3-ai-powered-scam-detectors-to-help-keep-me-safe-online-and-theres-a-clear-winner)

**Norton Genie (Gen Digital)**
- It is free and scans texts, emails, websites and social posts. In 2026 it was extended into Claude and ChatGPT. — [Malwarebytes comparison (vendor page)](https://www.malwarebytes.com/solutions/best-scam-detection-tools); [Cautellus](https://cautellus.com/blog/best-scam-checkers-2026)
- Gen Digital claims more than 90% scam-detection accuracy across about 1M Genie installs. This is a vendor claim. — [search summary of Cautellus/Malwarebytes pages](https://cautellus.com/blog/best-scam-checkers-2026)
- A roundup says it is available in the US, UK, Australia and New Zealand. — [eSecurity Planet](https://www.esecurityplanet.com/cybersecurity/best-ai-deepfake-detection-tools/)
- KSL found it was the only app that flagged the phishing email. It passed the safe-message test and asked follow-up questions on the vishing case, but uploads had to be retried several times because of app issues. — [KSL](https://www.ksl.com/article/news/ksl-investigates/we-tested4popularscamdetection-apps-hereswhatactually-worked/51589869)

**McAfee Scam Detector**
- It sends automatic alerts with optional on-demand checks, and is the only primarily automatic one of the four compared. Price is from $119.99/yr. — [Malwarebytes comparison (vendor page)](https://www.malwarebytes.com/solutions/best-scam-detection-tools)
- KSL rated it "most reliable overall", but it does not accept screenshots, so text has to be pasted. — [KSL](https://www.ksl.com/article/news/ksl-investigates/we-tested4popularscamdetection-apps-hereswhatactually-worked/51589869)

**Trend Micro ScamCheck**
- Official languages are English, Japanese, Mandarin, German and French. It accepts images and screenshots. Call lookup and caller ID are listed for the US, Canada, Japan, Italy and Taiwan. — [Trend Micro](https://www.trendmicro.com/en_us/forHome/products/trend-micro-scam-check.html); [App Store](https://apps.apple.com/us/app/-/id1566099565)
- In KSL's test it caught all vishing scripts but missed the phishing email. It flagged a legitimate Amazon order confirmation as a scam (a false positive), and its character limit cut off a long romance-scam text. — [KSL](https://www.ksl.com/article/news/ksl-investigates/we-tested4popularscamdetection-apps-hereswhatactually-worked/51589869)

**Malwarebytes Scam Guard**
- It does on-demand checks with AI responses on iPhone and Android. It is free, with paid plans from $59.99/yr. — [Malwarebytes](https://www.malwarebytes.com/solutions/best-scam-detection-tools)

**Whoscall (Gogolook, Taiwan; strong in Taiwan, HK, Japan, Thailand, Philippines)**
- "Check" accepts screenshots of WhatsApp, Facebook or WeChat messages and runs them through an AI model. Its Web Checker uses Gogolook data, Taiwan's Criminal Investigation Bureau database and ScamAdviser's database. — [Whoscall blog](https://whoscall.com/en/blog/articles/800-Is_it_a_scam_website_use_Whoscall_Web_Checker_to_check)
- Gogolook says it identified more than 6B unknown calls and SMS in 2025, about 480M of them scams (vendor claim). — [Yahoo Finance / Whoscall release](https://finance.yahoo.com/news/whoscall-releases-annual-report-hong-020000908.html)
- It won Google Play "Best App of 2025" (in its market). — [Gogolook newsroom](https://www.gogolook.com/newsroom/whoscall-wins-best-app-of-2025-on-google-play-a-major-milestone-following-its-major-app-revamp)
- It launched an anti-scam app in the Philippines. — [Manila Standard](https://manilastandard.net/business/314644382/gogolook-rolls-out-anti-scam-app-amid-rising-fraud-in-the-philippines.html)

**Government and NGO tools**
- Singapore ScamShield is a suite: an app that checks suspicious calls, websites and messages (SMS, Telegram, WhatsApp) and blocks or filters scam calls and SMS, the 1799 helpline, a website and WhatsApp alert channels. It is run by MHA, SPF, Open Government Products and NCPC. — [ScamShield](https://www.scamshield.gov.sg/about-scamshield/what-is-scamshield/); [CSA](https://www.csa.gov.sg/our-programmes/cybersecurity-outreach/cybersecurity-campaigns/stop-and-check-campaign/add-scamshield-and-anti-virus-apps/); [OGP report card](https://reports.open.gov.sg/scamshield)
- India Sanchar Saathi (Department of Telecommunications) checks IMEIs, blocks lost or stolen phones, and lets users flag suspected fraud communications. The flagging feature is called Chakshu. It is a reporting tool, not a verdict engine. — [Wikipedia](https://en.wikipedia.org/wiki/Sanchar_Saathi)
- Checkmate (Singapore) is a volunteer WhatsApp bot launched in March 2023. It verifies forwarded messages, images and videos using NLP/ML plus human "CheckMates" who vote. Current 2026 status is unconfirmed. — [Circular Connection blog](https://www.circularconnection.com/post/checkmate-singapore-s-new-whatsapp-bot-to-combat-misinformation)
- Cofacts (Taiwan, g0v civic tech) is a LINE chatbot. Users forward messages, volunteer editors reply, and repeat messages are answered from the database. In 2018 it auto-answered 35,180 of more than 46,000 messages in 3 months, with fewer than 12 active editors handling about 250 new messages a week. Its topics include scams and misinformation. 2026 status was not found. — [IJNet](https://ijnet.org/en/story/taiwanese-cofacts-fact-checks-information-line)

**Google (Circle to Search)**
- Circle to Search scam checking of on-screen text messages has existed since December 2025. — [Unite.AI](https://www.unite.ai/google-details-circle-to-search-scam-checks-for-android-text-messages/)

**Open-source and hobby projects** (many repos named "ScamShield", all demos, none with adoption evidence)
- One repo is a React + FastAPI + Gemini 2.5 Flash detector that takes pasted SMS/WhatsApp text or a screenshot and returns Scam/Suspicious/Safe in English, Tamil or Hindi. — [GitHub Sangeeth2004762/scam-shield](https://github.com/Sangeeth2004762/scam-shield)
- Another is a web app in English and Hindi that highlights manipulative words and includes a scam simulator. — [GitHub safamahek0309/scamShield](https://github.com/safamahek0309/scamShield)
- Another uses Gemma 4 vision for screenshots, URLs and phone intel. — [GitHub YTxFSGAMERz/ScamShield](https://github.com/YTxFSGAMERz/ScamShield)

### Inferences
- The forward-and-get-a-verdict format is commoditised. Free versions exist from Bitdefender, Gen, Google and governments. A new entrant cannot win on that format alone.
- Replies in local languages are a real gap. Scamio replies only in English, and ScamCheck covers 5 languages with no Indic, Southeast Asian (other than Mandarin) or African languages. The Indic support I found is in hobby repos only.
- Screenshot ingestion is unreliable in practice. In KSL's test it caused freezes and failures to read links in images, and McAfee does not accept screenshots at all.

### Gaps
- Malwarebytes Scam Guard: languages, screenshot support and countries were not found.
- Norton Genie: language list not found.
- Scamio: country availability is not stated. A Telegram channel is not confirmed (the brief listed Telegram, but the support page doesn't).
- Kaspersky, Avast (Gen), F-Secure, ScamAdviser app, Get Safe Online "Check a website", Which?, CheckPhish/Bolster, VirusTotal and urlscan were not researched in this pass. No citations were collected for them.
- Current (2026) status of Checkmate and Cofacts was not found.
- I found no reliable source on "Ask Silver"-style startup bots.

## Q2. Which handle voice notes or live calls, and how?

### Takeaway
Live-call scam detection that ships today is mostly Google's Pixel/Android Scam Detection (on-device) and Truecaller's AI Call Scanner (Android, paid). Apple's call screening asks unknown callers for a reason, but a human still decides; it does no AI scam judgement. Deepfake voice detection is mostly PC or browser-based (McAfee, Norton, Hiya extension) and tied to specific hardware. I found no product that analyses forwarded voice notes from WhatsApp or Telegram.

### Cited Findings
- Google says Scam Detection in Phone by Google and Google Messages flags more than 5M suspected scam calls and texts a month (vendor claim). — [Cyberpress](https://cyberpress.org/google-rolls-out-new-android-protections/)
- Oct 14 2026 Android update: a verified financial calls program against bank impersonation, apps can no longer silently enable call forwarding (an OTP-theft vector), and login and payment fields are masked during screen sharing in Chrome and WebView. — [Unite.AI](https://www.unite.ai/google-rolls-out-ai-scam-defenses-across-android-messages-and-calls/); [9to5Google](https://9to5google.com/2026/10/14/google-messages-enhanced-protection-mode/); [pk-sharma briefing](https://www.pk-sharma.com/briefing/google-android-scam-defences-messages-call-forwarding-screen-share-rollout)
- Apple iOS 26 "Ask Reason for Calling" has unknown callers state their name and reason. One review says it still needs a human to review the call and does not use Apple Intelligence to decide whether a call is spam. — [search summary of Tom's Guide/9to5Mac/Sinch](https://9to5mac.com/?p=1005384); [Sinch community](https://community.sinch.com/t5/SMS/iOS-26-New-Features-for-Messages-and-Calls/m-p/18774)
- Truecaller AI Call Scanner does real-time AI voice detection on calls. It launched on Android in the US and is rolling out to India and other markets, and needs Premium. One source names a similar feature "AI Verify" at $4/mo, so naming is inconsistent across sources. — [eSecurity Planet / roundups](https://www.esecurityplanet.com/cybersecurity/best-ai-deepfake-detection-tools/); [eyesift](https://www.eyesift.com/faq/ai-voice-detection-deepfake-audio-2026/)
- Hiya Deepfake Voice Detector is a free Chrome extension that checks voices in online content. Hiya's live-call tech is sold mainly to carriers and OEMs. — [Business Wire (Hiya)](https://www.businesswire.com/news/home/20240725061586/en); [diyai.io](https://diyai.io/ai-tools/ai-detection/best-ai-voice-detectors/)
- McAfee Deepfake Detector is a PC audio alert tool tied to Intel Core Ultra 200V PCs and select HP and Lenovo Copilot+ PCs. It is not a phone-call scanner. — [McAfee](https://www.mcafee.com/learn/ai-deepfake-detector/); [Business Wire](https://www.businesswire.com/news/home/20250103596300/en)
- Norton Deepfake Protection runs on-device on Windows PCs and analyses synthetic voices in video and audio. It is auto-enabled on AI PCs and on high-performance non-AI PCs. — [Norton support](https://support.norton.com/sp/en/us/home/current/solutions/v2025051222180272)
- In the KSL test, "vishing" was tested only as pasted text descriptions of calls, not audio. All four apps flagged that text. — [KSL](https://www.ksl.com/article/news/ksl-investigates/we-tested4popularscamdetection-apps-hereswhatactually-worked/51589869)

### Inferences
- Live-call protection depends on the platform. Google's is on Android phones and requires the device's own dialer. Truecaller has to sit in the call path on Android. Apple doesn't let third-party apps access call audio.
- No consumer product was found that analyses forwarded voice notes (WhatsApp/Telegram audio) for scam content or voice cloning. This looks like an open niche, but absence of evidence is not proof.

### Gaps
- Exact device and country list for Google's live call Scam Detection was not retrieved this pass. February 2026 coverage says it is on select devices such as Pixel 10 ([Jetstream](https://jetstream.blog/en/google-messages-scam-detection-expands-20-countries/)).
- Independent accuracy data for Truecaller, Hiya or McAfee deepfake detection was not found.
- RoboKiller, Nomorobo and Apple Live Voicemail were not researched in this pass.

## Q3. Where do they fail: languages, code-switching, new scam scripts, false positives, platform lock-in?

### Takeaway
The recurring failure modes are platform and hardware lock-in (Pixel 10/Galaxy S26-class devices for Gemini Nano, Copilot+ PCs for deepfake tools), language limits (English-only replies, 5-language lists), screenshot/OCR fragility, hedged or wrong verdicts, false positives on legitimate commerce messages, and blind spots for scams arriving from compromised known contacts. Google's newest and strongest mode sends chats to the cloud and is opt-in.

### Cited Findings
**Google Messages**
- Scam Detection started in the US, UK and Canada. In Feb 2026 it expanded to more than 20 countries with Arabic, French, German, Portuguese and Spanish support, on select devices such as Pixel 10. — [Jetstream](https://jetstream.blog/en/google-messages-scam-detection-expands-20-countries/)
- Gemini Nano on-device link checks are limited to Pixel 10+, the Galaxy S26 series, Z Flip 8/Fold 8 and "other select devices". — [tbreak](https://tbreak.com/google-messages-gemini-scam-detection/); [Malaysian Wireless](https://www.malaysianwireless.com/2026/10/google-messages-gemini-ai-scam-protection/)
- Oct 2026 "Enhanced protection" is opt-in. It sends unknown-sender chats to cloud Gemini via Private AI Compute, and rollout is "in the coming weeks" with no country list. — [9to5Google](https://9to5google.com/2026/10/14/google-messages-enhanced-protection-mode/); [AndroidHeadlines](https://www.androidheadlines.com/2026/10/google-is-rolling-out-new-scam-protections-for-android-heres-whats-coming.html)
- Notification-based scam alerts are expanding to Motorola, OnePlus, Oppo, Xiaomi, Vivo and Realme. — [tbreak](https://tbreak.com/google-messages-gemini-scam-detection/)
- Google's headline detection figures come from a Google-commissioned evaluation, and one outlet urges caution. — [pk-sharma briefing](https://www.pk-sharma.com/briefing/google-android-scam-defences-messages-call-forwarding-screen-share-rollout); [Unite.AI](https://www.unite.ai/google-details-circle-to-search-scam-checks-for-android-text-messages/)
- Sources conflict on whether Gemini Nano powers text-pattern detection or only link checks. — [tbreak](https://tbreak.com/google-messages-gemini-scam-detection/) vs [PCQuest](https://www.pcquest.com/smartphones/android-scam-protection-gemini-nano-12689594)

**Apple**
- The iOS 26 Messages unknown-sender filter sends texts to separate lists with no notifications. A reviewer missed wanted messages under the strictest setup. Heise said the effectiveness of Apple's spam filter can't yet be judged. — [Tom's Guide](https://www.tomsguide.com/phones/iphones/how-to-screen-texts-from-unknown-senders-in-ios-26-messages); [heise](https://heise.de/-10479488)

**WhatsApp/Meta**
- Shipped features: alerts when you're added to unknown groups, plus a "Safety Overview" for assessing a group and exiting. — [Aura / search summary](https://www.aura.com/learn/whatsapp-scams); [Techweez](https://techweez.com/2026/06/26/whatsapp-stranger-chat-warning-feature/)
- Scam Alert test (Aug 2026, beta): checks messages from non-contacts on-device and warns rather than blocks. It does not cover compromised contacts, which carry some of the most effective scams. — [Malwarebytes blog (search snippet; fetch failed)](https://www.malwarebytes.com/blog/news/2026/08/whatsapp-is-testing-a-new-warning-for-scam-messages)
- A warning screen for unknown numbers was in beta on Android and iOS in June 2026 (WABetaInfo). — [Techweez](https://techweez.com/2026/06/26/whatsapp-stranger-chat-warning-feature/)
- Meta reports shutting down about 7M WhatsApp scam accounts (enforcement, not a user tool). — [Gulf News](https://gulfnews.com/technology/meta-shuts-down-nearly-7-million-whatsapp-accounts-in-major-scam-crackdown-1.500224125)
- India's SEBI warned on 22 Oct 2026 about invitation-only WhatsApp stock-tip groups run from overseas numbers. These are a live scam class that the existing group warnings have not stopped. — [BusinessToday](https://businesstoday.in/personal-finance/story/sebi-warns-investors-against-fake-stock-tips-on-invitation-only-whatsapp-groups-563162-2026-10-22)

**Microsoft Edge Scareware Blocker**
- It uses an on-device ML model. It exits full screen, mutes audio and warns the user. Microsoft says it is enabled by default on most Windows/Mac devices (Oct 2025), but a Feb 2026 guide says it isn't on by default, so the sources conflict. It started as a preview (BleepingComputer). — [Edge blog](https://blogs.windows.com/msedgedev/2025/10/31/protecting-more-edge-users-with-expanded-scareware-blocker-availability-and-real-time-protection/); [Microsoft support](https://support.microsoft.com/en-us/edge/prevent-online-scams-with-the-scareware-blocker-in-microsoft-edge); [BleepingComputer](https://www.bleepingcomputer.com/news/microsoft/microsoft-tests-edge-scareware-blocker-to-block-tech-support-scams/); [xentric](https://xentric.com/resources/blog/microsoft-edges-scareware-blocker-a-quiet-fix-for-a-loud-problem/)

**Chatbot checkers, cross-product**
- No app passed every smishing test. Pasted text worked better than screenshots, which caused freezes and links in images were missed. — [KSL](https://www.ksl.com/article/news/ksl-investigates/we-tested4popularscamdetection-apps-hereswhatactually-worked/51589869)
- Chatbot-style detectors such as Scamio and Genie are most useful as a "second opinion" on a scam already in progress (PCMag 2026, cited second-hand). — [Cautellus](https://cautellus.com/blog/best-scam-checkers-2026)
- Automatic scanners need more phone access, which raises privacy concerns. — [KSL](https://www.ksl.com/article/news/ksl-investigates/we-tested4popularscamdetection-apps-hereswhatactually-worked/51589869)

### Inferences
- Code-switching (Hinglish, Taglish, Singlish, Manglish), regional Indic and Southeast Asian scripts, and transliterated text have no documented support in any major product found. Combined with the English-only replies, this is the most defensible gap for an India or Southeast Asia focused entrant.
- Pull-based tools (you have to think to check) miss victims who are already emotionally committed. Push-based tools are tied to an OS or OEM.

### Gaps
- No vendor publishes false-positive rates for message scanning.
- No independent test of code-switched or non-English scam messages was found.

## Q4. What independent tests or reviews exist?

### Takeaway
Independent evidence is thin. AV-Comparatives runs anti-phishing URL tests and fake-shop tests for AV suites (the latest found is 2024), but I found no lab test of AI chat or message scam checkers or of on-device phone scam detection. The best comparative evidence is journalistic (KSL, Jan 2026; Tom's Guide). Academic benchmarks exist but evaluate LLMs, not shipped products.

### Cited Findings
- AV-Comparatives 2024 anti-phishing: 1,000 phishing URLs over four quarterly tests. Avast and McAfee reached 95% detection, with McAfee showing more false alarms. — [PR Newswire](https://prnewswire.co.uk/news-releases/av-comparatives-announces-2024-phishing-test-results-avast-and-mcafee-excel-in-yearly-assessment-302318894.html)
- AV-Comparatives Fake-Shops Detection Test 2024: not all products detect fake shops. — [MalwareTips](https://malwaretips.com/threads/fake-shops-detection-test-2024.132344/)
- KSL Investigates (30 Jan 2026) tested McAfee, Trend Micro, Norton Genie and Scamio with an IT consultant, covering phishing, vishing-as-text, smishing (text plus screenshots), romance scams and legitimate controls. No app scored perfectly. — [KSL](https://www.ksl.com/article/news/ksl-investigates/we-tested4popularscamdetection-apps-hereswhatactually-worked/51589869)
- Academic work: Fraud-R1 (8,564 cases, 15 LLMs) found a substantial gap between Chinese and English performance. — [arXiv 2502.12904](https://arxiv.org/pdf/2502.12904)
- FraudSMSWalker covers 699 bilingual SMS-to-webpage chains. — [arXiv 2606.16659](https://arxiv.org/abs/2606.16659v1)
- ConScamBench-278 covers multi-turn conversational scams across 8 families. — [arXiv 2607.11707](https://arxiv.org/html/2607.11707v1)
- LLM phishing email detection, including multilingual attacks. — [arXiv 2512.10104](https://arxiv.org/html/2512.10104v2)
- SoK on LLM-generated phishing. — [arXiv 2508.21457](https://arxiv.org/html/2508.21457v1)

### Inferences
- Publishing a transparent, multilingual, code-switched benchmark is an open opportunity, and a credible differentiator for anyone building in this space.

### Gaps
- AV-Comparatives and AV-TEST results for 2025-2026 scam or phishing were not found by search. Check av-comparatives.org directly.
- No independent evaluation of Google's Scam Detection, Truecaller AI Call Scanner, Apple filters or WhatsApp Scam Alert was found.

## Q5. What remains genuinely unsolved?

### Takeaway
Based on the evidence above, these are the open problems: (1) local-language and code-switched analysis with explanations in the user's own language; (2) voice notes and live calls on iPhone, and on the many Android phones without Gemini Nano; (3) scams that come from compromised known contacts or that run as long-con groups (investment, romance), where unknown-sender heuristics fail; (4) reliable screenshot handling; (5) independent, published accuracy and false-positive measurement; (6) closing the loop from a verdict to action (reporting to the 1930 helpline, Chakshu or ScamShield; bank freeze).

### Cited Findings
- Scamio replies only in English. — [Bitdefender](https://www.bitdefender.com/consumer/support/answer/97320/)
- Trend Micro ScamCheck supports only 5 languages. — [Trend Micro](https://www.trendmicro.com/en_us/forHome/products/trend-micro-scam-check.html)
- Gemini Nano features require flagship devices. — [tbreak](https://tbreak.com/google-messages-gemini-scam-detection/)
- WhatsApp Scam Alert misses compromised contacts and is still in testing. — [Malwarebytes](https://www.malwarebytes.com/blog/news/2026/08/whatsapp-is-testing-a-new-warning-for-scam-messages)
- Apple's call screening has no AI scam judgement. — [9to5Mac](https://9to5mac.com/?p=1005384)
- Screenshot failures in chatbot checkers. — [KSL](https://www.ksl.com/article/news/ksl-investigates/we-tested4popularscamdetection-apps-hereswhatactually-worked/51589869)
- Investment-group scams persist on WhatsApp in India (SEBI warning, Oct 2026). — [BusinessToday](https://businesstoday.in/personal-finance/story/sebi-warns-investors-against-fake-stock-tips-on-invitation-only-whatsapp-groups-563162-2026-10-22)
- The Chinese-English gap in LLM fraud robustness. — [Fraud-R1](https://arxiv.org/pdf/2502.12904)
- Cofacts-style human-in-the-loop bots hit editor-capacity limits (fewer than 12 editors for about 250 new messages a week in 2018). — [IJNet](https://ijnet.org/en/story/taiwanese-cofacts-fact-checks-information-line)

### Inferences
- A WhatsApp-native bot that is device-agnostic, handles Indic and code-switched text, screenshots and voice notes, and replies in the user's language with a clear verdict, a reason and the next step (with a link to Chakshu or 1930) does not appear to exist as a mature product, based on the products checked. This is an inference from the searches above; incumbents could ship it quickly.

### Gaps
- I did not verify Truecaller's or Whoscall's newest 2026 features in India or Southeast Asia, Kaspersky or F-Secure scam tools, Brazil's government tools, UK 7726, or Australia's Scamwatch / NASC tools. All need a follow-up pass before the matrix is final.
