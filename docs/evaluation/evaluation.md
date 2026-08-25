# Evaluation Methodology

Real methodology implemented in `src/cka/evaluation/` and run via
`scripts/evaluate.py` — see `results.md` for the actual numbers this
produces against the real corpus.

## Golden Dataset

`data/evaluation/*.yaml` — 18 real, hand-authored cases across three
categories, run against the real 5-document sample corpus
(`data/sources/registry.yaml`), not a mocked or hypothetical dataset:

- **Retrieval cases**: query + expected relevant `source_id`s, used to
  compute Recall@5, Precision@5, MRR, NDCG@5.
- **Generation cases**: query + expected citation behavior, used to compute
  citation accuracy/completeness and abstention accuracy.
- **Adversarial cases**: prompt-injection and out-of-scope queries, used to
  compute resistance rate (does the system correctly refuse/ignore the
  injected instruction) and abstention accuracy.

## Deterministic metrics (no LLM required)

Pure functions in `src/cka/evaluation/retrieval_metrics.py` — always
computed, regardless of whether a real LLM key is configured:

- **Recall@5 / Precision@5**: standard IR metrics against the expected
  relevant sources.
- **MRR** (Mean Reciprocal Rank): position of the first relevant result.
- **NDCG@5**: rank-quality metric, bounded [0,1] — a real defect (computed
  value of 1.158, impossible under that bound) was found and fixed in
  Block 3 by deduplicating retrieved chunks to unique `source_id`s before
  scoring (see `docs/release-gate/PROGRESS.md`).

## LLM-dependent metrics (require `ANTHROPIC_API_KEY`)

- **Citation accuracy / completeness**: deterministic checks against which
  `chunk_id`s the model actually cited vs. which were retrieved — not
  itself LLM-judged, but only meaningful when a real model (not
  `FakeLLMProvider`) produced the answer being checked.
- **Faithfulness / Answer relevance**: real LLM-as-judge
  (`infrastructure/llm/anthropic_judge.py`), same `claude-sonnet-5` model,
  a second real API call scoring the first one's output.

## The gate (`scripts/evaluate.py`, real, run for real)

`check_gate()` always enforces `recall_at_5 >= Settings.evaluation_min_recall_at_5`
(default 0.70). Generation-quality thresholds
(`citation_accuracy`, `faithfulness`, `answer_relevance`) are only enforced
when `real_llm_used: true` — a real defect fix from Block 3: the original
gate failed permanently for anyone without a real Anthropic key, since
`FakeLLMProvider` never cites anything by design. `real_llm_used` is
threaded through the whole evaluation run so the gate's behavior is honest
about what it actually checked.

## What this project has never exercised

No environment across Blocks 1–4 has run with a real `ANTHROPIC_API_KEY` —
the LLM-as-judge path and the citation-accuracy-in-anger path are
implemented and unit-tested against `FakeLLMProvider`/mocked judge
responses, but never run against the real Anthropic API. This is stated
plainly in `results.md`, not implied to be more validated than it is.
