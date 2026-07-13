# Development Build Plan (plan.md)

## Current Status: [x] BC5 Completed
**Next Build Cycle:** BC6 — RAG Retrieval, Hybrid Search, Reranking Preparation

---

## Completed Cycles
- [x] **BC0 — Verify Starter Repo Integrity**
- [x] **BC1 — Scaffolding & Multi-Agent Orchestration Commit**
- [x] **BC2 — Database Schema & Alembic Migrations**
- [x] **BC3 — PDF Upload Endpoint & Validation Limits**
- [x] **BC4 — Structure Detection & Page Rasterization**
- [x] **BC5 — Chunking & Embeddings**

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

## BC6 — RAG Retrieval, Hybrid Search, Reranking Preparation

**Status:** [ ] Planned

### Objectives
Build the retrieval layer that turns indexed chunks into ranked context for the future chat endpoint.

### Implementation Plan
- [ ] Implement lexical search over `chunks.content_tsv` with `websearch_to_tsquery`.
- [ ] Implement vector search over `chunks.embedding` using pgvector cosine distance and transaction-local `SET LOCAL hnsw.ef_search`.
- [ ] Merge lexical and vector candidates with Reciprocal Rank Fusion (`RRF_K=60`) strictly as candidate ordering, not confidence.
- [ ] Add retrieval result models carrying `chunk_id`, document metadata, page number, section path, lexical rank, vector rank, and fused score.
- [ ] Prepare reranker interface and deterministic fallback wiring without enabling BC8 confidence gating yet.
- [ ] Add retrieval tests for lexical-only, vector-only, hybrid fusion ordering, deleted-document cascade behavior, and per-transaction HNSW setting.
- [ ] Update `tests-README.md` and draft `.codex/pull_requests/PR_BC6.md` after verification.
