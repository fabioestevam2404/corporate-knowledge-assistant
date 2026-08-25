# Data Flow

Real request/data flow for the system's two core operations, matching the
actual OpenTelemetry span tree captured live in Block 3
(`docs/release-gate/PROGRESS.md`, real Jaeger trace, 9 real spans).

## `POST /ask` — real span tree, as captured from a live trace

```
POST /ask                              (root span)
 ├─ http receive
 ├─ hybrid_retrieval        pgvector cosine + Postgres full-text (tsvector/
 │                          GIN), fused via Reciprocal Rank Fusion (k=60),
 │                          filtered by the caller's real AccessScope
 │                          BEFORE reranking — an unauthorized chunk never
 │                          reaches the reranker or the LLM
 ├─ reranking                cross-encoder/ms-marco-MiniLM-L-6-v2 reorders
 │                          the hybrid candidate set (hybrid_candidate_k=20)
 │                          down to retrieval_top_k=5
 ├─ context_building         PromptBuilder wraps retrieved chunks in
 │                          <UNTRUSTED_DOCUMENTS>, the query in
 │                          <USER_QUERY> — the prompt-injection defense
 │                          from ADR-009: document content is data, never
 │                          treated as instructions
 ├─ llm_generation            real Anthropic call (claude-sonnet-5,
 │                          tool-use forcing structured {answer, citations}
 │                          output) — or FakeLLMProvider if no
 │                          ANTHROPIC_API_KEY, see model-governance.md
 ├─ citation_validation       every citation in the model's response is
 │                          checked against the chunk_ids actually
 │                          retrieved — a citation to a chunk that was
 │                          never in context is dropped, not trusted
 └─ http send
```

Every span above is real (OpenTelemetry SDK + manual instrumentation, see
ADR-011) — this is not an idealized diagram, it is the shape captured from
an actual `/ask` call against the live stack.

## Document ingestion flow (`POST /documents`)

```
POST /documents (multipart)
 └─ IngestDocument (application layer)
     ├─ validates source_id against data/sources/registry.yaml
     │  (SourceNotFoundError/SourceNotApprovedError → 400 if not approved)
     └─ ProcessDocument
         ├─ loader (PDF page-aware, or plain text)
         ├─ chunking (recursive character, tiktoken cl100k_base,
         │  chunk_size=1200, chunk_overlap=200)
         ├─ embedding (all-MiniLM-L6-v2, 384-dim)
         └─ SqlAlchemyDocumentRepository.save()
            (flushes internally — see the real flush-ordering defect
            fixed in Block 3, PROGRESS.md)
```

## Authorization checkpoint — where `AccessScope` actually filters

`AccessScope` is applied inside the hybrid-retrieval query itself
(`infrastructure/retrieval/`), not as a post-processing filter on results
already fetched. This is the real mechanism behind the roadmap's headline
ACL test (Release Gate §7): an EMPLOYEE-role query about a
`management`-classified source returns **zero rows from that source at the
database query level** — the LLM never sees it, so there's nothing to
accidentally leak through generation even if retrieval or reranking had a
bug elsewhere. Verified for real in
`tests/security/test_document_acl.py` (Block 3).
