"""Seeded mutation lab: determinism, replay, lineage and property-based robustness checks.

Hypothesis prints the failing seed/transform/example and a reproduction blob (print_blob in conftest), so a
failure can be replayed exactly.
"""

import json
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from scamcheck.data.io import load_items
from scamcheck.engine import analyse
from scamcheck.eval.mutate import BY_NAME, GENERATOR_VERSION, TRANSFORMS, generate, replay, variant_record

ROOT = Path(__file__).parents[1]
BENCH = ROOT / "benchmarks" / "synthetic"
ITEMS = load_items(BENCH / "items.grouped.jsonl").items
MANIFEST = json.loads((BENCH / "manifest.json").read_text(encoding="utf-8"))
SPLIT = {r["id"]: r["split"] for r in MANIFEST["items"]}
SCAM_PARENTS = [it for it in ITEMS if it.gold.label == "scam" and analyse(it.text).verdict == "LIKELY_SCAM"]
# Transforms that the normaliser is designed to undo; B4 verdicts must not move under them.
NORMALISED = ["whitespace", "zero_width", "confusables", "fullwidth_nfkc", "casing", "url_defang_style"]


@given(st.integers(0, 10_000), st.sampled_from([t.name for t in TRANSFORMS]), st.sampled_from(ITEMS))
def test_generation_is_deterministic_and_replayable(seed, transform, item):
    a = generate(item.id, item.text, transform, seed)
    assert a == generate(item.id, item.text, transform, seed)
    rec = variant_record(item.id, item.text, item.language, item.gold.label, transform, seed)
    assert replay([rec], {item.id: item.text}) == []
    assert rec["generator_version"] == GENERATOR_VERSION


@given(st.integers(0, 10_000), st.sampled_from(NORMALISED), st.sampled_from(SCAM_PARENTS))
def test_normalised_transforms_never_change_the_verdict(seed, transform, item):
    variant = generate(item.id, item.text, transform, seed)
    assert analyse(variant).verdict == analyse(item.text).verdict


@given(st.integers(0, 10_000), st.sampled_from([t.name for t in TRANSFORMS if t.preserving]),
       st.sampled_from(SCAM_PARENTS))
def test_preserving_transforms_never_turn_a_scam_into_reassurance(seed, transform, item):
    assert analyse(generate(item.id, item.text, transform, seed)).verdict != "NO_STRONG_SIGNALS"


def test_meaning_changing_variants_need_review_and_carry_no_label():
    it = ITEMS[0]
    rec = variant_record(it.id, it.text, it.language, it.gold.label, "prompt_injection", 1)
    assert rec["status"] == "needs_human_review" and "label" not in rec
    assert not BY_NAME["prompt_injection"].preserving


def test_unchanged_outputs_are_excluded():
    rec = variant_record("x-001", "no link here", "english", "legitimate", "drop_link", 1)
    assert rec["status"] == "excluded_no_change"


def test_replay_detects_tampering():
    it = ITEMS[0]
    rec = variant_record(it.id, it.text, it.language, it.gold.label, "typo", 5)
    assert replay([{**rec, "output_sha256": "0" * 64}], {it.id: it.text})
    assert replay([{**rec, "seed": 6}], {it.id: it.text}) or generate(it.id, it.text, "typo", 6) == rec["text"]


def test_committed_variants_replay_and_come_only_from_dev_and_test():
    path = ROOT / "reports/robustness/synthetic/variants.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert replay(records, {it.id: it.text for it in ITEMS}) == []
    assert {SPLIT[r["parent_id"]] for r in records} <= {"dev", "test"}
    assert len({r["seed"] for r in records}) >= 3


@pytest.mark.parametrize("name", [t.name for t in TRANSFORMS])
def test_every_transform_changes_some_parent(name):
    t = BY_NAME[name]
    assert any(generate(it.id, it.text, name, 1) != it.text for it in ITEMS if it.language in t.languages)
