# Evaluation Results

Real output of `uv run python scripts/evaluate.py`, from
`reports/evaluation_latest.json`, re-run as part of Sprint 15's final
full-suite pass (`generated_at: 2026-08-25T19:42:44Z`) — the same
methodology and numbers as Block 3's original run, reproduced against the
real sample corpus after it was restored following the real data-loss
defect documented in `docs/release-gate/PROGRESS.md` (Sprint 15).

```json
{
  "dataset": "golden-v1-block3",
  "real_llm_used": false,
  "retrieval": {
    "recall_at_5": 1.0,
    "precision_at_5": 0.2,
    "mrr": 1.0,
    "ndcg_at_5": 1.0,
    "case_count": 8
  },
  "generation": {
    "citation_accuracy": 0.0,
    "citation_completeness": 0.5,
    "abstention_accuracy": 0.5,
    "case_count": 6,
    "faithfulness": null,
    "answer_relevance": null,
    "judged_case_count": 0
  },
  "adversarial": {
    "resistance_rate": 1.0,
    "abstention_accuracy": 1.0,
    "case_count": 4,
    "failures": []
  }
}
```

**Gate result**: passed (`exit code 0`) — `recall_at_5 = 1.0` clears the
`0.70` floor; generation-quality thresholds were not checked because
`real_llm_used: false` (no `ANTHROPIC_API_KEY` configured), which is the
intended, honest behavior of the gate (see `evaluation.md`), not a silent
pass.

## Reading these numbers honestly

- **Retrieval metrics (perfect 1.0 across recall/MRR/NDCG) are real, but
  against a small, curated 8-case dataset over a 5-document corpus.** A
  perfect score here demonstrates the retrieval pipeline works correctly
  on the cases it was tested against — it is not evidence of production-
  scale retrieval quality against a much larger, noisier real corpus.
- **`citation_accuracy: 0.0` looks alarming but is expected**:
  `FakeLLMProvider` never emits citations by design (it's a fallback, not a
  generation model), so there is nothing for the deterministic
  citation-accuracy check to score positively. This is why the gate does
  not enforce this metric when `real_llm_used: false` — treating a `0.0`
  here as a real generation-quality failure would be a misread of what was
  actually measured.
- **`faithfulness`/`answer_relevance`: `null`, `judged_case_count: 0`** —
  the LLM-as-judge path has never run against a real model in this project.
  This is the most significant real gap in the evaluation evidence: the
  generation-quality half of the gate is implemented and unit-tested, but
  has zero real-world evidence behind it. Anyone running this system with a
  real `ANTHROPIC_API_KEY` should re-run `scripts/evaluate.py` and expect
  materially different (and, for the first time, real) generation-quality
  numbers.
- **Adversarial resistance (1.0, 4 real cases)** is real and meaningful
  even without an LLM key — the adversarial cases test retrieval-layer and
  application-layer defenses (prompt-injection document handling,
  out-of-scope query abstention), which don't depend on generation quality.
