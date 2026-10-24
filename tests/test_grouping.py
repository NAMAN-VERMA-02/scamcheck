from scamcheck.data.grouping import group_items
from scamcheck.data.normalise import content_hash, normalise


def groups(items, **kw):
    grouped, pairs = group_items(items, **kw)
    return {it.id: it.campaign_id for it in grouped}, pairs


def test_normalise_masks_numbers_and_invisible_chars():
    assert normalise("Pay​ Rs 2,500 NOW") == normalise("pay rs 999 now")
    assert content_hash("A <OTP> b") == content_hash("a <otp> B")


def test_expected_groups(items):
    g, _ = groups(items)
    assert g["fx-001"] == g["fx-002"] == g["fx-003"]  # near dup + shared scam domain
    assert g["fx-005"] == g["fx-016"]                  # adversarial parent
    assert g["fx-007"] == g["fx-017"]                  # translated seed
    assert g["fx-008"] == g["fx-009"]                  # exact template duplicate
    assert g["fx-005"] != g["fx-006"]                  # both use t.me, unrelated campaigns
    assert g["fx-004"] != g["fx-020"]


def test_pairs_already_merged_by_lineage_are_not_sent_to_review(items):
    _, pairs = groups(items)
    pair = next(p for p in pairs if {p.a, p.b} == {"fx-005", "fx-016"})
    assert pair.status == "already_grouped"


def test_grouping_is_deterministic(items):
    assert groups(items)[0] == groups(list(reversed(items)))[0]


def test_review_decisions(items):
    by_id = {it.id: it for it in items}
    a = by_id["fx-019"]
    b = a.model_copy(update={"id": "fx-090", "text": a.text.replace("Thank you for choosing", "Thanks for using")})
    base = [a, b, by_id["fx-004"], by_id["fx-020"]]

    g, pairs = groups(base, threshold=0.95, review_low=0.3)
    pair = next(p for p in pairs if {p.a, p.b} == {"fx-019", "fx-090"})
    assert pair.status == "needs_review" and g["fx-019"] != g["fx-090"]

    g, _ = groups(base, threshold=0.5, review_low=0.3)
    assert g["fx-019"] == g["fx-090"]  # auto-merged at a lower threshold

    g, pairs = groups(base, threshold=0.5, review_low=0.3,
                      decisions={frozenset(("fx-019", "fx-090")): "different",
                                 frozenset(("fx-004", "fx-020")): "same"})
    assert g["fx-019"] != g["fx-090"]
    assert g["fx-004"] == g["fx-020"]
    statuses = {frozenset((p.a, p.b)): p.status for p in pairs}
    assert statuses[frozenset(("fx-019", "fx-090"))] == "decided_different"
    assert statuses[frozenset(("fx-004", "fx-020"))] == "decided_same"
