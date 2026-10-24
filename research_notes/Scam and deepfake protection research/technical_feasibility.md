# Technical feasibility, accuracy, cost and risk: multilingual scam-analysis assistant (as of Oct 2026, solo student builder)

Research note: about 17 tool calls (searches and fetches). Many figures come from search-result snippets and abstracts, not full papers. Those are marked "(snippet)" and should be checked before anyone quotes them as headline numbers. Items written from background knowledge and not checked in this session are marked "UNVERIFIED" and listed under Gaps.

## 1. LLM scam/phishing detection accuracy (incl. multilingual, code-switching, false positives)

### Takeaway
Published LLM results on curated phishing-email sets are high (about 80% to 99%). The evidence on real-world mobile-message scams is much weaker: a 2026 study of 175k real user-reported scams says off-the-shelf detectors are inconsistent and have high false-positive rates. No public benchmark exists for Hinglish or other code-mixed scam SMS, and no study measures false positives on legitimate bank, OTP or delivery messages. The builder would have to build that evaluation set.

### Cited Findings
- Lu, Medeiros, Butler, Traynor (arXiv 2605.16656, 15 May 2026) collected 175,430 user-reported mobile messaging scams from Reddit (Jun 2020 to Dec 2025) and evaluated "commercial and open-source off-the-shelf detection tools". Reply-based scams had the lowest detector performance. The abstract does not give accuracy or FP numbers. — [arXiv 2605.16656](https://arxiv.org/abs/2605.16656)
- A search snippet of the same paper says LLMs "do not perform consistently in detecting fraudulent messages, suffering from high FP rates, especially on reply-based scams" (snippet, not verified in full text). — [arXiv 2605.16656 PDF](https://arxiv.org/pdf/2605.16656)
- arXiv 2511.15165 (Nov 2025, an MLLM phishing benchmark): zero-shot Gemini 2.5 Pro reached about 99% on one phishing dataset, and results varied sharply with prompt language (snippet). — [arXiv 2511.15165](https://arxiv.org/pdf/2511.15165)
- arXiv 2511.21448 benchmarks LLMs on phishing, spam and legitimate email. Phishing detection is strong, but separating spam from legitimate mail is weaker (snippet). — [arXiv 2511.21448](https://arxiv.org/abs/2511.21448v1)
- arXiv 2507.07406: the lightweight model DeepSeek-R1-Distill-Qwen-14B scores above 80% accuracy on phishing detection within 17 GB VRAM (snippet; the dataset type is unclear). — [papers.cool 2507.07406](https://papers.cool/arxiv/2507.07406)
- arXiv 2512.10104 reports LLM phishing-email detection above 90% accuracy, but says these systems are exploitable by adversarial, prompt-injection and multilingual attacks (snippet). — [arXiv 2512.10104](https://www.arxiv.org/pdf/2512.10104)
- Smishing: the master's thesis "Smishlock Holmes" (NCI, 2025) reports 87.5% accuracy on a balanced subset of the Super SMS Dataset. It is a thesis, not peer-reviewed. — [NORMA NCI](https://norma.ncirl.ie/9367/)
- FraudSMSWalker (arXiv 2606.16659, 2026) benchmarks agentic LLMs that follow SMS links to the landing page for fraud detection. Its results were not retrieved. — [arXiv 2606.16659](https://arxiv.org/pdf/2606.16659)
- Code-mixed: a Murdoch University thesis (2026) covering Bengali, English, Romanised Bengali and code-mixed smishing reports that fine-tuned Gemma-3 reached 99.14% accuracy. It argues that promotional messages must be labelled separately from phishing, and says no existing corpus covers Bangla, English, Banglish and code-mixed SMS with fine-grained labels. — [Murdoch research portal](https://researchportal.murdoch.edu.au/esploro/outputs/graduate/A-Multilingual-Fine-Tuned-LLM-Framework-for/991005909771807891)
- Indirect evidence on code-mixing: a 2026 arXiv paper found a fine-tuned DistilBERT beat Llama 3.1, Mistral, Gemma 3 and Phi-4 on Hinglish sarcasm detection. The task is different, but it suggests small fine-tuned models can beat zero-shot LLMs on code-mixed classification. — [arXiv 2602.21933](https://arxiv.org/abs/2602.21933)
- MOZ-Smishing (AfricaNLP 2025) is a crowd-sourced dataset of mobile-money fraud SMS (Mozambique). It is a dataset paper with no LLM accuracy figures. — [ACL Anthology author page](https://aclanthology.org/people/saide-m-saide/unverified/)

### Inferences
- The 95 to 99% headline accuracies come from curated, mostly English email datasets. They should not be read as real-world accuracy on WhatsApp forwards in Hindi, Hinglish or Tagalog. The only large real-world study (2605.16656) points the other way.
- At scale, false positives on legitimate bank, OTP, delivery and government messages are the main product risk, because those messages share the vocabulary of scams (KYC, OTP, "account blocked", links). The builder should collect a legitimate-message set and report the FP rate per category.
- A plausible architecture: deterministic signals first (URL reputation, domain age, known-sender patterns), then a cheap LLM for explanation, with a three-way verdict (likely scam / unclear / likely fine).

### Gaps
- No published accuracy figures were found for LLM scam detection on Hinglish, Taglish, Tamil, Bengali-Hindi or other Indian-language WhatsApp forwards. Searches for a Hinglish scam SMS benchmark found none.
- No study was found that measures false positives on legitimate bank or OTP messages. The search "LLM scam detection false positives legitimate bank OTP" returned only advisories and a patent.
- No published latency figures specific to scam detection were found.
- Full-text numbers for 2605.16656, 2511.21448 and FraudSMSWalker were not retrieved.

## 2. Public, legally usable datasets and licences

### Takeaway
English SMS and phishing corpora exist, and some are permissively licensed. Indic and code-mixed scam data is nearly absent: the only Hinglish scam set found has 63 Hinglish examples. Licences for the deepfake-audio datasets (In-the-Wild, MLAAD) were not confirmed and must be checked before any commercial use.

### Cited Findings
- `bolewara/hinglish-scam-text-dataset` on Hugging Face: about 3,787 examples, English and Hinglish financial scams. The Hinglish portion is only 35 scam and 28 benign hand-written examples (KYC, UPI, OTP patterns). The English portion comes from the UCI SMS Spam Collection. — [Hugging Face](https://huggingface.co/bolewara/hinglish-scam-text-dataset)
- COMI-LINGUA: 376K expert-annotated Hindi-English code-mixed instances (language ID, NER, POS, MT tasks, not scam labels), CC-BY-4.0. Usable for Hinglish robustness work. — [arXiv 2503.21670](https://arxiv.org/html/2503.21670v3)
- Super SMS Dataset (used in the Smishlock Holmes thesis). Licence not checked. — [NORMA NCI](https://norma.ncirl.ie/9367/)
- Reddit-derived dataset of 175,430 scam messages (2605.16656). Release status and licence were not found in the abstract. — [arXiv 2605.16656](https://arxiv.org/abs/2605.16656)
- Audio deepfakes: the In-the-Wild dataset holds about 37.9 h of celebrity and politician audio and is published publicly. ASVspoof 2019-trained models saw EER rise by up to 1000% on it. — [Müller et al., arXiv 2203.16263](https://arxiv.org/html/2203.16263v4)
- Cross-dataset deepfake numbers: training on MLAAD gives 16.07% EER on In-the-Wild. The best models in other papers reach 1.7% to 3.19% EER on In-the-Wild versus 0.43% in-domain on ASVspoof2019 LA. Thresholds do not transfer across datasets. — [arXiv 2507.01750](https://arxiv.org/pdf/2507.01750); [arXiv 2404.13008](https://arxiv.org/pdf/2404.13008)
- The search for MLAAD and In-the-Wild licence terms returned none. — (failed search, see Gaps)

### Inferences
- An MVP can be trained and evaluated on English corpora. Any Indian-market claim requires a self-collected, consented Hinglish/Indic set, ideally from users who opt in to donating their forwards.
- Voice-deepfake detection in production is not a solo-builder feature. Out-of-domain EER of 3% to 16% on clean-ish audio will be worse on compressed WhatsApp voice notes (Opus codec), and per-dataset threshold drift makes a "this is AI voice" verdict unreliable.

### Gaps
- UNVERIFIED (background knowledge, not fetched): UCI SMS Spam Collection (5,574 messages) is listed under CC BY 4.0. The Nazario phishing corpus is freely downloadable with informal terms. PhishTank data is free with an API key, and OpenPhish's community feed is free with commercial feeds paid. ASVspoof 2019/2021 is distributed under an ODC-By-style licence via Edinburgh DataShare. The report writer should confirm each before citing.
- The MLAAD and In-the-Wild licences were not found.
- No public multilingual scam-conversation dataset covering Indian languages was found.

## 3. Adversarial robustness: prompt injection, evasion, poisoning

### Takeaway
Prompt injection against LLM phishing detectors is a documented, peer-reviewed attack (RAID 2026), and it works even on GPT-5-class models. LLM rewriting also evades classical detectors. A scam bot that feeds attacker-controlled forwarded text or page content straight into an LLM should assume it will be attacked.

### Cited Findings
- Koide, Nakano, Chiba, "Clouding the Mirror" (arXiv 2602.05484, v1 5 Feb 2026, v2 5 Oct 2026, accepted at RAID 2026): attackers embed hidden instructions in phishing sites that exploit the "perceptual asymmetry between LLMs and human users". State-of-the-art multimodal LLMs remain vulnerable in controlled settings and on real phishing sites. Their defence, InjectDefuser (prompt hardening, allowlist-grounded retrieval, output validation), reduces attack success. The abstract gives no ASR numbers. — [arXiv 2602.05484](https://arxiv.org/abs/2602.05484)
- Promptfoo's vulnerability DB summarises the same attack class (hidden instructions in HTML, CSS, URLs or images), listing GPT-5, Grok 4 Fast, Llama 4 Maverick and Gemma 3 27B as affected. — [promptfoo](https://promptfoo.dev/lm-security-db/vuln/invisible-prompt-phishing-evasion-4db6c531/)
- A WSU 2026 poster reports that LLM rewriting of phishing emails cut an NLP detector from 99.70% to 88.00% (11.70% flip rate). These are preliminary poster results. — [WSU poster](https://wpcdn.web.wsu.edu/wp-vcea/uploads/sites/3267/2026/06/poster-2026-Liu.pdf)
- arXiv 2512.10104 names prompt-injection and multilingual attacks as exploitable weaknesses of LLM phishing detectors. — [arXiv 2512.10104](https://www.arxiv.org/pdf/2512.10104)

### Inferences
- Mitigations within a student's reach: treat message content strictly as data (structured output schema, no tool use triggered by content), strip zero-width and hidden characters, OCR the image rather than trusting embedded text, and keep a rule-based or reputation layer that the LLM cannot override toward "safe".
- Translation into a low-resource language is a known evasion route, so a multilingual bot is more exposed than an English one.

### Gaps
- No published poisoning attack on crowdsourced scam-report databases was found in this session; this topic was not searched specifically, so it remains open.

## 4. Screenshots (OCR/vision) and voice notes (speech-to-text)

### Takeaway
Image understanding is cheap with small multimodal models: image input on Gemini 2.5 Flash-Lite is priced like text. Speech-to-text is the weak link for Indian phone audio. Even fine-tuned Whisper (IndicWhisper) has 26.8% WER on Hindi GramVaani telephone-style speech, and commercial ASR does worse on that benchmark.

### Cited Findings
- Vistaar benchmark (AI4Bharat, Interspeech 2023): IndicWhisper (Whisper fine-tuned on Vistaar data) has the lowest WER on 39 of 59 benchmarks. Its Hindi average is 13.6% WER. On Hindi GramVaani (closest to phone audio) it is 26.8% WER. Google STT averages 23.9 WER and Azure 20 across benchmarks; on GramVaani, Google gets 59.9 and Azure 42.3. — [arXiv 2305.15386](https://arxiv.org/pdf/2305.15386); [GitHub AI4Bharat/vistaar](https://github.com/AI4Bharat/vistaar)
- Vaani Benchmark V1.0 (Hindi, 2026): Whisper-large-v3 shows substantially higher WER on background-noise speech, and Chirp 3 performs best. The 34.1 figure seen in a snippet has no confirmed metric. — [arXiv 2606.21408](https://arxiv.org/pdf/2606.21408)
- Gemini 2.5 Flash-Lite: $0.10 per 1M input tokens for text, image and video; $0.40 per 1M output. Audio input was $0.50 per 1M at preview, and GA coverage says audio was cut by 40%, but the GA figure was not confirmed. — [SD Times](https://sdtimes.com/ai/gemini-2-5-pro-and-flash-are-generally-available-and-gemini-2-5-flash-lite-preview-is-announced/); [alternativeto](https://alternativeto.net/news/2025/7/google-gemini-2-5-flash-lite-launches-with-lower-pricing-and-1m-context-window)
- Telegram Bot API: bots can download files up to 20 MB (getFile), which covers voice notes and screenshots. — [Telegram Bot FAQ](https://core.telegram.org/bots/faq)

### Inferences
- Voice notes: expect roughly 15% to 30%+ WER on real Hindi or Hinglish phone-quality audio. Scam keywords (amounts, bank names, "OTP") may survive, but nuance will not. Present any verdict on voice content as low-confidence.
- A rough cost estimate from the cited prices, assuming Gemini docs' figure of about 258 tokens per image and 32 audio tokens per second (UNVERIFIED): a screenshot check costs about $0.0001 to $0.0002, and a 1-minute voice note about 1,920 tokens, or $0.001 at $0.50/M. Verify against the live pricing page.

### Gaps
- No published OCR accuracy for Indic-script WhatsApp screenshots by vision LLMs was found.
- No Whisper-large-v3 telephony WER for Hindi was found directly.
- Current OpenAI transcription per-minute prices were not fetched (background knowledge, UNVERIFIED: whisper-1 at $0.006/min, gpt-4o-mini-transcribe at about $0.003/min).

## 5. Safe URL analysis (Web Risk / Safe Browsing, VirusTotal, urlscan, WHOIS/RDAP, CT)

### Takeaway
VirusTotal's free API cannot legally power a public product: it is non-commercial and limited to 4 requests/min and 500/day. Google Web Risk is the commercial path, it forbids redistributing its results, and its Update API keeps user URLs local for privacy. The free Safe Browsing API's commercial terms were not confirmed in this session.

### Cited Findings
- VirusTotal Public API: 500 requests/day and 4 requests/min. It "must not be used in commercial products or services". Registering multiple accounts to get around the limits is forbidden. — [VirusTotal docs: Public vs Premium API](https://docs.virustotal.com/reference/public-vs-premium-api); [Wazuh docs quoting the terms](https://documentation.wazuh.com/current/user-manual/capabilities/virustotal-scan/)
- Files submitted to VirusTotal go into a corpus shared with AV partners. This matters for privacy if users' screenshots or files are forwarded (secondary source). — [issoh.co.jp](https://www.issoh.co.jp/tech/details/17462/)
- Google Web Risk: an enterprise product for checking URLs against unsafe lists (phishing, social engineering, malware), and the lists "may be incomplete or contain errors". The Lookup API sends URLs to Google. The Update API downloads hashed prefixes and checks locally, contacting Google only on a hash match. "The information returned by the Web Risk must not be redistributed." — [Web Risk overview](https://docs.cloud.google.com/web-risk/docs/overview)

### Inferences
- The prototype stack would be Web Risk (paid, commercial-OK) or Safe Browsing (if non-commercial terms fit), RDAP domain age, CT-log certificate first-seen date, and a homoglyph or brand-similarity check. Fetching a live URL with a headless browser should run in an isolated, disposable sandbox without user cookies, or be delegated to urlscan.io. Scam pages cloak and serve benign content to datacenter IPs, so a "clean" fetch is weak evidence.

### Gaps
- Web Risk pricing and free tier: the overview page did not include them. UNVERIFIED background: about the first 100k Lookup calls/month are free, then a per-1k charge. The Safe Browsing v4/v5 non-commercial-use clause is likewise UNVERIFIED (Google historically said Safe Browsing APIs are for non-commercial use and pointed commercial users to Web Risk).
- urlscan.io API quotas, RDAP and CT (crt.sh) rate limits, and headless-fetch sandbox incidents were not researched (budget).

## 6. Channel constraints (WhatsApp, Telegram, browser extension, Android, iOS)

### Takeaway
WhatsApp is now the riskiest channel. From 15 Jan 2026 Meta bars "AI providers" whose AI is the core product. A scam checker built around an LLM sits in a grey zone that Meta decides. Since 1 Oct 2026 the business also pays for service replies beyond 1,000 per month per number. Telegram is free and permissive, but has rate limits and a much smaller Indian user base for this use.

### Cited Findings
- WhatsApp Business API terms: a new "AI providers" section bars providers from distributing general-purpose assistants. It applied to new users from 15 Oct 2025 and to all users from 15 Jan 2026. Meta told TechCrunch that businesses using AI for customer service are unaffected, and Meta reserves the right to decide what counts as a primary use case. — [respond.io](https://respond.io/blog/whatsapp-general-purpose-chatbots-ban); [Gulf News](https://gulfnews.com/technology/no-more-chatgpt-and-perplexity-on-whatsapp-meta-bans-major-ai-chatbots-from-2026-1.500316016)
- The prohibition hinges on whether "the AI is the core product rather than a supporting feature". Allowed examples are structured tasks such as order confirmation, ticket triage and reminders. — [respond.io](https://respond.io/blog/whatsapp-general-purpose-chatbots-ban)
- WhatsApp pricing (official):
  - Per-message pricing since 1 Jul 2025. Only delivered business-to-user messages are charged, and user-to-business messages are free.
  - Service messages were free from 1 Nov 2024. From 1 Oct 2026 each business number gets 1,000 free service messages per month, and messages beyond that are charged.
  - Utility templates sent inside the customer-service window are charged from 1 Oct 2026.
  - A separate "AI Providers pricing policy" has applied since 16 Feb 2026 (updated 12 May 2026), and the 1 Oct 2026 service changes do not apply to AI providers.
  - Meta Business Agent messages cost $2.00 per 1M tokens, about 4 to 5 cents per message.
  - India rates are in the rate-card CSV, and India accounts must migrate to INR by 31 Dec 2026.
  — [Meta WhatsApp pricing docs](https://developers.facebook.com/docs/whatsapp/pricing)
- Telegram Bot API limits:
  - About 1 msg/s per chat and 20 msgs/min per group.
  - About 30 msgs/s for broadcast. Paid broadcasts go up to 1,000/s at 0.1 Stars per message and need 100k Stars plus 100k MAU.
  - File download limit is 20 MB and upload limit is 50 MB.
  — [Telegram Bot FAQ](https://core.telegram.org/bots/faq)
- Google already ships comparable features. Chrome 137 uses on-device Gemini Nano in Enhanced Protection to extract scam signals from pages, with Safe Browsing making the final call; it launched for tech-support scams. Scam Detection in Google Messages and Phone by Google (announced 4 Mar 2025) analyses conversational scams on-device. — [Infosecurity Magazine](https://www.infosecurity-magazine.com/news/google-ai-gemini-nano-scams-chrome/); [The Hacker News](https://thehackernews.com/2025/05/google-rolls-out-on-device-ai.html)

### Inferences
- A WhatsApp scam-check bot is defensible only if it is narrowly scoped: it accepts forwards, returns a verdict, and refuses open questions. Even then, Meta's discretion is an existential platform risk, and the AI-provider pricing policy may apply to it. Pricing exposure for a free service: users initiate every check, so replies are service messages, and after 1,000/month per number each one costs the per-message service rate (India rate not retrieved).
- Telegram is the safer MVP channel (free, no AI-provider clause found), but Indian scam victims are mostly on WhatsApp, so there is a distribution mismatch.
- Android's built-in Scam Detection and Chrome's Gemini Nano overlap with the concept. Differentiation would need to be multilingual explanation or WhatsApp-forward coverage.

### Gaps
- MV3 extension constraints (no remote code, service-worker lifetime, declarativeNetRequest rule caps), Android Accessibility and NotificationListener Play-policy restrictions, and iOS limits (no access to WhatsApp content; only the SMS-filter ILMessageFilterExtension) were not researched in this session for lack of budget. Background (UNVERIFIED): Google Play restricts AccessibilityService to genuine accessibility uses, and iOS apps cannot read other apps' messages, so share-sheet or forward-to-bot is the only route.
- India per-message WhatsApp service and utility rates were not retrieved (they are in the CSV rate card).
- No report was found of enforcement against narrow AI bots after 15 Jan 2026.

## 7. On-device vs cloud models

### Takeaway
Google itself splits the work: Gemini Nano extracts signals on-device and the server-side Safe Browsing makes the verdict. Small open models (14B distilled) reach about 80% on phishing, and small fine-tuned encoders may beat zero-shot LLMs on code-mixed text.

### Cited Findings
- Chrome 137 runs Gemini Nano on-device to extract page intent signals, which are sent to Safe Browsing for the final verdict. — [Infosecurity Magazine](https://www.infosecurity-magazine.com/news/google-ai-gemini-nano-scams-chrome/)
- DeepSeek-R1-Distill-Qwen-14B scores above 80% on phishing detection within 17 GB VRAM (snippet). — [papers.cool 2507.07406](https://papers.cool/arxiv/2507.07406)
- Fine-tuned DistilBERT beat Llama 3.1, Mistral, Gemma 3 and Phi-4 on Hinglish sarcasm (an analogous task). — [arXiv 2602.21933](https://arxiv.org/abs/2602.21933)
- Fine-tuned Gemma-3 reached 99.14% on code-mixed Bengali smishing (thesis). — [Murdoch](https://researchportal.murdoch.edu.au/esploro/outputs/graduate/A-Multilingual-Fine-Tuned-LLM-Framework-for/991005909771807891)

### Inferences
- A cheap tiered design: a fine-tuned multilingual encoder (MuRIL or XLM-R class) or small Gemma as the first-pass classifier on a CPU server or on-device, escalating to a cloud LLM only for "unclear" cases and explanations.

### Gaps
- No benchmarks were found for Phi or Qwen small models on scam SMS. The Chrome built-in AI (Prompt API) availability to third-party extensions in Oct 2026 was not checked.

## 8. Cost to serve a large free user base

### Takeaway
With text-only checks, LLM cost is small: about $0.03 to $0.10 per 1,000 checks on Flash-Lite-class models. Channel cost (WhatsApp per-message beyond 1,000 per month) and URL-reputation APIs are likely to dominate.

### Cited Findings
- Gemini 2.5 Flash-Lite: $0.10 per 1M input tokens (text, image, video) and $0.40 per 1M output tokens. — [SD Times](https://sdtimes.com/ai/gemini-2-5-pro-and-flash-are-generally-available-and-gemini-2-5-flash-lite-preview-is-announced/); [morphllm roundup 2026](https://www.morphllm.com/gemini-api-pricing)
- WhatsApp charges service messages beyond 1,000/month/number from 1 Oct 2026, and Meta's own Business Agent costs about 4 to 5 cents per message. — [Meta pricing](https://developers.facebook.com/docs/whatsapp/pricing)

### Inferences
- Worked estimate from the cited prices (an estimate, not a published number):
  - Text check: about 500 input tokens (system prompt plus message) and about 150 output tokens, giving $0.00005 + $0.00006, about $0.00011 per check, or about $0.11 per 1k checks.
  - Screenshot check: about $0.15 to $0.25 per 1k.
  - 1-minute voice note: about $1 per 1k at the $0.50/M preview audio price.
  - At 1M checks/month, text-only LLM cost is about $110/month before any free tier.

### Gaps
- Current GPT-4.1-nano, GPT-5-nano, Claude Haiku and Gemini 3 Flash-Lite prices as of Oct 2026 were not fetched. Use the live pricing pages.

## 9. Privacy and regulation (GDPR, India DPDP Act 2023 + 2025 Rules, third-party data, children)

### Takeaway
The DPDP Rules were notified on 14 Nov 2025, and most obligations (consent notices, security, retention, children's verifiable parental consent) apply from about 13 May 2027. A product launched in 2026 should design for them now. Forwarded messages contain third parties' personal data that those people never consented to share.

### Cited Findings
- MeitY notified the DPDP Rules 2025 on 14 Nov 2025 with a staggered rollout:
  - Rules 1, 2 and 17 to 21 took effect immediately.
  - Rule 4 (Consent Managers) applies after one year (about Nov 2026).
  - Rules 3, 5 to 16, 22 and 23 apply after 18 months (about 13 May 2027).
  — [Storyboard18](https://www.storyboard18.com/digital/breaking-govt-notifies-final-dpdp-rules-sets-staggered-rollout-with-key-obligations-for-data-fiduciaries-84201.htm); [BDO India](https://www.bdo.in/en-gb/news/2025/digital-personal-data-protection-rules-2025-%E2%80%94-check-provisions,-implementation-plan,-penalties); [Mondaq](https://www.mondaq.com/regulatory-update-notification-of-the-digital-personal-data-protection-rules-2025/1713500)
- Verifiable parental consent for children can rely on identity and age details the fiduciary already holds, details the individual volunteers, or virtual tokens. There are exemptions for essentials such as healthcare. — [EY India](https://www.ey.com/en_in/insights/cybersecurity/transforming-data-privacy-digital-personal-data-protection-rules-2025); [Mondaq](https://webiis08.mondaq.com/india/data-protection/1775140/from-draft-to-reality-key-changes-in-indias-dpdp-rules-2025)
- One source claimed the rules are "fully implemented", which conflicts with the official staggered timeline. Treat that claim as wrong. — [gracker.ai](https://gracker.ai/news/indias-digital-data-protection-rules-2025-key-insights-and-analysis)

### Inferences
- Practical design: process messages ephemerally, store only hashes of URLs and phone numbers for reputation, redact names, numbers and account IDs before any LLM call or log, and set a short retention period. Use providers' zero-retention or no-training API settings. Avoid sending user files to VirusTotal, whose corpus is shared. Gate users under 18, or design no-retention flows so children's data is not "processed" beyond the transient check.

### Gaps
- GDPR-specific analysis (the legitimate-interest basis for third-party data in forwards, Art. 8 child consent at age 13 to 16, Art. 22 automated decisions) was not researched in this session.
- No legal commentary was found on third-party personal data inside forwarded messages under DPDP; this was not searched.

## 10. How users respond to automated verdicts (trust, explanations, uncertainty)

### Takeaway
Explanations help. LLM-written warnings can match or beat expert-written ones, and explainable warnings teach users to spot phishing later. Counterfactual explanations reduce false-positive harm. No study was found that directly tests "we're not sure" uncertainty messaging in scam warnings.

### Cited Findings
- Cau et al. (arXiv 2507.07916, 2025), N=750 between-subjects:
  - Warnings explained by Claude 3.5 Sonnet or Llama 3.3 70B matched or beat manually written explanations at reducing phishing susceptibility, and Claude's were most robust.
  - Feature-based explanations worked better on true phishing, and counterfactual explanations lowered false-positive rates.
  - Workload, gender and prior familiarity moderated the effects. Llama 3.3 was rated clearer, but that did not translate into behaviour.
  — [arXiv 2507.07916](https://arxiv.org/html/2507.07916v2)
- PhishXplain (arXiv 2505.06836), N=150 Prolific: explainable warnings increased immediate compliance and improved later independent detection compared with generic Google Safe Browsing warnings. The largest gains were among users with low technical proficiency. — [arXiv 2505.06836](https://arxiv.org/pdf/2505.06836v1)
- Chen, Xiong, Li, Proctor (AHFE 2016): warning reliability shapes trust. Low reliability leads to disuse, and high trust risks automation bias (the "description-experience gap"). — [Chen et al. 2016](https://www.sos-vo.org/system/files/sos_files/Chen_et_al_2016_AHFEpdf.pdf)

### Inferences
- Product copy should name the specific red flags (feature-based) for "likely scam", and use counterfactual framing for "probably fine" ("this would be a scam if it asked for your OTP"). Every verdict should teach the user something, so they do not become dependent on the bot.
- Repeated false positives erode trust in true warnings, which ties back to the bank and OTP false-positive gap in section 1.

### Gaps
- No empirical study was found on calibrated uncertainty or "we're not sure" phrasing in scam or phishing warnings specifically (search returned only general XAI work and a design-science paper, IACIS 2026, with results not seen). — [IACIS 2026](https://iacis.org/iis/2026/2_iis_2026_685-706.pdf)
