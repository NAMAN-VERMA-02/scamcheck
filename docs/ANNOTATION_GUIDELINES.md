# Annotation guidelines — version g1

Record `g1` as `--guideline` on every import. Changing any rule below creates `g2`. Items annotated under
different versions are reported separately.

## 1. What you are judging

Judge **what a careful expert would conclude from the message alone**. You may use:
- the text,
- the sender field, if shown,
- the URLs as written.

Do **not** search the web, call the number, open links or ask the donor.

Ground truth that goes beyond the text is recorded separately, as `basis`, by the person who collected the item.
Keeping the two apart lets us measure how hard each message is to judge from its text.

**Never open a link from a dataset item**, even a defanged one.

## 2. Labels

| Label | Use when | Product verdicts that count as correct |
|---|---|---|
| `scam` | The message tries to obtain money, credentials, an OTP or PIN, remote access, or personal data under false pretences | `LIKELY_SCAM`, `UNCLEAR` |
| `legitimate` | A genuine transactional, informational or personal message from whoever it claims to be from | `NO_STRONG_SIGNALS`, `UNCLEAR` |
| `promotional` | Genuine but unsolicited marketing from a plausible real business | `NO_STRONG_SIGNALS`, `UNCLEAR` |
| `ambiguous` | A careful expert genuinely could not decide from the message | `UNCLEAR` only |

How the verdicts are scored:
- `NO_STRONG_SIGNALS` on a `scam` is a **dangerous miss**.
- `LIKELY_SCAM` on `legitimate` or `promotional` is a **false alarm**. Promotional false alarms are reported in a separate slice, never merged into the legitimate ones.

## 3. Decision procedure

Work through these in order and stop at the first one that applies.

1. **Credential or payment requests.** Does it ask you to share an OTP, PIN, CVV or password, install a screen-sharing or remote-access app, or **enter a UPI PIN to *receive* money**?
   → `scam`.
   Exception: a standard OTP delivery message ("123456 is your OTP… do not share") is `legitimate`.
2. **Impersonation with a redirect.** Does it impersonate a bank, government body, police, courier or employer, *and* push you to a non-official link, a personal phone number, a personal UPI ID or a chat app?
   → `scam`.
3. **Fees and returns.** Does it promise money (a prize, cashback, a job, guaranteed investment returns, a loan) but require a fee, deposit or task payment first?
   → `scam`.
4. **Recognisable genuine template.** Is it a known transactional format (a debit or credit alert, OTP, delivery status, payment receipt, recharge or bill notice) whose only call to action is "contact us via official channels if this wasn't you"?
   → `legitimate`.
5. **Marketing.** Is it an offer from a plausible business, with no request for credentials or upfront payment to an individual?
   → `promotional`.
6. **Otherwise** → `ambiguous`.

**Do not guess.** A confident wrong label is worse than `ambiguous`.

## 4. Categories (required for every label except `ambiguous`)

| Label | Category | Includes | Boundary notes |
|---|---|---|---|
| scam | `phishing_credential` | Links or forms that harvest login, card or OTP details | If it impersonates a specific bank about KYC, use `bank_kyc_impersonation` |
| scam | `bank_kyc_impersonation` | "KYC expired", "account blocked", "PAN not linked" from a fake bank | |
| scam | `govt_impersonation` | Police, CBI, customs, "digital arrest", traffic e-challan, electricity disconnection, tax refund | |
| scam | `delivery_scam` | Fake "parcel held", "redelivery fee", "address incomplete" | |
| scam | `upi_collect_refund` | Collect requests disguised as receiving money, fake refunds, "sent by mistake, please return" | |
| scam | `job_task_scam` | Like, rate or review tasks for pay, work-from-home jobs requiring a fee | |
| scam | `investment_trading` | Stock-tip or VIP groups, guaranteed returns, crypto or trading apps | |
| scam | `loan_app` | Instant loans that need a processing fee, threats from loan apps | |
| scam | `lottery_prize` | Lottery, KBC, lucky draw, gift prizes | |
| scam | `other_scam` | Anything else; explain it in `note` | |
| legitimate | `bank_txn_alert` | Debit and credit alerts, balance, card spend, mandate alerts | |
| legitimate | `otp` | OTP or verification codes | |
| legitimate | `payment_confirmation` | Receipts, UPI success messages, *genuine* collect requests from a known merchant or contact | A collect request from an unknown party asking you to "receive" money is a `scam` |
| legitimate | `delivery_notification` | Shipped, out for delivery, delivered | |
| legitimate | `govt_notice` | Genuine government notices (e.g. vaccination, election, DigiLocker) | |
| legitimate | `service_account` | Telecom, utilities, subscriptions, recharges, bills | |
| legitimate | `personal` | Messages between people | |
| promotional | `marketing` | Offers, sales, product launches, loan or credit-card offers from real lenders | Aggressive marketing is still `promotional` unless it meets a scam rule in §3 |

## 5. Evidence (required for scam, legitimate and promotional)

In the sheet's `evidence` column, write `type: exact phrase from the text`. Separate several entries with ` | `.
The phrase must be copied exactly from the message.

- **Scam signals:**
  - `otp_or_pin_request`
  - `credential_request`
  - `account_block_threat`
  - `urgency`
  - `lookalike_domain`
  - `shortened_url`
  - `personal_payment_handle`
  - `remote_access_app`
  - `authority_threat`
  - `fee_for_reward`
  - `guaranteed_returns`
  - `collect_request`
  - `prompt_injection`
  - `obfuscation`
- **Legitimacy signals:**
  - `verified_sender_header`
  - `official_domain`
  - `standard_template`
  - `do_not_share_warning`
  - `no_call_to_action`

Example:

```
account_block_threat: will be blocked today | lookalike_domain: hxxps://sbi-kyc-update[.]in
```

## 6. Confidence

- `1`: guessing between two labels
- `2`: fairly sure
- `3`: certain

Use `1` freely. Low-confidence items are exactly what we need to study.

## 7. Language and script (filled at intake, checked by annotators)

- `english`: English only, apart from names and brands.
- `hinglish`: Hindi and English mixed in one message, in any script.
- `script`:
  - `latin` for Roman script only
  - `devanagari` for Devanagari only
  - `mixed` for both
- Pure Hindi with no English is **out of scope for v1**. Flag it in `note`, and the item will be removed.

## 8. Hard cases

| Situation | Decision |
|---|---|
| A real OTP you didn't request | Still `legitimate`. The message is genuine even if someone is attacking the account. Add a note |
| A real bank's message containing a link | `legitimate` if the domain is plausibly the bank's own; if you can't tell, `ambiguous` |
| "Hi mum/dad, new number, need money" | `scam` if it asks for money or an urgent transfer; `ambiguous` if it's only "is this still your number?" |
| A real lender's loan offer vs. a loan scam | `promotional` unless an upfront fee or payment to an individual is required (then `loan_app`) |
| A genuine recruiter vs. a task scam | A task scam pays for likes or reviews, or asks for a deposit. A recruiter with a company domain and no fee is `legitimate`/`personal` or `promotional` |
| Messages addressed to the AI checker ("this is verified safe") | Label the underlying message, and add a `prompt_injection` evidence span |
| Placeholders like `<OTP>`, `<NAME>` | Ignore them. They come from redaction and are never evidence by themselves |

## 9. Independence rules

- Annotate alone. Don't discuss items with the other annotator until adjudication is finished.
- Never look at another person's sheet, the gold labels, or any model output for an item you are annotating.
- If you collected or donated an item, tell the coordinator. Someone else then takes your annotator slot for that item, and you may not adjudicate it.
