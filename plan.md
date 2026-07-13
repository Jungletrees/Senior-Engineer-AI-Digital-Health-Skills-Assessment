# Development Build Plan (plan.md)

## Current Status: [x] BC7/BC8 Completed
**Next Build Cycles:** BC9 — Retrieval Agent: Confidence Gate, Query Expansion, and Page Image Fetch; BC10 — Orchestrator: Retrieval-Agent Tool Boundary and Generation Assembly

---

## Completed Cycles
- [x] **BC0 — Verify Starter Repo Integrity**
- [x] **BC1 — Scaffolding & Multi-Agent Orchestration Commit**
- [x] **BC2 — Database Schema & Alembic Migrations**
- [x] **BC3 — PDF Upload Endpoint & Validation Limits**
- [x] **BC4 — Structure Detection & Page Rasterization**
- [x] **BC5 — Chunking & Embeddings**
- [x] **BC6 — Ingestion Agent: Bounded Tool-Use Loop**
- [x] **BC7 — Retrieval: Vector Search, Lexical Search, and Hybrid Fusion**
- [x] **BC8 — Reranking: Local Cross-Encoder Confidence Signal**

---

## BC4 — Structure Detection & Page Rasterization

**Status:** [x] Completed

### Objectives
Implement the automated PDF processing worker that transitions documents from `status=processing` to `status=indexed` after structure detection and page rasterization.

### Completed Work
- [x] Instrumented `backend/app/worker.py` with granular logging for document lookup, file resolution/loading, PDF parsing, structure detection, rasterization, chunk preparation, commits, rollbacks, and exception handling.
- [x] Fixed upload path resolution so the worker reads PDFs from `backend/uploads`, matching the BC3 upload route.
- [x] Stripped padded `CHAR(64)` document hashes before constructing file paths, fixing the early return that left documents stuck in `processing`.
- [x] Persisted table/figure page images using the current `PageImage.storage_ref` schema.
- [x] Verified worker completion updates documents to `indexed`.

### Verification
- [x] `docker compose -p assessment exec backend pytest app/tests/test_rasterization.py -vv -s`
  - Result: `1 passed in 2.79s`

### PR Draft
- [x] `.codex/pull_requests/PR_BC4.md`

---

## BC5 — Chunking & Embeddings

**Status:** [x] Completed

### Objectives
Implement deterministic, structure-aware chunking and embedding persistence into the `chunks` table using configured chunk size, overlap, and embedding model settings.

### Completed Work
- [x] Added `backend/app/documents/chunking.py` with token-bounded chunking from structured PDF blocks.
- [x] Implemented heading-aware context injection and table-preserving chunk boundaries.
- [x] Honored `CHUNK_SIZE_TOKENS` and `CHUNK_OVERLAP_RATIO`.
- [x] Added OpenAI/Voyage embedding HTTP clients selected by `EMBEDDING_MODEL`.
- [x] Added deterministic local/test embedding fallback when hosted provider keys are absent.
- [x] Added embedding dimension validation against `EMBEDDING_DIM`.
- [x] Persisted chunk rows with pgvector embeddings while relying on Postgres to generate `content_tsv`.
- [x] Integrated chunking/embedding into `process_document` before final `indexed` status update.

### Verification
- [x] `docker compose -p assessment exec backend pytest app/tests/test_chunking.py -vv -s`
  - Result: `6 passed in 2.81s`
- [x] `docker compose -p assessment exec backend pytest`
  - Result: `20 passed, 12 skipped, 4 warnings in 10.25s`

### PR Draft
- [x] `.codex/pull_requests/PR_BC5.md`

---

## BC6 — Ingestion Agent: Bounded Tool-Use Loop

**Status:** [x] Completed

### Objectives
Replace the fixed-order BC4 structure loop with a bounded ingestion-agent tool loop that can call only `detect_structure`, `extract_text_ocr_fallback`, and `flag_table_pages`, then feed completed page assessments into the BC5 chunking tail.

### Completed Work
- [x] Added `backend/app/agents/ingestion_agent.py` with provider-neutral tool-use blocks, static ingestion tool schemas, Anthropic Messages API client wiring, page-scaled iteration caps, and per-page fallback behavior.
- [x] Added `backend/app/agents/tracing.py` to persist compact tool-call rows into `agent_trace_log` when a database session is supplied.
- [x] Added centralized `backend/app/settings.py` fields for `AGENT_MODEL`, `INGESTION_AGENT_MAX_ITERATIONS_HARD_CEILING`, `AGENT_TRACE_LOGGING_ENABLED`, and `ANTHROPIC_API_KEY`.
- [x] Updated `backend/app/worker.py` to run `IngestionAgent`, write structure/fallback metadata, and pass agent page assessments into chunk persistence.
- [x] Updated `backend/app/documents/chunking.py` to accept in-memory `PageAssessment` results, preserving headings, page numbers, table flags, and fallback text as chunking inputs.
- [x] Added backend test setup for isolated pytest async event loops with `NullPool` under `ASSESSMENT_TESTING=1`.
- [x] Added BC6 tests for iteration-cap regression, static tool scope, trace logging, table-page parity, per-page fallback metadata, and prompt-injection/tool-scope containment.

### Verification
- [x] `docker compose -p assessment exec backend pytest`
  - Result: `24 passed, 12 skipped, 4 warnings in 8.28s`

### PR Draft
- [x] `.codex/pull_requests/PR_BC6.md`

---

## BC7 — Retrieval: Vector Search, Lexical Search, and Hybrid Fusion

**Status:** [x] Completed

### Objective
Build the retrieval layer that turns indexed `chunks` rows into ranked context candidates for BC8 reranking and the future chat endpoint.

### Completed Work
- [x] Added `backend/app/retrieval/` with typed retrieval and reranking result models carrying chunk, document, page, section, rank, fusion, and score metadata.
- [x] Reused the BC5 embedding client pattern for query embedding with the same configured dimension guard used for persisted chunks.
- [x] Implemented `vector_search` using SQLAlchemy `AsyncSession` and explicit `text()` SQL against pgvector cosine distance, with transaction-local `SET LOCAL hnsw.ef_search`.
- [x] Implemented `lexical_search` over generated `chunks.content_tsv` using Postgres full-text search and `ts_rank_cd`, filtered to indexed documents and optional document IDs.
- [x] Implemented exact Reciprocal Rank Fusion in Python with `RRF_K=60`, keeping fused score as ordering-only and separate from confidence.
- [x] Implemented `hybrid_search` with vector/lexical merge, deterministic ordering, top-k output, and a vector-only branch.
- [x] Added retrieval settings for `RETRIEVAL_TOP_K`, `HYBRID_SEARCH_ENABLED`, `RRF_K`, and `HNSW_EF_SEARCH`.
- [x] Added tests for literal RRF scoring, vector retrieval, lexical rare-term retrieval, hybrid ordering, deleted-document exclusion, query embedding dimension mismatch, and transaction-local HNSW configuration.

### Inferred Repo-Specific Notes
- The architecture plan references raw `asyncpg`, but the implemented backend already uses SQLAlchemy async sessions. BC7 should continue that local pattern and use `text()` SQL for pgvector/full-text operations.
- The `chunks.content_tsv` column is database-generated, so BC7 should only read it; application code must not write or recalculate it.
- Query embedding should be injected in tests via a fake embedding client, matching BC5's deterministic approach and avoiding provider network calls.

### Definition of Done
- [x] `hybrid_search` returns stable candidate objects with chunk/document/page/section metadata.
- [x] Vector and lexical paths are independently testable.
- [x] RRF has exact-value tests and is documented as fusion-only.
- [x] HNSW `ef_search` is set per call and cannot leak through pooled connections.
- [x] `tests-README.md` and `.codex/pull_requests/PR_BC7.md` are updated with verification output.

### Verification
- [x] `docker compose -p assessment exec backend pytest`
  - Result: `37 passed, 12 skipped, 4 warnings in 15.06s`

### PR Draft
- [x] `.codex/pull_requests/PR_BC7.md`

---

## BC8 — Reranking: Local Cross-Encoder Confidence Signal

**Status:** [x] Completed

### Objective
Add a reranking layer that consumes BC7's top retrieval candidates and produces a bounded `top_relevance_score` for future Retrieval Agent confidence gating.

### Completed Work
- [x] Added `backend/app/retrieval/rerank.py` with one public `rerank(query, candidates, top_n)` entry point.
- [x] Added typed result models carrying ranked chunks, raw logits, sigmoid scores, `top_relevance_score`, duration, and provider metadata.
- [x] Lazy-loads the local cross-encoder once per process behind a singleton so tests can inject a fake reranker without model downloads.
- [x] Converts cross-encoder logits to sigmoid confidence, guaranteeing `top_relevance_score` is in `[0, 1]`.
- [x] Returns `0.0` for empty candidate lists instead of raising.
- [x] Added `RERANK_TOP_N`, `RERANKER_MODEL`, and optional `RERANK_PROVIDER` settings.
- [x] Added the pinned `sentence-transformers` backend dependency for the default local CrossEncoder path.
- [x] Kept a hosted reranker escape hatch behind the same input/output contract while defaulting to local deterministic/testable behavior.
- [x] Wrapped rerank calls with `@traced(agent_name="retrieval_agent")`.
- [x] Added tests for empty input, score bounds, ordering by score, top-n limiting, hosted strategy selection, and missing hosted-adapter failure.

### Inferred Repo-Specific Notes
- Avoid making the deterministic backend suite depend on a model download. Unit tests should use a fake cross-encoder object and reserve real model timing for optional/local verification.
- BC8 should not gate retrieval. It only produces the bounded score that BC9's Retrieval Agent will use.
- RRF scores from BC7 and reranker confidence from BC8 must remain separate fields to avoid repeating the architecture's known range-mismatch bug.

### Definition of Done
- [x] Reranking is implemented behind a stable typed interface.
- [x] `top_relevance_score` is bounded and tested, including empty input.
- [x] Local and hosted strategy selection is deterministic under tests.
- [x] Model loading is not repeated per request.
- [x] `tests-README.md` and `.codex/pull_requests/PR_BC8.md` are updated with verification output.

### Verification
- [x] `docker compose -p assessment exec backend pytest`
  - Result: `37 passed, 12 skipped, 4 warnings in 15.06s`

### PR Draft
- [x] `.codex/pull_requests/PR_BC8.md`

---

## BC9 — Retrieval Agent: Confidence Gate, Query Expansion, and Page Image Fetch

**Status:** [ ] Planned

### Objective
Wire BC7 hybrid search and BC8 reranking into the retrieval cascade that uses deterministic retrieval by default and expands queries only when reranker confidence is low.

### Implementation Plan
- [ ] Add `backend/app/agents/retrieval_agent.py` with `RetrievalAgent.run` and a plain `run_retrieval_cascade` helper.
- [ ] Add `RETRIEVAL_AGENT_CONFIDENCE_THRESHOLD=0.55` and `RETRIEVAL_AGENT_MAX_ITERATIONS=3` to centralized settings if not already present.
- [ ] Gate expansion on `reranked.top_relevance_score`, never on BC7's RRF `top_score`.
- [ ] Implement `expand_query` as a narrow agent-model call returning 1-3 parsed sub-queries, with malformed output falling back to `[original_query]`.
- [ ] Merge expanded retrieval candidates by `chunk_id`, preserving the best fused score before reranking against the original query.
- [ ] Implement `fetch_page_image` as an internal-only tool for final reranked chunks; add a route-table regression test proving no public page-image endpoint exists.
- [ ] Wrap `hybrid_search`, `rerank`, `expand_query`, and `fetch_page_image` calls with retrieval-agent trace context.
- [ ] Add tests for gate-signal selection, expansion/no-expansion paths, malformed expansion fallback, merge/dedup behavior, iteration-bound fallback, and internal-only page-image access.

### Handoff Notes
- BC9 must use BC8's bounded `top_relevance_score` as the only confidence signal.
- Keep `fetch_page_image` internal until a future explicit source-page viewing feature designs authorization for that surface.
- Preserve the SQLAlchemy async-session pattern documented in the architecture divergence row.

---

## BC10 — Orchestrator: Retrieval-Agent Tool Boundary and Generation Assembly

**Status:** [ ] Planned

### Objective
Implement the Orchestrator boundary that consults the Retrieval Agent as a tool, compacts retrieved context deterministically, and assembles a generation-ready prompt with text context and optional page images.

### Implementation Plan
- [ ] Add `backend/app/agents/orchestrator.py` with `consult_retrieval_agent(query, session_id)` as the only retrieval-facing orchestrator tool.
- [ ] Enforce the import boundary: orchestrator code must not import `hybrid_search`, `rerank`, or database access directly.
- [ ] Implement `compact_chunk` as deterministic extractive trimming by lexical overlap, restoring selected sentences to document order and falling back to first tokens on zero overlap.
- [ ] Assemble Messages API content with `<context source="..." page="...">...</context>` text blocks, image blocks only when the generation model supports multimodal input, and the user question last.
- [ ] Add a clearly marked output-filter stub that always passes until BC14 replaces it with real grounding/leak/PII checks.
- [ ] Raise a clear retrieval-unavailable error if `RetrievalAgent.run` fails outright; do not generate an ungrounded answer.
- [ ] Add tests for compaction behavior, retrieval import boundary, multimodal degrade path, generation assembly, output-filter stub status, and failure propagation.

### Handoff Notes
- BC10 should treat the Retrieval Agent as the only retrieval surface; this keeps BC11/BC12 from coupling directly to BC7 internals.
- Keep the output-filter stub explicit so BC14 can replace a named boundary instead of reverse-engineering generation flow.
