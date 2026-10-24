import copy

import pytest

from scamcheck.data.grouping import DEFAULT_THRESHOLD, group_items
from scamcheck.data.split import check_leakage, split_items


@pytest.fixture
def grouped(items):
    return group_items(items)[0]


def split_of(manifest):
    return {r["id"]: r["split"] for r in manifest["items"]}


def test_requires_grouping_first(items):
    with pytest.raises(ValueError, match="group"):
        split_items(items)


def test_synthetic_never_in_test_by_default(grouped):
    m = split_items(grouped)
    assert "test" not in m["counts"]
    assert set(m["counts"]) == {"train", "dev"}


def test_pending_items_excluded(grouped):
    m = split_items(grouped, allow_synthetic_in_test=True)
    assert m["excluded"] == [{"id": "fx-018", "reason": "no gold label"}]
    assert "fx-018" not in split_of(m)


def test_groups_never_straddle_splits_and_split_is_deterministic(grouped):
    m = split_items(grouped, allow_synthetic_in_test=True)
    s = split_of(m)
    for it in grouped:
        if it.id in s:
            peers = {s[o.id] for o in grouped if o.campaign_id == it.campaign_id and o.id in s}
            assert peers == {s[it.id]}
    assert set(m["counts"]) == {"train", "dev", "test"}
    assert split_items(list(reversed(grouped)), allow_synthetic_in_test=True) == m


def test_leakage_check_passes_on_clean_manifest(grouped):
    m = split_items(grouped, allow_synthetic_in_test=True)
    assert check_leakage(grouped, m, DEFAULT_THRESHOLD) == []


def _move(manifest, item_id, to):
    m = copy.deepcopy(manifest)
    for r in m["items"]:
        if r["id"] == item_id:
            r["split"] = to
    return m


def test_leakage_check_catches_moved_group_member(grouped):
    m = split_items(grouped, allow_synthetic_in_test=True)
    current = split_of(m)["fx-002"]
    other = next(x for x in ("train", "dev") if x != current)
    problems = check_leakage(grouped, _move(m, "fx-002", other), DEFAULT_THRESHOLD)
    kinds = " ".join(problems)
    assert "campaign" in kinds and "scam domain" in kinds and "near duplicate" in kinds


def test_leakage_check_catches_edits_and_ineligible_test_items(grouped):
    m = split_items(grouped, allow_synthetic_in_test=True)
    edited = [it.model_copy(update={"text": it.text + " edited"}) if it.id == "fx-010" else it for it in grouped]
    assert any("content changed" in p for p in check_leakage(edited, m, DEFAULT_THRESHOLD))

    strict = copy.deepcopy(m)
    strict["params"]["allow_synthetic_in_test"] = False
    test_ids = [i for i, sp in split_of(m).items() if sp == "test"]
    assert test_ids
    problems = check_leakage(grouped, strict, DEFAULT_THRESHOLD)
    assert sum("in test but synthetic" in p for p in problems) == len(test_ids)
