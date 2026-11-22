# Hallucination detector evaluation – verifier_2026-11-21T21-51-48

31 labelled claims ({'supported': 14, 'contradicted': 9, 'unsupported': 8}). Positive class = hallucination (gold label unsupported or contradicted).

- Precision: **0.944**  (flagged claims that really were hallucinations)
- Recall: **1.000**  (hallucinations that were caught)
- F1: **0.971**, accuracy 0.968
- Exact 3-class verdict accuracy: **0.903**

## Confusion matrix (rows = gold, columns = predicted)

| gold | supported | partially_supported | unsupported | contradicted | not_checked |
|---|---|---|---|---|---|
| supported | 13 | 0 | 1 | 0 | 0 |
| unsupported | 0 | 0 | 7 | 1 | 0 |
| contradicted | 0 | 0 | 1 | 8 | 0 |

## Errors

| id | gold | predicted | confidence | claim |
|---|---|---|---|---|
| C11 | contradicted | unsupported | 0.151 | The big Transformer reached 31.2 BLEU on English-to-German translation. |
| C17 | supported | unsupported | 0.075 | Mawsynram receives more rain than Mumbai. |
| C28 | unsupported | contradicted | 0.937 | Marie Antoinette was executed in October 1793. |

