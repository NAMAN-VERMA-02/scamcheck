# Redaction checklist (second person, every row)

Compare each row of `intake.csv` with the raw message in `data/raw/`. Tick every line before you fill
`redaction_checked_by`. The automated check after this **cannot find names or addresses**; you are the safeguard.

- [ ] **Names.** Every person's name, in any script or spelling, is `<NAME>`, including the donor's and the sender's. Brand and bank names may stay.
- [ ] **Payee and payer names in UPI/IMPS messages.** `UPI/P2A/412345678901/RAVI KUMAR` → `UPI/P2A/412345678901/<NAME>`. Merchant names (`AMAZON`) may stay.
- [ ] **Numbers the automated check deliberately skips.** After `Order ID`, `Txn ID`, `AWB`, `Tracking`, `Invoice`, `Booking` or `PNR`, and 12-digit values in UPI/IMPS slots, confirm the number really is a transaction reference and not a mobile or Aadhaar number.
- [ ] **Phones.** Every phone number is `<PHONE>`, in any format: `+91`, a leading `0`, spaces, dots, landline, WhatsApp links, Devanagari digits.
- [ ] **Emails.** Every email address is `<EMAIL>`, including `name [at] gmail [dot] com` forms.
- [ ] **UPI IDs.** Every UPI ID is `<UPI>`, including ones built from a phone number (`98…@ybl`).
- [ ] **Account and card numbers.** Bank account numbers are `<ACCT>`; card numbers are `<CARD>`. Masked forms already printed by the sender (`XX1234`) may stay.
- [ ] **Codes.** OTPs, PINs, CVVs and verification codes are `<OTP>`.
- [ ] **ID numbers.** Aadhaar, PAN, passport, voter ID, driving licence and vehicle numbers are `<ID>`.
- [ ] **Addresses.** Addresses, PIN codes, landmarks and locations precise enough to find a person are `<ADDRESS>`.
- [ ] **Sender.** `sender_value` is blank, `<PHONE>`, `<EMAIL>`, a pseudo-id token, a public short code, or a DLT header.
- [ ] **URLs.**
  - Defanged (`hxxps`, `[.]`).
  - Query strings and path parts carry no phone, email, UPI ID, name or token belonging to a person.
- [ ] **Other free text.** `source_name` and any notes contain no identifiers.
- [ ] **Not a private conversation.** If the message is between people the donor knows, it doesn't belong in the pilot: remove the row.
- [ ] **File format.** Saved as **CSV UTF-8**, and Devanagari still displays correctly after re-opening.
