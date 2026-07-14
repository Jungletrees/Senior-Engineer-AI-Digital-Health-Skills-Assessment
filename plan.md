# Development Build Plan (plan.md)

## Current Status: [ ] BC16-BC28 Corrective Implementation In Progress
**Active Build Cycle:** BC16-BC28 - Final Tests, Deployment Hardening, Scheduled Grading, and Gold-Standard Correctives

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
- [x] **BC12-BC15 - Chat, Documents UI, Guardrails, Auth, and Rate Limiting**
  - Pushed commit: `8ef6666 feat: implement BC12-BC15 chat documents guardrails auth`
  - Source branch: `codex/bc12-bc15-chat-documents-guardrails-auth`
  - PR creation URL: `https://github.com/Jungletrees/Senior-Engineer-AI-Digital-Health-Skills-Assessment/pull/new/codex/bc12-bc15-chat-documents-guardrails-auth`
  - Merged into current branch: `codex/bc16-bc28-final-tests-deploy-grading-correctives`

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

## Active Cycle: BC16-BC28

**Status:** [x] Corrective implementation and deterministic verification completed; documentation/handover fold-back in progress. Playwright remains unscaffolded in the current frontend package, and gold manual/CI runs require corpus fetch/checksum pinning plus human expected-answer verification before scores are meaningful.

### Objective
Complete the BC16-BC20 final test/deployment/docs/scheduler scope and BC21-BC28 corrective scope without restarting from scratch. This includes deterministic/gold-set test consolidation, frontend/Playwright coverage, deploy hardening, singleton scheduled jobs, cost/rate-limit/cache correctness, numeric-aware grounding, reproducible `JudgeAgent` grading, fixed gold-standard corpus evaluation, deviation alerts, and documentation fold-back.

### Planned Work
- [ ] **BC16:** Consolidate deterministic backend/golden-set tests; add `golden_set` pytest marker and retrieval-mode/cache/grounding report caveat.
- [ ] **BC17:** Complete frontend deterministic tests and Playwright smoke workflow; document `PLAYWRIGHT_BASE_URL` in README, not `.env.example`.
- [ ] **BC18:** Add/verify `/health`, production Docker system packages, S3 storage backend via IAM/task role, and CI jobs with deploy gated via real `needs:`.
- [ ] **BC19:** Fold README/local setup/test documentation back; add cross-link/env-var audit scripts and public tool docstring drift pass.
- [ ] **BC20:** Extend the existing scheduler with nightly grading, anomaly detection, config drift checks, and hour-of-day baseline guards.
- [x] **BC21:** Add Postgres advisory-lock scheduler singleton guard with per-job-family lock offsets.
- [x] **BC22:** Finish model-pricing cost computation, rate-limit indexes, semantic-cache `embedding_model` scoping, and drift invalidation.
- [x] **BC23:** Finish numeric-aware grounding and use the same implementation for pre-send filtering, nightly re-check, and gold grading; generated-output numeric claims are exact-match only.
- [x] **BC24:** Split anomaly cadence, store judge metadata, add Chainlit step shim tests, make tsvector config explicit, assert `SET LOCAL hnsw.ef_search` transaction scope, and keep duplicate idempotency polling pool-safe.
- [x] **BC25:** Integrate the gold-standard corpus/question/rubric package with TOFU checksums, verified-question skipping, and fixed rubric weights.
- [x] **BC26:** Persist `gold_eval_run` / `gold_eval_result`; add manual/CI runner through `/chat`; use fake chat and fake `JudgeAgent` clients in deterministic tests.
- [x] **BC27:** Add Markdown reports, category scores/trends foundation, deviation alerts, and baseline-reset behavior.
- [x] **BC28:** Fold BC21-BC27 decisions/docs/env/PR descriptions/handover into the canonical repo documentation.

### Expected Test Coverage
- [x] `docker compose -p assessment exec backend pytest app/tests/test_scheduler_singleton.py -vv`
- [x] `docker compose -p assessment exec backend pytest app/tests/test_cost.py -vv`
- [x] `docker compose -p assessment exec backend pytest app/tests/test_rate_limit_indexes.py -vv`
- [x] `docker compose -p assessment exec backend pytest app/tests/test_semantic_cache_model_scope.py -vv`
- [x] `docker compose -p assessment exec backend pytest app/tests/test_numeric_grounding.py -vv`
- [x] `docker compose -p assessment exec backend pytest app/tests/test_anomaly_detection.py -vv`
- [x] `docker compose -p assessment exec backend pytest app/tests/test_judge_reproducibility.py -vv`
- [x] `docker compose -p assessment exec backend pytest app/tests/test_gold_standard.py -vv`
- [x] `docker compose -p assessment exec backend pytest -m golden_set -vv`
- [x] `docker compose -p assessment exec backend pytest`
- [x] `npm test --prefix frontend -- --runInBand`
- [ ] `npx playwright test --prefix frontend` - not run; frontend has no Playwright dependency/config/spec yet.
- [ ] `python -m gold_standard.runner --trigger manual --sample 8` - pending corpus fetch/checksum pinning, indexing, and expected-answer verification.
- [ ] `python -m gold_standard.runner --trigger ci --floor 85` - pending corpus fetch/checksum pinning, indexing, and expected-answer verification.

### Verification Status
- [x] `python3 -m compileall backend/app gold_standard`
  - Result: passed in the handoff state.
- [x] `docker compose -p assessment build backend`
  - Result: passed. Fixed by pinning CPU-only `torch==2.9.1+cpu` from the official PyTorch CPU wheel index before `sentence-transformers`, keeping the local CrossEncoder architecture while avoiding the CUDA wheel chain that failed earlier.
- [x] `docker compose -p assessment up -d backend frontend`
  - Result: passed after backend image packaging was changed to include `gold_standard/` and `pytest.ini`.
- [x] `docker compose -p assessment exec backend pytest`
  - Result: `120 passed, 12 skipped, 4 warnings in 41.03s`.
- [x] `npm test --prefix frontend -- --runInBand`
  - Result: `1 passed`.
- [x] backend health smoke
  - Result: `{"status":"ok","database":"ok"}`.

### Current Partial Implementation
- [x] BC20-BC28 settings fields added in `backend/app/settings.py`.
- [x] `backend/app/core/cost.py` added and `/chat` cost finalization started.
- [x] Duplicate idempotency polling changed to roll back before sleeping so it does not hold a database connection.
- [x] Semantic cache lookup/write scoped by embedding model in code; migration/model/test coverage still pending.
- [x] `backend/alembic/versions/0013_corrective_grading_schema.py` added for corrective schema changes.
- [x] `backend/app/agents/judge_agent.py` added as the production `JudgeAgent` boundary with injectable client and deterministic fallback.
- [x] `backend/app/security/numeric_grounding.py` added and `guardrails.py` wired to fail unsupported clinical numeric claims.
- [x] `gold_standard/` package copied from corrective builds; `client.py` and `runner.py` still require repo-native SQLAlchemy/`/chat`/`JudgeAgent` adaptation.
