"""Human review of mutation families: nothing inherits a label until a family is validated or a variant reviewed."""

import json
from datetime import date
from pathlib import Path

import pytest

from scamcheck.cli import main
from scamcheck.data.io import load_items
from scamcheck.data.pilot import read_csv, write_csv
from scamcheck.eval.mutate import variant_record
from scamcheck.eval.review import (MIN_FAMILY_REVIEWS, SHEET_COLUMNS, apply_reviews, export_sheet, family_status,
                                   import_sheet, visible)

ROOT = Path(__file__).parents[1]
BENCH = ROOT / "benchmarks" / "synthetic"
ITEMS = load_items(BENCH / "items.grouped.jsonl").items
TEXT = {it.id: it.text for it in ITEMS}
TODAY = date(2026, 10, 25)


def records(transforms=("typo", "zero_width", "prompt_injection"), seeds=(1, 2, 3)):
    return [variant_record(it.id, it.text, it.language, it.gold.label, t, s)
            for s in seeds for it in ITEMS for t in transforms]


def decision(vid, meaning="yes", reviewer="R1", label=None):
    return {"variant_id": vid, "reviewer": reviewer, "meaning_preserved": meaning,
            **({"label": label} if label else {}), "note": "", "guideline": "mr1", "at": "2026-10-25"}


def live(recs, transform):
    return [r for r in recs if r["transform"] == transform and r["status"] != "excluded_no_change"]


def test_without_reviews_nothing_inherits_a_label():
    recs = records()
    fam = apply_reviews(recs, [])
    assert all("label" not in r for r in recs)
    assert {r["status"] for r in live(recs, "typo")} == {"unvalidated_family"}
    assert {r["status"] for r in live(recs, "prompt_injection")} == {"needs_human_review"}
    assert fam["typo"]["status"] == "pending" and fam["prompt_injection"]["status"] == "meaning_changing"


def test_family_validated_only_after_enough_unanimous_yes():
    recs = records()
    typo = live(recs, "typo")
    almost = [decision(r["variant_id"]) for r in typo[:MIN_FAMILY_REVIEWS - 1]]
    apply_reviews(recs, almost)
    assert family_status(recs, almost)["typo"]["status"] == "pending"
    assert {r["status"] for r in live(recs, "typo")[MIN_FAMILY_REVIEWS:]} == {"unvalidated_family"}

    enough = [decision(r["variant_id"]) for r in typo[:MIN_FAMILY_REVIEWS]]
    fam = apply_reviews(recs, enough)
    assert fam["typo"]["status"] == "validated" and fam["typo"]["meaning_change_upper_95"] < 0.12
    rest = live(recs, "typo")[MIN_FAMILY_REVIEWS:]
    assert rest and all(r["status"] == "label_inherited" and r["label"] == r["parent_label"] for r in rest)
    assert {r["status"] for r in live(recs, "zero_width")} == {"unvalidated_family"}   # other families untouched


def test_one_meaning_change_blocks_inheritance_for_the_family():
    recs = records()
    typo = live(recs, "typo")
    revs = [decision(r["variant_id"]) for r in typo[:MIN_FAMILY_REVIEWS]]
    revs[0] = decision(typo[0]["variant_id"], meaning="no", label="ambiguous")
    fam = apply_reviews(recs, revs)
    assert fam["typo"]["status"] == "meaning_change_observed"
    assert typo[0]["status"] == "human_reviewed" and typo[0]["label"] == "ambiguous"
    assert typo[0]["review_meaning"] == "no"
    assert {r["status"] for r in typo[MIN_FAMILY_REVIEWS:]} == {"unvalidated_family"}


def test_meaning_changing_families_never_inherit_and_conflicts_give_no_label():
    recs = records()
    inj = live(recs, "prompt_injection")
    revs = [decision(inj[0]["variant_id"], label="scam"),
            decision(inj[1]["variant_id"], reviewer="R1", label="scam"),
            decision(inj[1]["variant_id"], reviewer="R2", label="ambiguous")]
    apply_reviews(recs, revs)
    assert inj[0]["status"] == "human_reviewed" and inj[0]["label"] == "scam"
    assert inj[1]["status"] == "review_conflict" and "label" not in inj[1]
    assert {r["status"] for r in inj[2:]} == {"needs_human_review"}


def test_sheet_is_seeded_blind_visible_and_skips_reviewed():
    recs = records()
    a = export_sheet(recs, TEXT, [], per_family=5, seed=9)
    assert a == export_sheet(recs, TEXT, [], per_family=5, seed=9)
    assert len(a) == 15 and set(a[0]) == set(SHEET_COLUMNS) and "parent_label" not in a[0]
    zw = [r for r in a if r["transform"] == "zero_width"]
    assert all("⟨U+" in r["variant_text"] and "​" not in r["variant_text"] for r in zw)
    again = export_sheet(recs, TEXT, [decision(r["variant_id"]) for r in a], per_family=5, seed=9)
    assert not {r["variant_id"] for r in a} & {r["variant_id"] for r in again}
    assert visible("a​b") == "a⟨U+200B⟩b"


def test_import_is_all_or_nothing_with_clear_errors():
    recs = records()
    typo, inj = live(recs, "typo")[0]["variant_id"], live(recs, "prompt_injection")[0]["variant_id"]
    ok, errs = import_sheet([{"variant_id": typo, "meaning_preserved": "Yes"}, {"variant_id": inj, "meaning_preserved": ""}],
                            recs, "R1", [], TODAY)
    assert errs == [] and len(ok) == 1 and ok[0]["meaning_preserved"] == "yes" and ok[0]["guideline"] == "mr1"
    bad_rows = [
        {"variant_id": typo, "meaning_preserved": "maybe"},
        {"variant_id": "mv-000000000000", "meaning_preserved": "yes"},
        {"variant_id": inj, "meaning_preserved": "yes"},                   # changing family needs a label
        {"variant_id": typo, "meaning_preserved": "yes", "label": "safe"},
        {"variant_id": typo, "meaning_preserved": "yes", "note": "call 9876543210"},
    ]
    for row in bad_rows:
        new, errs = import_sheet([{"variant_id": typo, "meaning_preserved": "yes"}, row], recs, "R2", [], TODAY)
        assert new == [] and errs, row
    new, errs = import_sheet([{"variant_id": typo, "meaning_preserved": "yes"}], recs, "R1", ok, TODAY)
    assert new == [] and "already reviewed" in errs[0]
    assert import_sheet([{"variant_id": typo, "meaning_preserved": "yes"}], recs, " ", [], TODAY)[1]


def test_formula_like_variant_text_survives_the_csv_round_trip(tmp_path):
    row = {"variant_id": "mv-1", "transform": "typo", "parent_text": "=HYPERLINK(\"x\")", "variant_text": "+1 call",
           "meaning_preserved": "", "label": "", "note": ""}
    write_csv(tmp_path / "s.csv", [row], SHEET_COLUMNS)
    raw = (tmp_path / "s.csv").read_text(encoding="utf-8-sig")
    assert "'=HYPERLINK" in raw and read_csv(tmp_path / "s.csv")[0] == row


def test_cli_sheet_import_and_robustness_round_trip(tmp_path):
    variants = ROOT / "reports/robustness/synthetic/variants.jsonl"
    sheet, revs = tmp_path / "sheet.csv", tmp_path / "reviews.jsonl"
    assert main(["review-sheet", str(BENCH / "items.grouped.jsonl"), "--variants", str(variants), "--out", str(sheet),
                 "--per-family", "30"]) == 0
    rows = read_csv(sheet)
    for r in rows:
        changing = r["transform"] in ("prompt_injection", "drop_link", "code_switch")
        r["meaning_preserved"] = "unsure" if changing else ("yes" if r["transform"] == "zero_width" else "")
    write_csv(sheet, rows, SHEET_COLUMNS)
    assert main(["review-import", "--sheet", str(sheet), "--variants", str(variants), "--reviewer", "R1",
                 "--out", str(revs)]) == 0
    assert main(["robustness", str(BENCH / "items.grouped.jsonl"), "--manifest", str(BENCH / "manifest.json"),
                 "--out-dir", str(tmp_path), "--reviews", str(revs)]) == 0
    res = json.loads((tmp_path / "robustness.json").read_text(encoding="utf-8"))
    fam = res["meta"]["families"]
    assert fam["zero_width"]["status"] == "validated" and fam["typo"]["status"] == "pending"
    assert res["meta"]["counts"]["label_inherited"] > 0 and res["meta"]["counts"]["reviewed_no_label"] > 0
    b4 = res["systems"]["B4-engine"]
    assert b4["consistency_validated_only"]["n"] > 0 and b4["consistency_provisional"] is True
    assert main(["review-import", "--sheet", str(sheet), "--variants", str(variants), "--reviewer", "R1",
                 "--out", str(revs)]) == 1       # the same reviewer cannot import the same decisions twice


def test_bad_review_file_is_a_usage_error(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text(json.dumps({"variant_id": "mv-1", "label": "scam"}) + "\n", encoding="utf-8")
    from scamcheck.cli import UsageError, _load_reviews
    with pytest.raises(UsageError, match="review-import"):     # the old {variant_id, label} format is rejected
        _load_reviews(str(p))
