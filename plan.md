# Development Build Plan (plan.md)

## Current Status: [ ] BC12/BC13/BC14/BC15 Implemented - Backend Image Verification Blocked
**Active Build Cycle:** BC12-BC15 - Chat, Documents UI, Guardrails, Auth, and Rate Limiting

---

## Completed Cycles
- [x] **BC0 - Verify Starter Repo Integrity**
- [x] **BC1 - Scaffolding & Multi-Agent Orchestration Commit**
- [x] **BC2 - Database Schema & Alembic Migrations**
- [x] **BC3 - PDF Upload Endpoint & Validation Limits**
- [x] **BC4 - Structure Detection & Page Rasterization**
- [x] **BC5 - Chunking & Embeddings**
- [x] **BC6 - Ingestion Agent: Bounded Tool-Use Loop**
- [x] **BC7 - Retrieval: Vector Search, Lexical Search, and Hybrid Fusion**
- [x] **BC8 - Reranking: Local Cross-Encoder Confidence Signal**
- [x] **BC9 - Retrieval Agent: Confidence Gate, Query Expansion, and Page Image Fetch**
- [x] **BC10 - Orchestrator: Retrieval-Agent Tool Boundary and Generation Assembly**
- [x] **BC11 - Exact/Semantic Cache and Cache Hygiene Scheduler**

---

## BC9 - Retrieval Agent: Confidence Gate, Query Expansion, and Page Image Fetch

**Status:** [x] Completed

### Objective
Wire BC7 hybrid search and BC8 reranking into a bounded Retrieval Agent cascade that uses deterministic retrieval by default and expands queries only when reranker confidence is low.

### Completed Work
- [x] Added `backend/app/agents/retrieval_agent.py` with `RetrievalAgent.run` and `run_retrieval_cascade`.
- [x] Added `backend/app/retrieval/expand_query.py` with strict JSON/Pydantic parsing and safe fallback to `[original_query]`.
- [x] Added `backend/app/retrieval/fetch_page_image.py` as an internal-only tool for final reranked chunks.
- [x] Extended `backend/app/retrieval/models.py` with typed expansion, page-image, and Retrieval Agent result models.
- [x] Added retrieval-agent settings for confidence threshold and max iterations.
- [x] Ensured the expansion gate uses `reranked.top_relevance_score`, never raw RRF `top_score`.
- [x] Added trace-context forwarding where tools support tracing.

### Verification
- [x] `docker compose -p assessment exec backend pytest app/tests/test_retrieval_agent.py -vv`
  - Result: `8 passed in 8.35s`

### PR Draft
- [x] `.codex/pull_requests/PR_BC9.md`

---

## BC10 - Orchestrator: Retrieval-Agent Tool Boundary and Generation Assembly

**Status:** [x] Completed

### Objective
Implement the Orchestrator boundary that consults the Retrieval Agent as its only retrieval surface, compacts retrieved context deterministically, and assembles a generation-ready payload with optional image blocks.

### Completed Work
- [x] Added `backend/app/agents/orchestrator.py` with `consult_retrieval_agent`, `assemble_generation_payload`, and `RetrievalUnavailableError`.
- [x] Added deterministic `compact_chunk` in `backend/app/retrieval/compaction.py`.
- [x] Assembled stable system prefix, `<context source="..." page="...">...</context>` blocks, optional image blocks for multimodal models, and the user question last.
- [x] Added prompt-cache control integration on the stable system block.
- [x] Added explicit output-filter stub comment for BC14 replacement.
- [x] Added static import-boundary coverage proving the Orchestrator does not import retrieval internals or database access directly.

### Verification
- [x] `docker compose -p assessment exec backend pytest app/tests/test_orchestrator.py -vv`
  - Result: `9 passed in 0.82s`

### PR Draft
- [x] `.codex/pull_requests/PR_BC10.md`

---

## BC11 - Exact/Semantic Cache and Cache Hygiene Scheduler

**Status:** [x] Completed

### Objective
Implement exact-cache lookup/write, semantic-cache lookup/write, prompt-cache control, and a lightweight cache hygiene scheduler for TTL expiry, semantic LRU cap enforcement, and document-deletion invalidation.

### Completed Work
- [x] Added `backend/app/cache/` modules for exact cache, semantic cache, cache hygiene, and cache-first answer orchestration.
- [x] Implemented exact query normalization and SHA-256 normalized-query hashing.
- [x] Implemented semantic cache lookup with existing embedding client/dimension guard and pgvector cosine similarity.
- [x] Updated semantic hits to increment `hit_count` and refresh `last_used_at`.
- [x] Added `eligible: bool` gates to exact and semantic cache writes with BC14 TODO wiring.
- [x] Added `backend/app/scheduling/cache_scheduler.py` and FastAPI lifespan startup/shutdown wiring gated by `ENABLE_SCHEDULED_JOBS`.
- [x] Added `SEMANTIC_CACHE_MAX_ROWS=5000` to `.env.example`.

### Verification
- [x] `docker compose -p assessment exec backend pytest app/tests/test_cache.py -vv`
  - Result: `9 passed in 7.74s`
- [x] `docker compose -p assessment exec backend pytest`
  - Result: `64 passed, 12 skipped, 4 warnings in 20.89s`

### PR Draft
- [x] `.codex/pull_requests/PR_BC11.md`

---

## Architecture Decisions Logged
- [x] `ARCHITECTURE (4).md` section 18 records internal-only page-image access.
- [x] `ARCHITECTURE (4).md` section 18 records deterministic lexical-overlap context compaction.
- [x] `ARCHITECTURE (4).md` section 18 records BC11 scheduler infrastructure extended by BC20.
- [x] `ARCHITECTURE (4).md` section 18 records cache write eligibility gates.
- [x] `ARCHITECTURE (4).md` section 18 records cache invalidation by missing referenced document IDs.

---

## Active Cycle: BC12-BC15

**Status:** [ ] Implemented; backend Docker verification blocked by image build failure

### Objective
Implement the chat endpoint and Chainlit wiring, the Next.js `/documents` upload page, real guardrails/output filtering, JWT document-management auth, and per-session/per-IP rate limiting.

### Planned Work
- [ ] **BC12:** Add `POST /api/v1/chat`, idempotency via `query_audit_log.idempotency_key`, cache-before-retrieval flow, session/message persistence, conversation window/summary helpers, deterministic generation client boundary, RetrievalAgent/Orchestrator integration, and Chainlit step wrappers.
- [ ] **BC13:** Add backend upload-limits config endpoint, build frontend `/documents` upload/manage UI, fetch limits from backend, implement progress/polling/delete/empty state/auth-header stub, and add deterministic frontend tests.
- [ ] **BC14:** Add router/app-level input validation, tool-result sanitization, real output filter, cache eligibility wiring, security headers, and configured CORS.
- [ ] **BC15:** Add JWT session endpoint, auth dependency, document route protection, anonymous chat flag behavior, rate limiting before cache lookup, `query_audit_log.client_ip` migration, and auth/rate-limit tests.

### Expected Test Coverage
- [ ] `docker compose -p assessment exec backend pytest app/tests/test_chat.py -vv`
- [ ] `docker compose -p assessment exec backend pytest app/tests/test_upload_config.py -vv`
- [ ] Frontend deterministic test command from `frontend/package.json`
- [ ] `docker compose -p assessment exec backend pytest app/tests/test_guardrails.py -vv`
- [ ] `docker compose -p assessment exec backend pytest app/tests/test_cache.py -vv`
- [ ] `docker compose -p assessment exec backend pytest app/tests/test_auth.py -vv`
- [ ] `docker compose -p assessment exec backend pytest app/tests/test_rate_limit.py -vv`
- [ ] `docker compose -p assessment exec backend pytest app/tests/test_migrations.py -vv`
- [ ] `docker compose -p assessment exec backend pytest app/tests/test_documents.py -vv`
- [ ] `docker compose -p assessment exec backend pytest`

### Verification Status
- [x] `python3 -m compileall backend/app`
  - Result: backend package compile completed successfully.
- [x] `npm test --prefix frontend -- --runInBand`
  - Result: `1..1`, `# tests 1`, `# pass 1`, `# fail 0`, duration `1696.303333ms`.
- [ ] `docker compose -p assessment up -d --build backend frontend`
  - Blocked: backend image build failed during `pip install --default-timeout=180 --retries=10 -r /requirements.txt` with a package hash mismatch:
    `Expected sha256 edd81538446786ec3b73972543e53bb43bcaf0bfc8ef76cb679fcc390ffe136d; Got 2ba3fbf7a9d0eb89c59f58dac6f4623089aa375ac40569fcbad9af9e2b646235`.
  - Impact: backend targeted pytest commands remain pending until the image build is repaired and rebuilt.
