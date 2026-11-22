"""Hallucination-aware answer verification (Module 8).

Every answer claim is checked against the passages it cites:
  - premises tried: each cited passage, its 3-sentence windows, and all cited passages
    combined (a claim may join facts from two sources)
  - the best entailment probability decides the verdict
  - a claim that cites nothing is checked against every source and flagged

This catches many unsupported or contradicted claims, but NOT all: NLI models can miss
paraphrases, numerical reasoning and long multi-step inferences. Verdicts are
confidence indicators, not proof.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.config import settings
from app.services.chunking.chunker import split_sentences
from app.services.verification import nli

if TYPE_CHECKING:
    from app.services.rag.pipeline import SourcePassage

logger = logging.getLogger(__name__)

VERDICT_SCORES = {"supported": 1.0, "partially_supported": 0.5, "unsupported": 0.0, "contradicted": 0.0}


@dataclass
class ClaimCheck:
    verdict: str  # supported | partially_supported | unsupported | contradicted | not_checked
    confidence: float | None
    evidence_number: int | None
    evidence_snippet: str | None
    cited: bool  # did the claim cite any source?

    @property
    def score(self) -> float:
        return VERDICT_SCORES.get(self.verdict, 0.0)


@dataclass
class _Premise:
    number: int
    text: str


def _premises(sources: list["SourcePassage"], numbers: list[int]) -> list[_Premise]:
    chosen = [s for s in sources if s.number in numbers] or sources
    premises = []
    for source in chosen:
        text = source.chunk.text
        premises.append(_Premise(source.number, text))
        sentences = split_sentences(text)
        if len(sentences) > 3:  # small windows help when the evidence is one sentence in a long passage
            premises += [_Premise(source.number, " ".join(sentences[i : i + 3])) for i in range(0, len(sentences) - 2, 2)]
    if len(chosen) > 1:
        premises.append(_Premise(chosen[0].number, "\n".join(s.chunk.text for s in chosen)))
    return premises


def verdict_for(entailment: float, contradiction: float) -> str:
    if entailment >= settings.SUPPORTED_THRESHOLD:
        return "supported"
    if contradiction >= settings.CONTRADICTION_THRESHOLD:
        return "contradicted"
    if entailment >= settings.PARTIAL_THRESHOLD:
        return "partially_supported"
    return "unsupported"


def verify_claims(claims: list[str], citations: list[list[int]], sources: list["SourcePassage"]) -> list[ClaimCheck]:
    not_checked = [ClaimCheck("not_checked", None, None, None, bool(c)) for c in citations]
    if not claims or not sources:
        return not_checked
    try:
        model = nli.get_nli_model()
    except Exception:  # model missing/offline: answer still works, just unverified
        logger.exception("NLI model unavailable; claims not verified")
        return not_checked

    premise_lists = [_premises(sources, numbers) for numbers in citations]
    pairs = [(p.text, claim) for claim, premises in zip(claims, premise_lists) for p in premises]
    scores = iter(model.predict(pairs))

    checks = []
    for numbers, premises in zip(citations, premise_lists):
        rows = [(premise, next(scores)) for premise in premises]
        best_premise, best = max(rows, key=lambda row: row[1].get("entailment", 0.0))
        worst_premise, worst = max(rows, key=lambda row: row[1].get("contradiction", 0.0))
        verdict = verdict_for(best.get("entailment", 0.0), worst.get("contradiction", 0.0))
        evidence, confidence = (
            (worst_premise, worst["contradiction"]) if verdict == "contradicted" else (best_premise, best["entailment"])
        )
        checks.append(
            ClaimCheck(verdict, round(confidence, 3), evidence.number, evidence.text[:600], cited=bool(numbers))
        )
    return checks
