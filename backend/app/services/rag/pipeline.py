"""Retrieval-Augmented Generation: answer a question from the user's own documents.

1. Detect the question's language                        (Module 6)
2. Rewrite follow-ups / translate to a standalone English question (LLM call 1, only if needed)
3. Hybrid retrieval + cross-encoder reranking            (Module 4)
4. Relevance gate: no relevant passage -> "not enough information", no LLM call
5. Grounded generation as cited claims (+ Telugu translation)  (LLM call 2)
6. Claim verification against the cited passages         (Module 8)
"""

import logging
import time
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Chunk
from app.services.llm import client as llm_client
from app.services.llm import prompts
from app.services.multilingual.language import detect_language, resolve_answer_language
from app.services.multimodal.figures import load_figure_images
from app.services.retrieval.retriever import retrieve
from app.services.security.injection_guard import find_injection_signals
from app.services.verification.verifier import ClaimCheck, verify_claims

logger = logging.getLogger(__name__)

INSUFFICIENT_MESSAGES = {
    "en": "I could not find enough information in your documents to answer this question.",
    "te": "మీ పత్రాలలో ఈ ప్రశ్నకు సమాధానం ఇవ్వడానికి తగినంత సమాచారం నాకు దొరకలేదు.",
}


@dataclass
class SourcePassage:
    number: int  # [n] as shown to the LLM and the user
    chunk: Chunk
    score: float  # reranker relevance probability
    suspicious: bool = False


@dataclass
class AnswerClaimResult:
    text: str  # English
    text_display: str  # answer language
    citations: list[int]
    check: ClaimCheck | None = None


@dataclass
class RagAnswer:
    status: str  # answered | insufficient_information
    question_language: str
    answer_language: str
    english_question: str
    sources: list[SourcePassage]
    claims: list[AnswerClaimResult]
    timings: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    faithfulness: float | None = None

    @staticmethod
    def _join(parts: list[tuple[str, list[int]]]) -> str:
        return " ".join(text + ("".join(f"[{n}]" for n in cites) if cites else "") for text, cites in parts)

    @property
    def display_text(self) -> str:
        return self._join([(c.text_display, c.citations) for c in self.claims])

    @property
    def english_text(self) -> str:
        return self._join([(c.text, c.citations) for c in self.claims])


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 1)


def _insufficient(question_language: str, answer_language: str, english_question: str, timings, sources=None) -> RagAnswer:
    return RagAnswer(
        status="insufficient_information",
        question_language=question_language,
        answer_language=answer_language,
        english_question=english_question,
        sources=sources or [],
        claims=[AnswerClaimResult(INSUFFICIENT_MESSAGES["en"], INSUFFICIENT_MESSAGES[answer_language], [])],
        timings=timings,
    )


def answer_question(
    db: Session,
    user_id: int,
    question: str,
    *,
    history: list[tuple[str, str]] | None = None,
    answer_language: str = "auto",
    document_ids: list[int] | None = None,
    verify: bool = True,
) -> RagAnswer:
    history = (history or [])[-settings.HISTORY_TURNS :]
    timings: dict[str, float] = {}
    llm = llm_client.get_llm()  # fail fast with a clear message if no API key is configured

    # 1. Language
    question_language = detect_language(question)
    language = resolve_answer_language(answer_language, question_language)

    # 2. Standalone English question (skipped for a first question in English: saves an LLM call)
    start = time.perf_counter()
    english_question = question
    if question_language != "en" or history:
        prepared = llm.generate_json(
            prompts.QUERY_SYSTEM, prompts.query_prompt(history, question), prompts.PreparedQuery, temperature=0.0
        )
        english_question = prepared.standalone_question_en.strip() or question
    timings["query_rewrite_ms"] = _elapsed_ms(start)

    # 3. Retrieval. Dense search uses the original question when there is no history, so the
    # multilingual embedding model matches Telugu questions to English text directly.
    start = time.perf_counter()
    results = retrieve(
        db,
        user_id,
        question if not history else english_question,
        english_query=english_question,
        top_k=settings.RAG_TOP_K,
        mode="hybrid",
        rerank=True,
        document_ids=document_ids,
    )
    timings["retrieval_ms"] = _elapsed_ms(start)

    # 4. Relevance gate
    relevant = [r for r in results if r.score >= settings.RELEVANCE_THRESHOLD]
    if not relevant:
        logger.info("No passage above relevance threshold %.2f", settings.RELEVANCE_THRESHOLD)
        return _insufficient(question_language, language, english_question, timings)

    sources = [
        SourcePassage(i, r.chunk, r.score, bool(find_injection_signals(r.chunk.text)))
        for i, r in enumerate(relevant, start=1)
    ]
    warnings = []
    if any(s.suspicious for s in sources):
        logger.warning("Possible prompt injection in sources %s", [s.chunk.id for s in sources if s.suspicious])
        warnings.append("Some source passages contain instruction-like text and were treated strictly as data.")

    # 5. Generation
    start = time.perf_counter()
    formatted = [
        prompts.format_source(
            s.number,
            s.chunk.document.title or s.chunk.document.original_filename,
            s.chunk.page_number,
            s.chunk.element_type,
            s.chunk.text,
            s.suspicious,
        )
        for s in sources
    ]
    images = load_figure_images(sources)  # Module 7: the model also sees retrieved figures
    prompt = prompts.answer_prompt(formatted, history, english_question, question)
    if images:
        prompt = "The attached images are the figures from the sources marked type=\"figure\" or \"image\", in order.\n\n" + prompt
    generated = llm.generate_json(
        prompts.answer_system_prompt(language), prompt, prompts.GeneratedAnswer, images=images
    )
    timings["generation_ms"] = _elapsed_ms(start)

    valid_numbers = {s.number for s in sources}
    translations = [t.strip() for t in generated.translated_claims]
    claims = []
    for index, claim in enumerate(generated.claims):
        if not claim.text.strip():
            continue
        display = claim.text
        if language == "te":
            if index < len(translations) and translations[index]:
                display = translations[index]
            elif "Telugu translation was not available" not in " ".join(warnings):
                warnings.append("Telugu translation was not available for part of the answer.")
        # Drop citation numbers the model invented
        claims.append(AnswerClaimResult(claim.text.strip(), display, sorted(set(claim.citations) & valid_numbers)))

    if generated.status == "insufficient_information" or not claims:
        answer = _insufficient(question_language, language, english_question, timings, sources)
        if claims:  # keep the model's explanation of what is missing
            answer.claims = [AnswerClaimResult(c.text, c.text_display, []) for c in claims]
        answer.warnings = warnings
        return answer

    answer = RagAnswer("answered", question_language, language, english_question, sources, claims, timings, warnings)

    # 6. Verification
    if verify:
        start = time.perf_counter()
        checks = verify_claims([c.text for c in claims], [c.citations for c in claims], sources)
        for claim, check in zip(claims, checks):
            claim.check = check
        scored = [c.check.score for c in claims if c.check]
        answer.faithfulness = round(sum(scored) / len(scored), 3) if scored else None
        timings["verification_ms"] = _elapsed_ms(start)
    return answer
