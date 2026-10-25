"""External-author check workflow, exercised on a FAKE file shaped like the dataset (invented messages only).

The real dataset is never downloaded by the tests.
"""

import csv
import json
import subprocess
from datetime import date
from pathlib import Path

import pytest

import scamcheck.eval.external as ext
from scamcheck.cli import main

ROOT = Path(__file__).parents[1]
TODAY = date(2026, 10, 26)
HI_SCAM = ["Aapka khata aaj band ho jayega, turant KYC update karein: hxxps://kyc-fake[.]xyz",
           "Aapko lottery mili hai, paisa paane ke liye UPI PIN daaliye abhi",
           "Beta mera phone kharab hai, jaldi paise bhejo is number par",
           "Aapka loan approve ho gaya hai, processing fee Rs 999 bhejo turant",
           "Bijli ka connection aaj raat kat jayega, abhi call kijiye",
           "आपका खाता बंद हो जाएगा, OTP बताइए"]
HI_LEGIT = ["Bhai kal match dekhne chalega kya? Main ghar par hoon",
            "Mummy main hostel pahunch gaya, shaam ko call karta hoon aur khana kha liya",
            "Aapka order kal tak pahunch jayega, dhanyavaad",
            "Yaar notes bhej de please, kal class mein nahi tha"]
EN = [("Ok see you at the station later", 0), ("Free entry to win a prize! Text WIN now", 1),
      ("Call 07700900123 to claim your reward", 1), ("Sorry, I'll call later lah", 0), ("Hai, what time tmr?", 0)]
ALL_TEXTS = HI_SCAM + HI_LEGIT + [t for t, _ in EN]


@pytest.fixture
def setup(tmp_path, monkeypatch):
    rows = [{"text": t, "label": lab} for t, lab in EN[:3]] + [{"text": t, "label": 1} for t in HI_SCAM] + \
           [{"text": t, "label": lab} for t, lab in EN[3:]] + [{"text": t, "label": 0} for t in HI_LEGIT]
    raw = tmp_path / "data.json"
    raw.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    monkeypatch.setattr(ext, "EXPECTED", {"scam": len(HI_SCAM), "legitimate": len(HI_LEGIT)})
    paths = {"raw": raw, "plan": tmp_path / "plan.json", "out": tmp_path / "out", "log": tmp_path / "log.md",
             "register": register(tmp_path / "reg.csv", verified=True)}
    paths["log"].write_text("", encoding="utf-8")
    return paths


def register(path, verified):
    with open(ROOT / "data/source_register.csv", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if r["source_id"] == ext.SOURCE_ID and verified:
            r["licence_verified_by"] = "Test Person"
            r["status"] = ext.REGISTER_STATUS + ": test only"
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return path


def plan(p):
    return ext.write_plan(p["raw"], ROOT, p["register"], p["plan"], p["log"], TODAY)


def run(p):
    return ext.run_check(p["raw"], ROOT, p["register"], p["plan"], p["out"], p["log"], TODAY)


def written(p):
    return "".join(f.read_text(encoding="utf-8") for f in [p["plan"], p["log"], *p["out"].glob("*")] if f.exists())


@pytest.mark.parametrize("text,expected", [
    ("Aaj party hai kya?", True), ("आपका खाता", True), ("Hai, what time tmr?", False),
    ("I am at home, see you soon", False), ("Ok lah, ka ki ko se", False),
])
def test_selection_rule(text, expected):
    assert ext.is_hinglish(text) is expected


def test_real_register_is_not_authorised_by_this_change():
    with pytest.raises(ext.ExternalCheckError, match=ext.REGISTER_STATUS):
        ext.check_register(ROOT / "data/source_register.csv")


def test_plan_requires_licence_verification(setup, tmp_path):
    setup["register"] = register(tmp_path / "unverified.csv", verified=False)
    with pytest.raises(ext.ExternalCheckError, match="licence_verified_by"):
        plan(setup)
    assert not setup["plan"].exists()


def test_count_mismatch_stops_the_plan_without_printing_text(setup, monkeypatch):
    monkeypatch.setattr(ext, "EXPECTED", {"scam": 35, "legitimate": 28})
    with pytest.raises(ext.ExternalCheckError) as e:
        plan(setup)
    assert "{'scam': 6, 'legitimate': 4}" in str(e.value) and not any(t in str(e.value) for t in ALL_TEXTS)


def test_plan_freezes_selection_and_code_and_logs_it(setup):
    p = plan(setup)
    assert p["selection"]["counts"] == {"scam": 6, "legitimate": 4}
    assert p["selection"]["rows"] == [3, 4, 5, 6, 7, 8, 11, 12, 13, 14]       # only the Hinglish rows
    assert p["frozen"]["sha256"] == ext.freeze_hash(ROOT) and p["dataset"]["revision"] == ext.REVISION
    assert p["authorisation"]["licence_verified_by"] == "Test Person"
    assert "PLANNED" in setup["log"].read_text(encoding="utf-8")
    assert not any(t in written(setup) for t in ALL_TEXTS)
    with pytest.raises(ext.ExternalCheckError, match="written once"):
        plan(setup)


def test_run_refuses_until_the_plan_is_committed(setup, monkeypatch):
    plan(setup)
    monkeypatch.setattr(ext, "plan_committed", lambda root, path: False)
    with pytest.raises(ext.ExternalCheckError, match="not committed"):
        run(setup)


def test_run_once_writes_results_without_text_and_refuses_a_second_run(setup, monkeypatch):
    plan(setup)
    monkeypatch.setattr(ext, "plan_committed", lambda root, path: True)
    res = run(setup)
    b4 = res["systems"]["B4-engine"]["metrics"]["overall"]
    assert b4["scam_recall"]["n"] == 6 and b4["false_alarm_rate_legitimate"]["n"] == 4
    assert b4["dangerous_miss_rate"]["k"] == 0                   # rule-only B4 never reassures
    assert set(res["systems"]) == set(ext.SYSTEMS)
    assert all(set(e) == {"row", "label", "verdict", "signals"} for e in res["b4_errors"])
    assert not any(t in written(setup) for t in ALL_TEXTS)
    assert "**RUN** once" in setup["log"].read_text(encoding="utf-8")
    with pytest.raises(ext.ExternalCheckError, match="already run once"):
        run(setup)


@pytest.mark.parametrize("tamper,match", [
    ("data", "data file differs"), ("code", "frozen code or training data changed"), ("register", "not authorised"),
])
def test_run_refuses_when_anything_frozen_changed(setup, monkeypatch, tmp_path, tamper, match):
    plan(setup)
    monkeypatch.setattr(ext, "plan_committed", lambda root, path: True)
    if tamper == "data":
        setup["raw"].write_text(setup["raw"].read_text(encoding="utf-8").replace("Bhai", "Bhaiya"), encoding="utf-8")
    elif tamper == "code":
        monkeypatch.setattr(ext, "freeze_hash", lambda root: "0" * 64)
    else:
        setup["register"] = register(tmp_path / "revoked.csv", verified=False)
    with pytest.raises(ext.ExternalCheckError, match=match):
        run(setup)
    assert not (setup["out"] / "results.json").exists()


def test_near_duplicates_share_a_campaign():
    g = ext.campaigns(["Aapka khata aaj band ho jayega turant call karein",
                       "Aapka khata aaj band ho jayega turant call kijiye", "Bhai kal milte hain"])
    assert g[0] == g[1] != g[2]


def test_plan_committed_uses_git(tmp_path):
    def git(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.email", "t@example.invalid")
    git("config", "user.name", "t")
    p = tmp_path / "plan.json"
    p.write_text("{}", encoding="utf-8")
    assert not ext.plan_committed(tmp_path, p)                   # untracked
    git("add", "plan.json")
    git("commit", "-q", "-m", "plan")
    assert ext.plan_committed(tmp_path, p)
    p.write_text('{"x": 1}', encoding="utf-8")
    assert not ext.plan_committed(tmp_path, p)                   # changed after commit


def test_cli_stops_with_a_reason_against_the_real_register(setup, capsys):
    assert main(["external-plan", "--raw", str(setup["raw"]), "--plan", str(setup["plan"]),
                 "--log", str(setup["log"])]) == 2
    assert ext.REGISTER_STATUS in capsys.readouterr().err and not setup["plan"].exists()
