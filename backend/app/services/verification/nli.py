"""Natural Language Inference (NLI) model.

Given a premise (a source passage) and a hypothesis (a claim), an NLI model predicts:
  entailment    - the premise supports the claim
  neutral       - the premise neither supports nor contradicts it
  contradiction - the premise says the opposite
DeBERTa-v3 fine-tuned on MNLI, FEVER and ANLI is a strong, CPU-friendly choice.
"""

import logging
import threading
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


class NLIModel(Protocol):
    def predict(self, pairs: list[tuple[str, str]]) -> list[dict[str, float]]: ...


class TransformersNLI:
    def __init__(self, model_name: str):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        logger.info("Loading NLI model %s", model_name)
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name).eval()
        # Map label names to output positions (models differ in label order)
        self.labels = {name.lower(): index for index, name in self.model.config.id2label.items()}

    def predict(self, pairs: list[tuple[str, str]], batch_size: int = 8) -> list[dict[str, float]]:
        results = []
        for start in range(0, len(pairs), batch_size):
            batch = pairs[start : start + batch_size]
            inputs = self.tokenizer(
                [premise for premise, _ in batch],
                [hypothesis for _, hypothesis in batch],
                truncation="only_first",  # shorten the passage, never the claim
                max_length=512,
                padding=True,
                return_tensors="pt",
            )
            with self.torch.no_grad():
                probabilities = self.torch.softmax(self.model(**inputs).logits, dim=-1)
            for row in probabilities.tolist():
                results.append({label: row[index] for label, index in self.labels.items()})
        return results


_model: NLIModel | None = None
_lock = threading.Lock()


def get_nli_model() -> NLIModel:
    global _model
    with _lock:
        if _model is None:
            _model = TransformersNLI(settings.NLI_MODEL)
        return _model
