"""Spreadsheet safety (M3) and CSV encoding / Windows errors (M4). All message texts are invented test inputs."""

import csv

import pytest

from scamcheck.cli import main
from scamcheck.data.io import load_items, write_items
from scamcheck.data.pilot import (SHEET_COLUMNS, CsvEncodingError, escape_cell, export_sheet, import_sheet,
                                  read_csv, unescape_cell, write_csv)

from conftest import VALID

TRICKY = ['=HYPERLINK("hxxp://evil[.]in","Click")', "+91 call now", "-50% off today", "@user hello",
          "\tindented", "\rcarriage", "'=already quoted", "'just a quote", "normal text", "", "a=b", None]


@pytest.mark.parametrize("value", TRICKY)
def test_escape_round_trip_is_exact(value):
    assert unescape_cell(escape_cell(value)) == value


@pytest.mark.parametrize("value", ['=1+1', "+91 call", "-5", "@SUM(A1)", "\tx", "\rx"])
def test_formula_like_cells_never_start_with_a_trigger_on_disk(tmp_path, value):
    path = tmp_path / "s.csv"
    write_csv(path, [{"text": value}], ["text"])
    with open(path, encoding="utf-8-sig", newline="") as f:
        cell = next(csv.DictReader(f))["text"]
    assert cell.startswith("'") and cell[1:] == value
    assert read_csv(path) == [{"text": value}]


def test_unescape_leaves_cells_alone_when_the_app_dropped_the_quote():
    # Excel and Sheets treat the leading quote as a "text" marker and often drop it on save.
    assert unescape_cell("=HYPERLINK(x)") == "=HYPERLINK(x)"
    assert unescape_cell("'plain") == "'plain"  # a quote not followed by a trigger is content


def _fresh(items):
    return [it.model_copy(update={"gold": None, "annotations": []}) for it in items if it.adversarial is None]


@pytest.mark.parametrize("app_keeps_quote", [True, False])
def test_malicious_text_survives_sheet_round_trip_and_imports(tmp_path, items, app_keeps_quote):
    evil = '=HYPERLINK("hxxp://evil[.]in","Click")'
    target = _fresh(items)[0].model_copy(update={"text": evil, "urls": []})
    sheet = tmp_path / "A1.csv"
    write_csv(sheet, export_sheet([target], "A1"), SHEET_COLUMNS)
    with open(sheet, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["text"].startswith("'=")  # what the spreadsheet app sees
    rows[0].update(label="scam", category="phishing_credential", confidence="2")
    if not app_keeps_quote:
        rows[0]["text"] = rows[0]["text"][1:]
    with open(sheet, "w", encoding="utf-8-sig", newline="") as f:  # simulate the app saving
        w = csv.DictWriter(f, fieldnames=SHEET_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    updated, errors = import_sheet([target], read_csv(sheet), "A1", "g1")
    assert errors == []
    assert updated[0].text == evil and updated[0].annotations[0].label == "scam"


# --- M4: encodings and Windows behaviour ---------------------------------------------------------

def _write_bytes(tmp_path, data: bytes):
    p = tmp_path / "in.csv"
    p.write_bytes(data)
    return p


@pytest.mark.parametrize("data", [
    "id,text\r\ndn-1,Café payment\r\n".encode("cp1252"),            # Excel "CSV (Comma delimited)"
    "id,text\r\ndn-1,ok\r\n".encode("utf-16"),                      # Excel "Unicode Text"
])
def test_non_utf8_csv_raises_actionable_error(tmp_path, data):
    with pytest.raises(CsvEncodingError, match="CSV UTF-8") as e:
        read_csv(_write_bytes(tmp_path, data))
    assert "cannot restore" in str(e.value)


@pytest.mark.parametrize("data", [
    "id,text\r\ndn-1,आपका खाता\r\n".encode("utf-8-sig"),           # Excel "CSV UTF-8" (BOM, CRLF)
    "id,text\ndn-1,आपका खाता\n".encode("utf-8"),                   # Google Sheets download (no BOM)
])
def test_utf8_csv_with_or_without_bom_and_crlf_reads(tmp_path, data):
    assert read_csv(_write_bytes(tmp_path, data)) == [{"id": "dn-1", "text": "आपका खाता"}]


def test_cli_reports_encoding_error_without_traceback(tmp_path, capsys):
    bad = _write_bytes(tmp_path, "id,text\r\ndn-1,Café\r\n".encode("cp1252"))
    code = main(["pilot-intake", str(bad), "--out", str(tmp_path / "o.jsonl"), "--basis-out",
                 str(tmp_path / "b.csv"), "--log", str(tmp_path / "log.jsonl")])
    err = capsys.readouterr().err
    assert code == 2 and "CSV UTF-8" in err and "Traceback" not in err


def test_cli_reports_locked_file_without_traceback(tmp_path, capsys, monkeypatch):
    import scamcheck.cli as cli

    def locked(path):
        raise PermissionError(13, "Permission denied", str(path))
    monkeypatch.setattr(cli, "read_csv", locked)
    code = main(["pilot-intake", str(tmp_path / "in.csv"), "--out", str(tmp_path / "o.jsonl"), "--basis-out",
                 str(tmp_path / "b.csv"), "--log", str(tmp_path / "log.jsonl")])
    err = capsys.readouterr().err
    assert code == 2 and "close it in Excel" in err


# --- H1 gate: notes and rationales typed into sheets are scanned before being stored ---------------

def test_import_blocks_identifiers_in_annotator_notes(tmp_path, items, capsys):
    data, sheet, log = tmp_path / "items.jsonl", tmp_path / "A1.csv", tmp_path / "log.jsonl"
    write_items(data, _fresh(items))
    assert main(["pilot-sheet", str(data), "--annotator", "A1", "--out", str(sheet), "--log", str(log)]) == 0
    rows = read_csv(sheet)
    rows[0].update(label="scam", category="other_scam", confidence="2", note="donor's number 9876543210")
    write_csv(sheet, rows, SHEET_COLUMNS)
    args = ["pilot-import", str(data), "--sheet", str(sheet), "--annotator", "A1", "--guideline", "g1",
            "--out", str(data), "--log", str(log)]
    assert main(args) == 1
    assert "annotations.0.note" in capsys.readouterr().err
    assert all(not it.annotations for it in load_items(data).items)  # nothing written
