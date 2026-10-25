"""Temporal hold-out on top of the group-aware split (SYNTHETIC fixtures with assigned collection dates)."""

from datetime import date
from pathlib import Path

import pytest

from scamcheck.cli import main
from scamcheck.data.grouping import group_items
from scamcheck.data.split import TemporalSplitError, check_leakage, split_items

ROOT = Path(__file__).parents[1]
CUT = date(2026, 3, 31)
# Older half before the cutoff, newer half after; fx-003 shares a campaign with fx-001/fx-002, so that campaign
# straddles the cutoff.
NEW = {"fx-003", "fx-006", "fx-008", "fx-009", "fx-010", "fx-011", "fx-014", "fx-019", "fx-020"}


def dated(items, new=NEW):
    out = []
    for it in items:
        d = date(2026, 6, 1) if it.id in new else date(2026, 1, 15)
        out.append(it.model_copy(update={"provenance": it.provenance.model_copy(update={"collected_at": d})}))
    return group_items(out, 0.6, 0.4, {})[0]


def test_future_campaigns_go_wholly_to_test_and_never_to_training(items):
    grouped = dated(items)
    m = split_items(grouped, allow_synthetic_in_test=True, temporal_cutoff=CUT)
    split_of = {r["id"]: r["split"] for r in m["items"]}
    by_id = {it.id: it for it in grouped}
    future = {by_id[i].campaign_id for i in NEW}
    for i, s in split_of.items():
        if by_id[i].campaign_id in future:
            assert s == "test", i
        else:
            assert s in ("train", "dev") and by_id[i].provenance.collected_at <= CUT, i
    t = m["temporal"]
    assert t["cutoff"] == "2026-03-31" and t["train_dev_latest"] <= "2026-03-31"
    assert by_id["fx-001"].campaign_id in t["straddling_campaigns"]     # fx-001 is old but its campaign is not
    assert split_of["fx-001"] == "test"
    assert m["params"]["temporal_cutoff"] == "2026-03-31"
    assert check_leakage(grouped, m, 0.6) == []


def test_ineligible_future_campaigns_are_excluded_not_trained_on(items):
    grouped = dated(items)
    with pytest.raises(TemporalSplitError, match="none is test-eligible"):
        split_items(grouped, allow_synthetic_in_test=False, temporal_cutoff=CUT)


@pytest.mark.parametrize("new,match", [
    (set(), "no campaign has an item collected after the cutoff"),
    ({f"fx-{i:03d}" for i in range(1, 21)}, "Nothing is left to train on"),
    ({"fx-001", "fx-002", "fx-003", "fx-004"}, "but no legitimate"),  # future data has scams only
])
def test_invalid_temporal_structure_fails_with_a_reason(items, new, match):
    with pytest.raises(TemporalSplitError, match=match):
        split_items(dated(items, new), allow_synthetic_in_test=True, temporal_cutoff=CUT)


def test_leakage_check_catches_future_items_in_training(items):
    grouped = dated(items)
    m = split_items(grouped, allow_synthetic_in_test=True, temporal_cutoff=CUT)
    row = next(r for r in m["items"] if r["id"] == "fx-008")
    row["split"] = "train"
    assert any(p.startswith("temporal: fx-008") for p in check_leakage(grouped, m, 0.6))


def test_non_temporal_manifests_are_unchanged(items):
    m = split_items(dated(items), allow_synthetic_in_test=True)
    assert "temporal" not in m and "temporal_cutoff" not in m["params"]


def test_cli_refuses_the_single_date_synthetic_benchmark(tmp_path, capsys):
    out = tmp_path / "m.json"
    code = main(["split", str(ROOT / "benchmarks/synthetic/items.grouped.jsonl"), "--out", str(out),
                 "--allow-synthetic-in-test", "--temporal-cutoff", "2026-10-24"])
    err = capsys.readouterr().err
    assert code == 2 and not out.exists()
    assert "1 distinct date" in err and "No manifest was written" in err
    assert main(["split", str(ROOT / "benchmarks/synthetic/items.grouped.jsonl"), "--out", str(out),
                 "--temporal-cutoff", "31/12/2026"]) == 2
    assert "must be a date" in capsys.readouterr().err
