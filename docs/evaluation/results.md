# Evaluation Results

Real output of `uv run python scripts/evaluate.py`, from
`reports/evaluation_latest.json` (`generated_at: 2026-08-26T00:11:32Z`) —
the first real run of this project's entire history against a real
`ANTHROPIC_API_KEY`, configured post-`v1.0.0` tag. See
`docs/release-gate/PROGRESS.md` ("Post-release: a real ANTHROPIC_API_KEY
was configured") for the four real defects this run surfaced and fixed,
and for why one real gate check still honestly fails.

```json
{
  "dataset": "golden-v1-block3",
  "real_llm_used": true,
  "retrieval": {
    "recall_at_5": 1.0,
    "precision_at_5": 0.2,
    "mrr": 1.0,
    "ndcg_at_5": 1.0,
    "case_count": 8
  },
  "generation": {
    "citation_accuracy": 0.8333333333333334,
    "citation_completeness": 0.8333333333333334,
    "abstention_accuracy": 0.8333333333333334,
    "case_count": 6,
    "faithfulness": 1.0,
    "answer_relevance": 1.0,
    "judged_case_count": 2
  },
  "adversarial": {
    "resistance_rate": 1.0,
    "abstention_accuracy": 1.0,
    "case_count": 4,
    "failures": []
  }
}
```

**Gate result**: **FAILED** — `citation_accuracy 0.8333... < 0.9`. Reported
exactly as measured, not smoothed over: a failing gate for a real,
understood reason is more valuable evidence than a passing one that was
quietly tuned to pass.

## Reading these numbers honestly

- **Retrieval metrics (perfect 1.0)** are real, but against a small,
  curated 8-case dataset over a 5-document corpus — evidence the pipeline
  works on the cases tested, not evidence of production-scale quality.
- **`faithfulness: 1.0`, `answer_relevance: 1.0`** are real LLM-as-judge
  scores, for the first time ever in this project (`judged_case_count: 2`
  — only cases where the model actually answered, per ADR-010's design,
  get judged). Getting a perfect score from only 2 judged cases is a small
  sample, not a broad quality claim.
- **`citation_accuracy: 0.8333...` is a real, correct gate failure.** Of
  the 3 "should answer" golden cases, 2 are answered and cited correctly;
  the third (`"What are the password length requirements?"`) correctly
  retrieves the right document as the #1 ranked result
  (`recall_at_5` stays a real `1.0`) but the cross-encoder reranker's
  absolute confidence for that specific pairing is genuinely low
  (`0.0074` on a 0-1 scale, against `0.99+` for the two working cases),
  so the system abstains rather than answers. This was deliberately
  **not** fixed by lowering the qualifying-evidence threshold — doing so
  would also admit genuinely irrelevant results scored just as low
  elsewhere, weakening the exact hallucination-prevention gate the
  threshold exists for. See `PROGRESS.md` for the full real score
  comparison table and reasoning.
- **Adversarial resistance (`1.0`, real model)**: the real model handled
  the prompt-injection payload correctly — explicitly refusing and
  explaining why, in its own words. The evaluation harness's own check for
  this used to be a naive substring match that flagged that explanation as
  a "leak" (because the refusal quotes the injected marker while declining
  to comply) — a real bug in the *test*, not the model, found and fixed
  the first time this ever ran for real (see `PROGRESS.md`).

## What changed since the pre-key run

Before a real key existed, this document reported `citation_accuracy: 0.0`
and `faithfulness: null` — both were artifacts of running on
`FakeLLMProvider` (expected, documented, not a defect) *and*, it turned
out once a real model was actually used, of two additional harness bugs
(an evidence placeholder passed to the judge, and citation_accuracy not
handling correct abstention the same way citation_completeness already
did) that had been hiding behind the fact that no real generation had ever
been evaluated. Real validation surfaced real bugs that a fake-only
evaluation path never could have.
