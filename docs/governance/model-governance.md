# Model Governance

Real model/version registry for the Corporate Knowledge Assistant — every
value below is the one actually configured in code as of this document's
date (2026-08-25), cross-checked against `src/cka/core/config.py::Settings`
and the modules cited, not copied from the roadmap's illustrative names.

## Registry

| Role | Model / Version | Configured in | Notes |
|---|---|---|---|
| Generation LLM | `claude-sonnet-5` | `Settings.anthropic_model` (`ANTHROPIC_MODEL` env var) | Default; no key set in any environment through Block 4 — see "Fallback behavior" below |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` | `Settings.embedding_model_name` | 384-dim, pinned in the DB schema (`infrastructure/database/models.py::EMBEDDING_DIMENSION`) — changing this model requires a migration, not just a config change |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` | `Settings.reranker_model_name` | Cross-encoder, reranks the hybrid-retrieval candidate set (`hybrid_candidate_k=20` down to `retrieval_top_k=5`) |
| System prompt | `PROMPT_VERSION = "v1"` | `src/cka/application/rag/prompt_builder.py` | Added in this sprint so prompt changes are trackable — every SYSTEM_PROMPT change to date has been `v1` (no revisions yet) |
| LLM-as-judge | same `claude-sonnet-5` | `infrastructure/llm/anthropic_judge.py` | Faithfulness/answer-relevance scoring; same real-key dependency as generation |

## Fallback behavior (real, not hypothetical)

No `ANTHROPIC_API_KEY` has been set in any environment across Blocks 1–4 of
this exercise. When unset, `/ask` runs on `FakeLLMProvider`
(`infrastructure/llm/fake_llm_provider.py`) instead of a real model call —
verified live in Block 4: `curl -X POST /ask ...` returns
`"answer":"ANTHROPIC_API_KEY not configured — no real answer available."`
with `"grounded":false`. This is why the evaluation gate's
generation-quality metrics (`citation_accuracy`, `faithfulness`,
`answer_relevance`) are threaded through `real_llm_used` in
`scripts/evaluate.py` and only enforced when a real key is present (see
ADR-010) — `.env.production.example` requires `ANTHROPIC_API_KEY` with no
default, specifically so production cannot silently run on the fallback.

## Known real constraint: no `temperature` parameter

The installed `anthropic` SDK (1.0.0) does not expose `temperature` as a
`messages.create` parameter the way earlier SDK versions did.
`Settings.llm_temperature` (default `0.0`) exists in config but is
currently **not** passed to the real API call — documented in
`infrastructure/llm/anthropic_provider.py` at the call site, not silently
dropped. Reviewed if/when the SDK reintroduces the parameter.

## Change process

Any change to the values in the Registry table above must:

1. Update the relevant `Settings` field (or `PROMPT_VERSION`), never hardcode
   a model name elsewhere.
2. Re-run `scripts/evaluate.py` against the real golden dataset before
   merging — a model/prompt change is a quality-affecting change, gated the
   same way as a code change (ADR-010).
3. Update this document in the same change, so the registry never drifts
   from what's actually configured.
4. For the embedding model specifically: a change requires a re-embedding
   migration (dimension or embedding-space change invalidates existing
   vectors) — not a drop-in config swap.
