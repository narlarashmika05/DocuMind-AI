# Module 8 – Hallucination Detection and Answer Verification

## Objective
Check every statement of every answer against the source passages, show users which statements are supported, which are not, and the evidence — while being honest that automatic verification is a **confidence signal, not proof**.

## Concepts

### What is a hallucination?
Text that is fluent and confident but **not supported by the sources** (intrinsic: contradicts the source; extrinsic: adds facts not in the source). RAG reduces hallucinations but does not eliminate them: the model can still merge facts wrongly, change numbers, or add background knowledge.

### Claim decomposition
Long answers mix true and false parts, so we verify **atomic claims**. The generator is asked to output a list of short, self-contained claims, each with citations — the decomposition comes for free, with no extra LLM call.

### Natural Language Inference (NLI)
An NLI model reads `(premise, hypothesis)` and outputs probabilities for **entailment**, **neutral**, **contradiction**. We use `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` (trained on MNLI, FEVER fact-checking and adversarial ANLI). It is a cross-encoder: premise and claim are read together.

### Verification algorithm
For each claim:
1. Premises = each **cited** passage, its 3-sentence sliding windows (evidence is often one sentence in a long passage), and all cited passages **combined** (for claims that join two sources). A claim with no citation is checked against every source.
2. Run NLI on all (premise, claim) pairs in batches.
3. Verdict from the best entailment and worst contradiction:

| Verdict | Rule (defaults, configurable) | UI |
|---|---|---|
| supported | entailment ≥ 0.70 | ✓ green |
| contradicted | contradiction ≥ 0.70 (and not supported) | ✕ red underline |
| partially_supported | entailment ≥ 0.35 | ~ amber underline |
| unsupported | otherwise | ! red underline |
| not_checked | NLI model unavailable | ? grey |

4. **Faithfulness score** of the answer = mean of claim scores (supported 1, partial 0.5, others 0).
5. The best (or most contradicting) premise is stored as **evidence** and shown next to the verdict.

### "I don't have enough information"
Three layers let the system refuse instead of guessing: the relevance gate (no relevant passage → no generation), the prompt rule (`insufficient_information` status), and verification (unsupported claims are visibly flagged).

### Why not ask the LLM to check itself?
"LLM-as-judge" is useful (RAGAS uses it in Module 9) but it is the same kind of model that hallucinated, costs another API call, and is non-deterministic. A small dedicated NLI model is free, local, deterministic and independent of the generator. Module 9 compares both.

## Measured behaviour (real NLI model)
Passage: *"The Transformer model was trained on 8 NVIDIA P100 GPUs for 3.5 days. It achieved a BLEU score of 28.4 on the WMT 2014 English-to-German translation task, improving over the best previous results by more than 2 BLEU."*

| Claim | Expected | Verdict | Confidence |
|---|---|---|---|
| The model was trained on 8 P100 GPUs. | supported | supported | 0.997 |
| Training took about three and a half days. *(paraphrase)* | supported | supported | 0.999 |
| The model reached 28.4 BLEU on English-to-German translation. | supported | supported | 0.997 |
| The model was trained on TPUs. | contradicted | contradicted | 0.999 |
| The model achieved a BLEU score of 35.0. *(changed number)* | contradicted | contradicted | 0.998 |
| The authors released the code under the MIT license. | unsupported | unsupported | 0.001 |

6/6 correct on this example, on CPU (first run includes ~1.5 min model download/load; afterwards a few hundred ms per claim). Six hand-picked claims prove nothing statistically — Module 9 measures detection precision/recall on a labelled set.

## Limitations — say these clearly
- NLI models struggle with **numbers and arithmetic** ("improved by more than 2 BLEU" vs "improved by 3 BLEU"), long multi-step reasoning, and heavy paraphrase.
- English-only verifier: Telugu answers are verified through their English claims.
- A claim can be "supported" by a passage that itself is wrong — verification checks faithfulness to the documents, not truth in the world.
- Thresholds trade false alarms against missed hallucinations; Module 9 measures this trade-off.
- **This system does not detect all hallucinations.** The UI says so next to every evidence check.

## Files
| File | Purpose |
|---|---|
| `app/services/verification/nli.py` | Loads the NLI model, batched inference, label mapping |
| `app/services/verification/verifier.py` | Premise construction, verdicts, evidence, confidence |
| `app/services/rag/pipeline.py` | Calls verification; computes faithfulness |
| `app/models/conversation.py` (`Claim`) | Stores verdict, confidence, evidence per claim |
| `frontend/src/components/chat/AssistantMessage.jsx` | Underlines, badges, evidence links, honest summary |
| `frontend/src/utils/verification.js` | Verdict labels and explanations |

## Configuration
```
NLI_MODEL=MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli
SUPPORTED_THRESHOLD=0.7
PARTIAL_THRESHOLD=0.35
CONTRADICTION_THRESHOLD=0.7
```

## Test
```powershell
pytest tests/test_chat.py -k "unsupported or grounded" -v
```

## Interview questions
1. What is a hallucination in RAG, and why does RAG not eliminate it?
2. Explain NLI. Why is it suitable for claim verification?
3. Why split answers into claims?
4. How do you choose the verification thresholds? What happens if you raise them?
5. Why use a separate NLI model instead of asking the LLM to verify itself?
6. What kinds of hallucinations will your system miss?
7. How would you measure the accuracy of the hallucination detector itself?
