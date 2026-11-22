"""Small, deterministic stand-ins for the ML models, so tests run in seconds and offline.

The real models are exercised by the evaluation framework (Module 9) instead.
"""

import hashlib
import math
import re

from app.services.embeddings.registry import EmbeddingModelSpec

WORD = re.compile(r"[a-z0-9ఀ-౿]+")


def words(text: str) -> list[str]:
    return WORD.findall(text.lower())


class FakeEmbedder:
    """Bag-of-words hashed into 128 dimensions: texts sharing words get similar vectors."""

    spec = EmbeddingModelSpec("fake-model", "fake/model", 128, 512, True, 0)

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.spec.dimensions
        for word in words(text):
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.spec.dimensions] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def tokenize(self, text: str) -> list[int]:
        return list(range(len(text.split())))

    def count_tokens(self, text: str) -> int:
        return len(text.split())


class FakeReranker:
    """Relevance = share of the query's words that appear in the passage."""

    def score(self, query: str, texts: list[str]) -> list[float]:
        query_words = set(words(query))
        return [len(query_words & set(words(text))) / max(len(query_words), 1) for text in texts]


SOURCE_BLOCK = re.compile(r'<source id="(\d+)"[^>]*>\n(.*?)\n</source>', re.DOTALL)


class FakeLLM:
    """Plays Gemini's role deterministically.

    - Query rewriting: returns `translations[question]` or the latest question itself.
    - Answering: one claim = the first sentence of source [1]; optionally adds a made-up
      claim (`hallucinate`) or cites a source that does not exist (`bad_citation`).
    - Figures: a fixed chart description.
    Every call is recorded in `calls` so tests can inspect prompts and images.
    """

    def __init__(self):
        self.calls: list[dict] = []
        self.translations: dict[str, str] = {}
        self.hallucinate = False
        self.bad_citation = False
        self.fail_with = None

    def generate_json(self, system, prompt, schema, images=None, temperature=None):
        from app.services.llm import prompts
        from app.services.multimodal.figures import FigureDescription

        self.calls.append({"schema": schema.__name__, "system": system, "prompt": prompt, "images": images or []})
        if self.fail_with:
            raise self.fail_with

        if schema is prompts.PreparedQuery:
            question = prompt.split("Latest question:\n", 1)[1].strip()
            return schema(standalone_question_en=self.translations.get(question, question))

        if schema is FigureDescription:
            return schema(kind="bar chart", description="Training loss decreases steadily over six epochs.")

        sources = SOURCE_BLOCK.findall(prompt)
        first_sentence = sources[0][1].split(". ")[0].rstrip(".") + "."
        claims = [{"text": first_sentence, "citations": [99] if self.bad_citation else [1]}]
        if self.hallucinate:
            claims.append({"text": "The study was funded by the Martian Space Agency.", "citations": [1]})
        translated = [f"[te] {c['text']}" for c in claims] if prompts.TRANSLATION_RULE_TE in system else []
        return schema(status="answered", claims=claims, translated_claims=translated)

    def schemas_called(self) -> list[str]:
        return [call["schema"] for call in self.calls]


class FakeNLI:
    """Entailment = share of the claim's content words found in the passage."""

    def predict(self, pairs):
        results = []
        for premise, hypothesis in pairs:
            claim_words = {w for w in words(hypothesis) if len(w) > 3}
            overlap = len(claim_words & set(words(premise))) / max(len(claim_words), 1)
            entailment = 0.95 if overlap >= 0.8 else 0.5 if overlap >= 0.5 else 0.05
            results.append({"entailment": entailment, "neutral": 1 - entailment, "contradiction": 0.0})
        return results
