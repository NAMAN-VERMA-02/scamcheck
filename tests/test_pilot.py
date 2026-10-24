import hashlib
import json

import pytest

from scamcheck.cli import main
from scamcheck.data.io import load_items, write_items
from scamcheck.data.pilot import (apply_adjudication, export_sheet, import_sheet, pseudo_id, read_csv, resolve,
                                  write_csv, ADJ_COLUMNS, SHEET_COLUMNS)


@pytest.fixture
def fresh(items):
    """Fixture items with gold and annotations stripped, as they would arrive from intake."""
    return [it.model_copy(update={"gold": None, "annotations": []}) for it in items if it.adversarial is None]


def fill(rows, answers):
    for r in rows:
        if r["id"] in answers:
            r.update(answers[r["id"]])
    return rows


def test_sheet_is_blind_and_order_differs_per_annotator(fresh):
    a1, a2 = export_sheet(fresh, "A1"), export_sheet(fresh, "A2")
    assert all(r["label"] == r["category"] == r["evidence"] == "" for r in a1)
    assert sorted(r["id"] for r in a1) == sorted(r["id"] for r in a2)
    assert [r["id"] for r in a1] != [r["id"] for r in a2]


def test_import_resolve_adjudicate_round_trip(fresh):
    ans_a1 = {"fx-001": {"label": "scam", "category": "bank_kyc_impersonation", "confidence": "3",
                         "evidence": "account_block_threat: will be blocked today"},
              "fx-010": {"label": "legitimate", "category": "otp", "confidence": "3"}}
    ans_a2 = {"fx-001": {"label": "scam", "category": "bank_kyc_impersonation", "confidence": "2"},
              "fx-010": {"label": "scam", "category": "phishing_credential", "confidence": "1"}}
    items, err = import_sheet(fresh, fill(export_sheet(fresh, "A1"), ans_a1), "A1", "g1")
    assert err == []
    items, err = import_sheet(items, fill(export_sheet(items, "A2"), ans_a2), "A2", "g1")
    assert err == []
    assert "fx-001" not in {r["id"] for r in export_sheet(items, "A1")}  # nothing re-served to A1

    items, adj = resolve(items)
    by = {it.id: it for it in items}
    assert by["fx-001"].gold.label == "scam" and not by["fx-001"].gold.adjudicated
    assert by["fx-010"].gold is None and [r["id"] for r in adj] == ["fx-010"]

    adj[0].update(final_label="legitimate", final_category="otp", rationale="Standard OTP template, no link.")
    _, err = apply_adjudication(items, adj, "A1")
    assert err and "cannot adjudicate" in err[0]
    items, err = apply_adjudication(items, adj, "A3")
    assert err == []
    gold = {it.id: it for it in items}["fx-010"].gold
    assert gold.adjudicated and gold.rationale.startswith("[A3]")


@pytest.mark.parametrize("change, needle", [
    ({"text": "edited", "label": "scam", "category": "loan_app", "confidence": "3"}, "text was edited"),
    ({"label": "maybe"}, "label"),
    ({"label": "scam", "category": "otp", "confidence": "2"}, "not valid for label"),
    ({"label": "scam", "category": "other_scam", "confidence": "2", "evidence": "urgency: not in text"}, "not found"),
    ({"label": "scam", "category": "other_scam", "confidence": "9"}, "confidence"),
])
def test_bad_sheet_rows_are_rejected_all_or_nothing(fresh, change, needle):
    good = {"fx-004": {"label": "scam", "category": "upi_collect_refund", "confidence": "3"}}
    rows = fill(export_sheet(fresh, "A1"), {**good, "fx-020": change})
    items, err = import_sheet(fresh, rows, "A1", "g1")
    assert any(needle in e for e in err), err
    assert items == fresh  # the valid row was not applied either


def test_adjudication_requires_rationale(fresh):
    a = [{"id": "fx-014", "final_label": "promotional", "final_category": "marketing", "basis": "annotator_judgment",
          "rationale": ""}]
    one = [it.model_copy(update={"annotations": []}) for it in fresh]
    _, err = apply_adjudication(one, a, "A3")
    assert err and "rationale" in err[0]


def test_pseudo_id_is_stable_normalised_and_keyed():
    k = b"test-key"
    assert pseudo_id("PHONE", "+91 98765-43210", k) == pseudo_id("phone", "9876543210", k)
    assert pseudo_id("UPI", "Scam.Pay@YBL", k) == pseudo_id("UPI", "scam.pay@ybl", k)
    assert pseudo_id("PHONE", "9876543210", k) != pseudo_id("PHONE", "9876543210", b"other")
    assert pseudo_id("PHONE", "9876543210", k).startswith("PHONE_")


def test_cli_pilot_flow_writes_hash_chained_audit_log(fresh, tmp_path):
    data, log = tmp_path / "items.jsonl", tmp_path / "audit.jsonl"
    write_items(data, fresh)
    for ann in ("A1", "A2"):
        sheet = tmp_path / f"{ann}.csv"
        assert main(["pilot-sheet", str(data), "--annotator", ann, "--out", str(sheet), "--log", str(log)]) == 0
        rows = read_csv(sheet)
        assert list(rows[0]) == SHEET_COLUMNS
        fill(rows, {"fx-014": {"label": "promotional", "category": "marketing", "confidence": "3"}})
        write_csv(sheet, rows, SHEET_COLUMNS)
        assert main(["pilot-import", str(data), "--sheet", str(sheet), "--annotator", ann, "--guideline", "g1",
                     "--out", str(data), "--log", str(log)]) == 0
    adj = tmp_path / "adj.csv"
    assert main(["pilot-resolve", str(data), "--out", str(data), "--adjudication", str(adj), "--log", str(log)]) == 0
    assert read_csv(adj) == []
    gold = {it.id: it.gold for it in load_items(data).items}
    assert gold["fx-014"].label == "promotional"

    lines = log.read_text(encoding="utf-8").splitlines()
    assert [json.loads(l)["cmd"] for l in lines] == ["pilot-sheet", "pilot-import", "pilot-sheet", "pilot-import",
                                                    "pilot-resolve"]
    for prev, line in zip(lines, lines[1:]):
        assert json.loads(line)["prev"] == hashlib.sha256(prev.encode("utf-8")).hexdigest()
