# Development Build Plan (plan.md)

## Current Status: [x] BC6 Completed
**Next Build Cycle:** BC7 — Retrieval: Vector Search, Lexical Search, and Hybrid Fusion

---

## Completed Cycles
- [x] **BC0 — Verify Starter Repo Integrity**
- [x] **BC1 — Scaffolding & Multi-Agent Orchestration Commit**
- [x] **BC2 — Database Schema & Alembic Migrations**
- [x] **BC3 — PDF Upload Endpoint & Validation Limits**
- [x] **BC4 — Structure Detection & Page Rasterization**
- [x] **BC5 — Chunking & Embeddings**
- [x] **BC6 — Ingestion Agent: Bounded Tool-Use Loop**

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

**Status:** [ ] Planned

### Objective
Build the retrieval layer that turns indexed `chunks` rows into ranked context candidates for BC8 reranking and the future chat endpoint.

### Implementation Plan
- [ ] Add `backend/app/retrieval/` with typed retrieval models for `Candidate`, `HybridSearchResult`, lexical rank, vector rank, fused score, document metadata, page number, and section path.
- [ ] Reuse the BC5 embedding client pattern to embed the incoming query with the same configured embedding model and dimension guard used for document chunks.
- [ ] Implement `vector_search` using SQLAlchemy `AsyncSession` raw SQL against pgvector cosine distance (`embedding <=> :query_embedding`) with a transaction-local `SET LOCAL hnsw.ef_search = :value` before the query.
- [ ] Implement `lexical_search` over generated `chunks.content_tsv` using Postgres full-text search and `ts_rank_cd`, filtered to non-deleted documents and optional document IDs when provided.
- [ ] Implement `reciprocal_rank_fusion` in Python with `RRF_K=60`, keeping the fused value as an ordering signal only, never as confidence.
- [ ] Implement `hybrid_search` that merges vector and lexical candidates, returns the top `RETRIEVAL_TOP_K`, and supports a vector-only branch for deterministic comparison.
- [ ] Add settings for `RETRIEVAL_TOP_K`, `HYBRID_SEARCH_ENABLED`, `RRF_K`, and `HNSW_EF_SEARCH`.
- [ ] Add tests for literal RRF scoring, vector-only retrieval, lexical rare-term retrieval, hybrid ordering, deleted-document exclusion, query embedding dimension mismatch, and transaction-local HNSW configuration.

### Inferred Repo-Specific Notes
- The architecture plan references raw `asyncpg`, but the implemented backend already uses SQLAlchemy async sessions. BC7 should continue that local pattern and use `text()` SQL for pgvector/full-text operations.
- The `chunks.content_tsv` column is database-generated, so BC7 should only read it; application code must not write or recalculate it.
- Query embedding should be injected in tests via a fake embedding client, matching BC5's deterministic approach and avoiding provider network calls.

### Definition of Done
- [ ] `hybrid_search` returns stable candidate objects with chunk/document/page/section metadata.
- [ ] Vector and lexical paths are independently testable.
- [ ] RRF has exact-value tests and is documented as fusion-only.
- [ ] HNSW `ef_search` is set per call and cannot leak through pooled connections.
- [ ] `tests-README.md` and `.codex/pull_requests/PR_BC7.md` are updated with verification output.

---

## BC8 — Reranking: Local Cross-Encoder Confidence Signal

**Status:** [ ] Planned

### Objective
Add a reranking layer that consumes BC7's top retrieval candidates and produces a bounded `top_relevance_score` for future Retrieval Agent confidence gating.

### Implementation Plan
- [ ] Add `backend/app/retrieval/rerank.py` with one public `rerank(query, candidates, top_n)` entry point.
- [ ] Add typed result models carrying ranked chunks, raw/sigmoid scores, `top_relevance_score`, and timing metadata.
- [ ] Load the local cross-encoder once at app startup or lazy-load it behind a small singleton so tests can inject a fake reranker without downloading model weights.
- [ ] Convert cross-encoder logits to confidence with sigmoid, guaranteeing `top_relevance_score` is in `[0, 1]`.
- [ ] Return `0.0` for empty candidate lists instead of raising.
- [ ] Add `RERANK_TOP_N`, `RERANKER_MODEL`, and optional `RERANK_PROVIDER` settings.
- [ ] Keep a hosted reranker escape hatch behind the same input/output contract, but default to local deterministic/testable behavior.
- [ ] Wrap rerank calls with `@traced(agent_name="retrieval_agent")` once BC7 retrieval tracing context is available.
- [ ] Add tests for empty input, score bounds, ordering by score, strategy selection, fake local-reranker injection, and a logged 20-candidate timing check.

### Inferred Repo-Specific Notes
- Avoid making the deterministic backend suite depend on a model download. Unit tests should use a fake cross-encoder object and reserve real model timing for optional/local verification.
- BC8 should not gate retrieval. It only produces the bounded score that BC9's Retrieval Agent will use.
- RRF scores from BC7 and reranker confidence from BC8 must remain separate fields to avoid repeating the architecture's known range-mismatch bug.

### Definition of Done
- [ ] Reranking is implemented behind a stable typed interface.
- [ ] `top_relevance_score` is bounded and tested, including empty input.
- [ ] Local and hosted strategy selection is deterministic under tests.
- [ ] Model loading is not repeated per request.
- [ ] `tests-README.md` and `.codex/pull_requests/PR_BC8.md` are updated with verification output.
