"""Assign campaign/duplicate groups so related items can never straddle splits.

Two items share a group when any of these holds:
  * identical normalised text (exact duplicate)
  * character 5-gram Jaccard >= threshold (near duplicate), unless a reviewer marked the pair "different"
  * both are scams pointing at the same registered domain (same campaign infrastructure), excluding shared
    platforms and any domain that also appears on a non-scam item
  * both are scams sharing a pseudonymised scammer id (phone/UPI/email/account)
  * one is a synthetic/adversarial derivative of the other (seed_id / parent_id)
  * a reviewer marked the pair "same"
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from .normalise import content_hash, jaccard, shingles
from .schema import Item

DEFAULT_THRESHOLD = 0.6
DEFAULT_REVIEW_LOW = 0.4

# Hosting/shortener/messaging domains used by unrelated actors; sharing one is not evidence of one campaign.
# shortcut: hand-maintained list; extend whenever the review file shows a platform domain linking unrelated scams.
SHARED_PLATFORM_DOMAINS = {
    "t.me", "telegram.me", "wa.me", "whatsapp.com", "bit.ly", "tinyurl.com", "cutt.ly", "is.gd", "rb.gy",
    "shorturl.at", "forms.gle", "google.com", "youtube.com", "youtu.be", "instagram.com", "facebook.com",
    "github.io", "blogspot.com", "wordpress.com", "netlify.app", "vercel.app", "pages.dev", "web.app",
    "firebaseapp.com", "herokuapp.com", "glitch.me", "wixsite.com", "weebly.com", "000webhostapp.com",
    "ngrok-free.app", "ngrok.io", "duckdns.org", "linktr.ee",
}


def linking_domains(items: list[Item]) -> dict[str, list[str]]:
    """Domains that may link scam items into one campaign.

    A domain that also appears on any non-scam item is treated as an official/brand domain (scams often quote the
    real bank site) and never links; nor do shared hosting/shortener platforms.
    """
    non_scam = {u.registered_domain for it in items if it.gold and it.gold.label != "scam" for u in it.urls}
    return {it.id: sorted({u.registered_domain for u in it.urls
                           if u.registered_domain not in SHARED_PLATFORM_DOMAINS and u.registered_domain not in non_scam})
            for it in items if it.gold and it.gold.label == "scam"}


@dataclass
class PairCandidate:
    a: str
    b: str
    similarity: float
    # auto_merged | needs_review | already_grouped | decided_same | decided_different | linked_by_domain | linked_by_scammer
    status: str

    def to_json(self) -> dict:
        return {"a": self.a, "b": self.b, "similarity": round(self.similarity, 3), "status": self.status}


class _UnionFind:
    def __init__(self, keys):
        self.parent = {k: k for k in keys}

    def find(self, k):
        while self.parent[k] != k:
            self.parent[k] = self.parent[self.parent[k]]
            k = self.parent[k]
        return k

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def load_decisions(path: Path | None) -> dict[frozenset, str]:
    """Reviewer decisions: JSONL lines {"a": id, "b": id, "decision": "same"|"different"}."""
    if path is None or not Path(path).exists():
        return {}
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            if d["decision"] not in ("same", "different"):
                raise ValueError(f"bad decision {d!r}")
            out[frozenset((d["a"], d["b"]))] = d["decision"]
    return out


def group_items(
    items: list[Item],
    threshold: float = DEFAULT_THRESHOLD,
    review_low: float = DEFAULT_REVIEW_LOW,
    decisions: dict[frozenset, str] | None = None,
) -> tuple[list[Item], list[PairCandidate]]:
    decisions = decisions or {}
    ids = [it.id for it in items]
    uf = _UnionFind(ids)
    by_id = {it.id: it for it in items}

    hashes: dict[str, str] = {}
    for it in items:
        h = content_hash(it.text)
        if h in hashes:
            uf.union(it.id, hashes[h])
        else:
            hashes[h] = it.id

    candidates: list[PairCandidate] = []
    first_seen: dict[str, str] = {}
    keys = {i: [f"domain:{d}" for d in ds] for i, ds in linking_domains(items).items()}
    for it in items:
        if it.gold and it.gold.label == "scam":
            keys.setdefault(it.id, []).extend(f"scammer:{s}" for s in it.scammer_ids)
    for item_id in ids:
        for key in keys.get(item_id, []):
            if key in first_seen:
                uf.union(item_id, first_seen[key])
                candidates.append(PairCandidate(first_seen[key], item_id, 0.0, f"linked_by_{key.split(':')[0]}"))
            else:
                first_seen[key] = item_id

    for it in items:
        for ref in (it.synthetic and it.synthetic.seed_id, it.adversarial and it.adversarial.parent_id):
            if ref and ref in by_id:
                uf.union(it.id, ref)

    # shortcut: O(n^2) pairwise Jaccard is fine below ~5k items; switch to MinHash/LSH beyond that.
    sh = {it.id: shingles(it.text) for it in items}
    for a, b in combinations(ids, 2):
        sim = jaccard(sh[a], sh[b])
        decision = decisions.get(frozenset((a, b)))
        if decision == "same":
            uf.union(a, b)
            candidates.append(PairCandidate(a, b, sim, "decided_same"))
        elif decision == "different":
            if sim >= review_low:
                candidates.append(PairCandidate(a, b, sim, "decided_different"))
        elif sim >= threshold:
            uf.union(a, b)
            candidates.append(PairCandidate(a, b, sim, "auto_merged"))
        elif sim >= review_low:
            candidates.append(PairCandidate(a, b, sim, "needs_review"))

    members: dict[str, list[str]] = {}
    for i in ids:
        members.setdefault(uf.find(i), []).append(i)
    group_of = {}
    for mids in members.values():
        gid = "g-" + hashlib.sha256("|".join(sorted(mids)).encode()).hexdigest()[:10]
        for m in mids:
            group_of[m] = gid

    for c in candidates:  # don't ask reviewers about pairs another edge already merged
        if c.status == "needs_review" and group_of[c.a] == group_of[c.b]:
            c.status = "already_grouped"

    grouped = [it.model_copy(update={"campaign_id": group_of[it.id]}) for it in items]
    candidates.sort(key=lambda c: -c.similarity)
    return grouped, candidates
