"""Regenerate the SYNTHETIC benchmark fixture: `python benchmarks/synthetic/build.py`.

Every message below was hand-written by the maintainer who also wrote the rule pack. None is a real message;
brands such as "XYZ Bank" or "Example Store" and all domains are invented or used only as imitation targets.
Scores on this set demonstrate that the pipeline runs. They are optimistic by construction (same author for rules
and data) and are NOT real-world detection performance.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[1] / "src"))

from scamcheck.data.schema import refang_host  # noqa: E402
from scamcheck.engine.urls import registered_domain  # noqa: E402

PROV = {"source_type": "synthetic", "source_name": "scamcheck-synthetic-benchmark-v1", "licence": "CC0-1.0",
        "licence_verified": True, "collected_at": "2026-10-25"}
SYN = {"method": "handwritten", "generator": "scamcheck-maintainers"}
RED = {"version": "r1", "checked_by": "synthetic-author"}
_DEFANGED = re.compile(r"hxxps?://\S+|\S+\[\.\]\S+")

# (language, label, category, channel, text)
ROWS = [
    # ── English scams ──
    ("english", "scam", "bank_kyc_impersonation", "sms", "Dear customer, your HDFC netbanking will be suspended today. Update PAN at hxxps://hdfc-pan-update[.]xyz/login"),
    ("english", "scam", "bank_kyc_impersonation", "sms", "SBI: Your YONO account is blocked due to incomplete KYC. Click hxxp://sbi-yono-kyc[.]top to reactivate within 2 hours."),
    ("english", "scam", "bank_kyc_impersonation", "sms", "ICICI Alert: your debit card will be blocked tonight. Call our KYC desk on <PHONE> immediately."),
    ("english", "scam", "phishing_credential", "email", "Your Netflix payment failed. Update card details at hxxps://netflix-billing-help[.]com to avoid suspension."),
    ("english", "scam", "phishing_credential", "sms", "Income tax refund of Rs 15,490 approved. Submit your bank details at hxxps://incometax-refund[.]site/claim"),
    ("english", "scam", "govt_impersonation", "sms", "Traffic challan of Rs 500 pending for your vehicle. Pay now at hxxps://echallan-parivahan[.]top or licence will be suspended."),
    ("english", "scam", "govt_impersonation", "sms", "Dear consumer, your electricity connection will be disconnected tonight at 9:30 pm due to unpaid bill. Contact officer <PHONE>."),
    ("english", "scam", "govt_impersonation", "whatsapp", "Mumbai Police cyber crime department: an FIR has been filed against your Aadhaar for money laundering. Join the video call now or face arrest."),
    ("english", "scam", "govt_impersonation", "sms", "Customs department: a parcel in your name with illegal items is held. Pay clearance charges to avoid legal action. Call <PHONE>."),
    ("english", "scam", "delivery_scam", "sms", "India Post: your package could not be delivered due to incomplete address. Update at hxxps://indiapost-redelivery[.]buzz within 24 hrs."),
    ("english", "scam", "delivery_scam", "sms", "Your courier is on hold. Pay Rs 25 redelivery fee at hxxps://bit[.]ly/<CODE> to receive it today."),
    ("english", "scam", "upi_collect_refund", "sms", "You have received a cashback of Rs 2,000. Approve the request in your UPI app to receive the amount."),
    ("english", "scam", "upi_collect_refund", "sms", "Refund of Rs 1,499 initiated. Enter your UPI PIN on the next screen to get the refund credited."),
    ("english", "scam", "job_task_scam", "whatsapp", "Hiring part-time: earn Rs 3,000 daily by rating hotels online. No experience needed. WhatsApp <PHONE>."),
    ("english", "scam", "job_task_scam", "sms", "Congratulations, you are selected for a work-from-home job. Pay Rs 1,500 registration fee to start."),
    ("english", "scam", "investment_trading", "telegram", "Join our VIP trading group on Telegram. Guaranteed 40% profit every week. hxxps://t[.]me/<HANDLE>"),
    ("english", "scam", "investment_trading", "whatsapp", "Double your money in 30 days with our crypto plan. Limited slots, invest now."),
    ("english", "scam", "loan_app", "sms", "Pre-approved instant loan of Rs 2,00,000. Pay processing fee of Rs 2,999 to release the amount today."),
    ("english", "scam", "lottery_prize", "sms", "Congratulations! You have won Rs 25,00,000 in the KBC lucky draw. Pay GST charges of Rs 12,500 to claim your prize."),
    ("english", "scam", "lottery_prize", "sms", "You are the lucky winner of an iPhone 15 in our anniversary contest! Claim within 24 hours: hxxps://claim-gift-now[.]shop"),
    ("english", "scam", "other_scam", "whatsapp", "Hi mom, I lost my phone and this is my new number. Please send Rs 8,000 to <UPI> urgently, will explain later."),
    ("english", "scam", "other_scam", "sms", "This is Airtel customer care. To fix your SIM issue please install AnyDesk and share the 9-digit code."),
    ("english", "scam", "phishing_credential", "sms", "Your WhatsApp will be deactivated today. Verify your account at hxxps://whatsapp-verify-secure[.]com"),
    ("english", "scam", "phishing_credential", "sms", "Amazon: someone tried to login to your account. To cancel this, reply with the OTP sent to your phone."),
    ("english", "scam", "other_scam", "sms", "Hello, I am from the electricity board, your meter reading is pending. Kindly call back on <PHONE>."),
    ("english", "scam", "job_task_scam", "whatsapp", "Dear candidate, your profile is shortlisted for a data entry role. Salary Rs 45,000. Contact HR on WhatsApp <PHONE>."),
    # ── Hinglish scams ──
    ("hinglish", "scam", "bank_kyc_impersonation", "sms", "Aapka SBI account aaj raat band ho jayega. KYC update karne ke liye hxxps://sbi-kyc-online[.]xyz par click karein."),
    ("hinglish", "scam", "bank_kyc_impersonation", "sms", "Priya grahak, aapka PAN card link nahi hai, aapka account block ho jayega. Turant hxxp://pan-link-update[.]top par jaye."),
    ("hinglish", "scam", "bank_kyc_impersonation", "other", "HDFC se bol raha hoon, aapka card band hone wala hai. Card number aur CVV bata dijiye verify karne ke liye."),
    ("hinglish", "scam", "upi_collect_refund", "sms", "Aapke account mein Rs 10,000 cashback aaya hai. Paisa lene ke liye UPI PIN daaliye."),
    ("hinglish", "scam", "govt_impersonation", "sms", "Bijli vibhag: aapka bijli connection aaj raat 9 baje kaat diya jayega. Turant is number par call karein <PHONE>."),
    ("hinglish", "scam", "govt_impersonation", "sms", "Aapka e-challan pending hai. Rs 500 jama karo hxxps://parivahan-echallan[.]vip par, warna licence cancel."),
    ("hinglish", "scam", "govt_impersonation", "whatsapp", "Main Delhi Police se bol raha hoon. Aapke Aadhaar se drugs wala parcel pakda gaya hai, video call par aaiye warna giraftar honge."),
    ("hinglish", "scam", "delivery_scam", "sms", "Aapka parcel address galat hone se ruk gaya hai. Rs 30 dekar update karein: hxxps://bluedart-track[.]icu"),
    ("hinglish", "scam", "upi_collect_refund", "other", "Customer care se bol raha hoon, refund ke liye aapke phone par ek OTP aaya hoga, woh bata dijiye."),
    ("hinglish", "scam", "job_task_scam", "telegram", "Ghar baithe roz Rs 2,000 kamao! Bas YouTube videos like karo. Join karne ke liye Telegram par message karo."),
    ("hinglish", "scam", "job_task_scam", "whatsapp", "Part time job hai, har task par Rs 150 milega. Pehle Rs 500 joining fee bhejo, phir kaam shuru."),
    ("hinglish", "scam", "investment_trading", "whatsapp", "Hamare stock tips group se roz 10% munafa pakka. Abhi join karo VIP group mein."),
    ("hinglish", "scam", "investment_trading", "whatsapp", "Paisa double scheme: 1 lakh lagao, 60 din mein 2 lakh pao. Bilkul risk free."),
    ("hinglish", "scam", "loan_app", "sms", "Aapka Rs 3 lakh ka loan approve ho gaya hai. Processing charge Rs 2,499 abhi bhejo aur paisa turant account mein."),
    ("hinglish", "scam", "lottery_prize", "sms", "Badhai ho! Aapne KBC lottery mein 25 lakh jeete hain. Inaam paane ke liye Rs 15,000 tax jama karein."),
    ("hinglish", "scam", "lottery_prize", "sms", "Aapko Amazon ki taraf se free gift mila hai! Claim karne ke liye hxxps://amazon-gift-claim[.]shop kholo."),
    ("hinglish", "scam", "other_scam", "whatsapp", "Mummy, mera phone kharab ho gaya, yeh naya number hai. Urgent Rs 5,000 is UPI par bhej do <UPI>."),
    ("hinglish", "scam", "other_scam", "sms", "Jio KYC expire ho gaya hai, aapki SIM 24 ghante mein band ho jayegi. Turant AnyDesk app install karke call karein."),
    ("hinglish", "scam", "govt_impersonation", "sms", "Aapke bijli bill mein galti hai, refund ke liye yeh APK download karein: hxxps://bijli-refund[.]in/app.apk"),
    ("hinglish", "scam", "phishing_credential", "whatsapp", "Aapka WhatsApp account hack hone wala hai. Usse bachane ke liye jo 6 digit code aaya hai woh bhejo."),
    ("hinglish", "scam", "phishing_credential", "other", "Sir, aapka Flipkart order cancel ho gaya. Refund ke liye apna card number aur expiry date message karein."),
    ("hinglish", "scam", "other_scam", "sms", "Sarkari yojana: PM scheme ke tahat aapko Rs 6,000 milenge. Registration ke liye Rs 199 fee bharo."),
    ("hinglish", "scam", "bank_kyc_impersonation", "other", "Hello ji, main bank se bol raha hoon, aapke account mein kuch problem hai. Is number par call back kijiye."),
    ("hinglish", "scam", "bank_kyc_impersonation", "sms", "Aapka Paytm wallet aaj band ho jayega. KYC ke liye hxxps://paytm-kyc-verify[.]online par login karein."),
    ("hinglish", "scam", "phishing_credential", "sms", "Income tax vibhag: aapka refund Rs 12,800 approve hua hai. Bank details is link par bhariye hxxps://itr-refund-status[.]in"),
    ("hinglish", "scam", "job_task_scam", "whatsapp", "Aapka resume select hua hai, ghar se kaam karke Rs 30,000 mahina. Interview ke liye HR ko WhatsApp karein <PHONE>."),
    # ── English legitimate ──
    ("english", "legitimate", "bank_txn_alert", "sms", "Rs 1,250.00 debited from A/c XX4521 on 12-Oct-26 to VPA <UPI>. If not done by you, call 1800 123 4567. -XYZ Bank"),
    ("english", "legitimate", "bank_txn_alert", "sms", "INR 35,000 credited to your A/c XX7781 on 15-10-26 by NEFT. Avl bal INR 52,340. -XYZ Bank"),
    ("english", "legitimate", "bank_txn_alert", "sms", "Your XYZ Bank credit card XX9012 has been blocked as requested. A new card will be dispatched in 7 working days."),
    ("english", "legitimate", "bank_txn_alert", "sms", "Alert: Rs 499 spent on your XYZ Bank card XX3344 at NETFLIX on 20-Oct-26. Not you? Block card via the official app."),
    ("english", "legitimate", "otp", "sms", "<OTP> is your OTP to log in to XYZ Bank. Do not share it with anyone. Bank staff never ask for OTP."),
    ("english", "legitimate", "otp", "sms", "Your OTP for transaction of Rs 2,300 at Example Store is <OTP>. Valid for 5 minutes. Never share your OTP."),
    ("english", "legitimate", "otp", "sms", "Use OTP <OTP> to verify your mobile number on Example App. We will never call you to ask for this code."),
    ("english", "legitimate", "otp", "sms", "Your delivery OTP is <OTP>. Share it with the delivery agent only after you receive your package."),
    ("english", "legitimate", "payment_confirmation", "sms", "Payment of Rs 650 to Example Cafe successful. UPI Ref No <REF>. Thank you for using Example Pay."),
    ("english", "legitimate", "payment_confirmation", "sms", "You have paid Rs 1,999 for your electricity bill. Transaction ID <REF>. Receipt sent to your email."),
    ("english", "legitimate", "payment_confirmation", "sms", "Received Rs 300 from <NAME> via UPI. Ref <REF>."),
    ("english", "legitimate", "delivery_notification", "sms", "Your Example Shop order <REF> has been shipped and will arrive by Friday. Track it in the Example Shop app."),
    ("english", "legitimate", "delivery_notification", "sms", "Out for delivery: your package will arrive today between 2 pm and 6 pm. Our agent will call before arriving."),
    ("english", "legitimate", "delivery_notification", "sms", "Your parcel could not be delivered today as the address was locked. We will try again tomorrow."),
    ("english", "legitimate", "govt_notice", "sms", "Your Aadhaar was successfully updated. Download the updated e-Aadhaar from the official UIDAI portal."),
    ("english", "legitimate", "govt_notice", "sms", "e-Challan <REF> of Rs 500 issued for overspeeding. Pay at hxxps://echallan.parivahan.gov[.]in or at the nearest traffic court."),
    ("english", "legitimate", "govt_notice", "sms", "Cyber safety alert: Beware of digital arrest calls. Police never arrest anyone over video call. Report fraud at 1930."),
    ("english", "legitimate", "service_account", "sms", "Your plan of Rs 299 expires on 30-Oct-26. Recharge on the Example Telecom app to continue services."),
    ("english", "legitimate", "service_account", "sms", "Your electricity bill of Rs 1,430 for Sep is generated. Due date 05-Nov-26. Pay via the official app or website."),
    ("english", "legitimate", "service_account", "sms", "Your broadband service will be temporarily unavailable on 28 Oct from 2 am to 4 am for maintenance."),
    ("english", "legitimate", "personal", "whatsapp", "Hey, are we still on for dinner at 8? Let me know if you want me to book a table."),
    ("english", "legitimate", "personal", "whatsapp", "Mom, reached the hostel safely. Will call you after class."),
    ("english", "legitimate", "personal", "whatsapp", "Can you send me the notes from today's lecture? I missed the last 20 minutes."),
    ("english", "legitimate", "personal", "whatsapp", "Rahul, please transfer my share of the trip, Rs 1,200, whenever you can."),
    # ── Hinglish legitimate ──
    ("hinglish", "legitimate", "bank_txn_alert", "sms", "Aapke A/c XX4521 se Rs 750 debit hue, 12-10-26 ko <UPI> ko. Agar aapne nahi kiya to 1800 123 4567 par call karein. -XYZ Bank"),
    ("hinglish", "legitimate", "bank_txn_alert", "sms", "Aapke khate XX7781 mein Rs 20,000 jama hue. Bachat khata balance Rs 41,200. -XYZ Bank"),
    ("hinglish", "legitimate", "otp", "sms", "<OTP> aapka OTP hai XYZ Bank netbanking login ke liye. Ise kisi ke saath share na karein."),
    ("hinglish", "legitimate", "otp", "sms", "Aapka OTP <OTP> hai. Bank kabhi bhi call karke OTP nahi maangta. Kisi ko na batayein."),
    ("hinglish", "legitimate", "otp", "sms", "Delivery ke waqt OTP <OTP> delivery agent ko bataiye, sirf package milne ke baad."),
    ("hinglish", "legitimate", "payment_confirmation", "sms", "Rs 450 ka payment Example Store ko safal raha. UPI Ref <REF>. Dhanyavaad!"),
    ("hinglish", "legitimate", "payment_confirmation", "sms", "Aapne Rs 1,200 ka bijli bill bhar diya hai. Transaction ID <REF>."),
    ("hinglish", "legitimate", "payment_confirmation", "sms", "<NAME> ne aapko Rs 500 bheje hain UPI se. Ref <REF>."),
    ("hinglish", "legitimate", "delivery_notification", "sms", "Aapka Example Shop order kal tak pahunch jayega. Order app mein track kar sakte hain."),
    ("hinglish", "legitimate", "delivery_notification", "sms", "Aapka parcel aaj delivery ke liye nikal chuka hai. Delivery agent aane se pehle call karega."),
    ("hinglish", "legitimate", "govt_notice", "sms", "Aapka Aadhaar update safal raha. Naya e-Aadhaar official UIDAI portal se download karein."),
    ("hinglish", "legitimate", "govt_notice", "sms", "Saavdhan! Koi bhi bank ya police officer aapse OTP ya PIN nahi maangta. Fraud ki report 1930 par karein."),
    ("hinglish", "legitimate", "service_account", "sms", "Aapka Rs 299 ka plan 30-10-26 ko khatam ho raha hai. Example Telecom app se recharge karein."),
    ("hinglish", "legitimate", "service_account", "sms", "Aapka bijli bill Rs 1,430 ka ban gaya hai. Aakhri tareekh 05-11-26. Official app se bhugtan karein."),
    ("hinglish", "legitimate", "service_account", "sms", "Kal subah 10 se 12 baje tak maintenance ke kaaran bijli band rahegi. Asuvidha ke liye khed hai."),
    ("hinglish", "legitimate", "personal", "whatsapp", "Bhai kal match dekhne chal raha hai? Main 7 baje tak free ho jaunga."),
    ("hinglish", "legitimate", "personal", "whatsapp", "Mummy, main hostel pahunch gaya. Shaam ko call karta hoon."),
    ("hinglish", "legitimate", "personal", "whatsapp", "Yaar aaj ke lecture ke notes bhej de please, main late aaya tha."),
    ("hinglish", "legitimate", "personal", "whatsapp", "Trip ka hisaab: tera share Rs 1,200 hai, jab time mile tab bhej dena."),
    ("hinglish", "legitimate", "bank_txn_alert", "sms", "Aapke XYZ Bank credit card ka bill Rs 8,450 hai. Due date 10-11-26. Bhugtan official app se karein."),
    ("hinglish", "legitimate", "bank_txn_alert", "sms", "Aapka cheque number <REF> clear ho gaya hai. -XYZ Bank"),
    ("hinglish", "legitimate", "service_account", "sms", "Aapki gas cylinder booking confirm ho gayi hai. Booking no <REF>. Delivery 2 din mein."),
    ("hinglish", "legitimate", "service_account", "sms", "Aapka train ticket PNR <REF> confirm hai. Coach B2, seat 34. Yatra mangalmay ho."),
    ("hinglish", "legitimate", "govt_notice", "sms", "Aapka passport application jama ho gaya hai. Status official portal par dekh sakte hain."),
    # ── Promotional ──
    ("english", "promotional", "marketing", "sms", "Flat 40% off on winter wear this weekend at Example Store. T&C apply."),
    ("english", "promotional", "marketing", "sms", "Upgrade to the Example Telecom 5G plan and get 20 GB extra data. Recharge on the app."),
    ("english", "promotional", "marketing", "sms", "Get assured returns of 7.25% p.a. on XYZ Bank fixed deposits. Visit your nearest branch."),
    ("english", "promotional", "marketing", "sms", "Example Mart sale: buy 2 get 1 free on all groceries till Sunday. Visit hxxps://www.example-mart[.]com/sale"),
    ("hinglish", "promotional", "marketing", "sms", "Example Store par Diwali sale! Sabhi kapdon par 50% tak ki chhoot. Jaldi aaiye."),
    ("hinglish", "promotional", "marketing", "sms", "Naya Example phone sirf Rs 9,999 mein. Aaj hi Example app se order karein."),
    ("hinglish", "promotional", "marketing", "sms", "XYZ Bank personal loan ab sirf 10.5% byaaj par. Apply karne ke liye nearest branch aayein."),
    ("hinglish", "promotional", "marketing", "sms", "Example Cinema: is weekend 1 ticket ke saath 1 free. Booking app par karein."),
    # ── Ambiguous: the text alone cannot decide ──
    ("english", "ambiguous", None, "whatsapp", "Hi, is this still your number? I have the documents you asked for."),
    ("hinglish", "ambiguous", None, "whatsapp", "Bhai mere dost ka emergency hai, abhi Rs 2,000 bhej sakte ho kya? Kal lauta dunga."),
    ("english", "ambiguous", None, "sms", "Your package is waiting. Reply YES to confirm your delivery slot."),
    ("english", "ambiguous", None, "whatsapp", "Hello, I got your number from a group. Are you interested in a part-time opportunity?"),
    ("hinglish", "ambiguous", None, "sms", "Aapka KYC pending hai, kripya nazdeeki branch mein jaakar complete karein."),
    ("hinglish", "ambiguous", None, "sms", "Sir, aapka number lucky customer list mein aaya hai. Details ke liye call karein."),
]


def urls(text: str) -> list[dict]:
    out = []
    for m in _DEFANGED.finditer(text):
        raw = m.group().rstrip(".,;:!?)")
        out.append({"raw": raw, "registered_domain": registered_domain(refang_host(raw))})
    return out


def build() -> list[dict]:
    items = []
    for n, (lang, label, cat, channel, text) in enumerate(ROWS, start=1):
        gold = {"label": label, "basis": "annotator_judgment"}
        if cat:
            gold["category"] = cat
        items.append({"id": f"sy-{n:04d}", "text": text, "channel": channel, "language": lang, "script": "latin",
                      "urls": urls(text), "gold": gold, "provenance": PROV, "synthetic": SYN, "redaction": RED})
    return items


if __name__ == "__main__":
    rows = build()
    with open(HERE / "items.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} synthetic benchmark items → {HERE / 'items.jsonl'}")
