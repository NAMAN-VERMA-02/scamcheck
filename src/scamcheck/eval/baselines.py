"""Comparable baselines. Each maps a message to exactly one of the three product verdicts.

B4 is not a re-implementation: it calls `scamcheck.engine.analyse`, the function behind the API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from ..engine import analyse
from ..engine.llm import ChatAdapter, classify
from ..engine.parse import parse
from ..engine.redact import redact
from ..engine.rules import run_rules

B2_CONFIG = {"vectorizer": "TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 5), sublinear_tf=True)",
             "classifier": "LogisticRegression(C=1.0, class_weight='balanced', max_iter=2000)",
             # Fixed before any evaluation; not tuned on dev or test.
             "t_high": 0.7, "t_low": 0.3,
             "train_labels": "scam vs. legitimate+promotional; ambiguous excluded"}


@dataclass
class System:
    name: str
    description: str
    predict: Callable[[str], str]
    config: dict = field(default_factory=dict)
    score: Optional[Callable[[str], float]] = None  # threshold-free score, only for ranking metrics (never shown)


def b1_rules_only(text: str) -> str:
    """Rule pack only, no URL or input signals, no model. Rule silence is read as NO_STRONG_SIGNALS, which shows
    what trusting a keyword list costs."""
    sev = {s.severity for s in run_rules(parse(text).text)}
    return "LIKELY_SCAM" if "HIGH" in sev else "UNCLEAR" if "MEDIUM" in sev else "NO_STRONG_SIGNALS"


def train_b2(texts: list[str], is_scam: list[bool], seed: int) -> tuple[Callable[[str], str], Callable[[str], float]]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline

    if len(set(is_scam)) < 2:
        raise ValueError("B2 needs both scam and non-scam training items")
    model = make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True),
                          LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, random_state=seed))
    model.fit([parse(t).text for t in texts], is_scam)
    hi, lo = B2_CONFIG["t_high"], B2_CONFIG["t_low"]

    def score(text: str) -> float:
        return float(model.predict_proba([parse(text).text])[0][1])

    def predict(text: str) -> str:
        p = score(text)
        return "LIKELY_SCAM" if p >= hi else "NO_STRONG_SIGNALS" if p <= lo else "UNCLEAR"
    return predict, score


def b3_llm_only(adapter: ChatAdapter) -> Callable[[str], str]:
    def predict(text: str) -> str:
        redacted, residual = redact(parse(text).text)
        if residual:
            return "UNCLEAR"
        r = classify(adapter, redacted)
        if r.status != "ok":
            return "UNCLEAR"
        return {"scam": "LIKELY_SCAM", "not_scam": "NO_STRONG_SIGNALS"}.get(r.label or "", "UNCLEAR")
    return predict


def build_systems(train_texts: list[str], train_is_scam: list[bool], seed: int,
                  model: Optional[ChatAdapter] = None) -> list[System]:
    b2_predict, b2_score = train_b2(train_texts, train_is_scam, seed)
    systems = [
        System("B0-unclear", "Control: always UNCLEAR", lambda t: "UNCLEAR"),
        System("B0-scam", "Control: always LIKELY_SCAM", lambda t: "LIKELY_SCAM"),
        System("B1-rules", "Rule pack only; rule silence → NO_STRONG_SIGNALS", b1_rules_only),
        System("B2-tfidf-lr", "Char n-gram TF-IDF + logistic regression, trained on train split only",
               b2_predict, B2_CONFIG, b2_score),
    ]
    if model is not None:
        systems.append(System("B3-llm", "Zero-shot LLM, fixed prompt, redacted input", b3_llm_only(model),
                              {"model_id": model.model_id}))
    b4_desc = ("Full evidence-first engine (rules + URL structure + LLM + combiner)" if model is not None
               else "Evidence-first engine in rule-only mode (no model configured: abstains unless a HIGH signal)")
    systems.append(System("B4-engine", b4_desc,
                          lambda t: analyse(t, model=model, llm_opt_in=model is not None).verdict))
    return systems
