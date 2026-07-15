# Next-Agent Handoff: RAG Stress Remediation — Phase 3+ and Verification

You are continuing the RAG stress-test remediation on branch
`codex/rag-precision-evidence-reliability-correctives` (pushed to `origin`). Read
`build-plans-architecture/RAG_STRESS_REMEDIATION_NEXT_AGENT_GUIDE.md` (the original brief),
`stress-test-results/RAG_STRESS_ENGINEERING_HANDOFF.md` (evidence base), and
`.codex/handover.json` (full running log) before making changes. The four corrective
overlay skills in `agents-skills/RAG-*.md` are the working profiles.

## Non-negotiables (unchanged)
- SQLAlchemy async + explicit `text()` SQL; no raw asyncpg in app code.
- Postgres + pgvector HNSW only; `SET LOCAL hnsw.ef_search` stays in the ANN transaction.
- RRF is ordering-only; the confidence gate uses the reranker score.
- No hosted LLM/embedding/auth/S3/reranker downloads in deterministic tests. Run the
  deterministic suite hermetically:
  `docker compose -p assessment exec -e GEMINI_API_KEY= -e OPENAI_API_KEY= -e VOYAGE_API_KEY= -e ANTHROPIC_API_KEY= -T backend pytest`
- pytest fixtures `alembic downgrade base` then re-`upgrade head`; they WIPE the shared DB.
  Run any live stress sample BEFORE the suite, and `alembic upgrade head` after to restore.
- Do NOT commit `stress-test-corpus/`, `stress-test-results/`, `stress-test-README.md`,
  `scripts/rag_stress_benchmark.py` (git-excluded via `.git/info/exclude`).
- The live backend bakes code into the image (no bind mount). To test uncommitted code in
  the running server, rebuild (`docker compose -p assessment up -d --build backend`) or
  `docker cp` files into the container for a pytest run (a container recreate resets cp'd files).

## What is already DONE (committed on this branch)
- **Phase 1**: handover entries at each phase.
- **Phase 4 reliability**: evidence gate (`app/chat/evidence_gate.py`) — fast external/current-fact
  refusal + conservative numeric-evidence refusal; reasons traced to `agent_trace_log`.
  IP-dimension rate-limit `Retry-After` fix. Idempotency terminal-state fix (no stale
  `in_flight`). Provider-failure-after-retrieval -> schema-stable non-cacheable response.
  Duplicate-poll releases its DB connection during sleep. All tested.
- **Phase 3 (analyzer)**: `app/retrieval/query_analysis.py` — typed `analyze_query` (intent,
  document aliases, entities, requested attributes, numeric requirement) + `resolve_document_ids`.
- **Phase 3 (document-aware retrieval)**: `app/agents/retrieval_agent.py` `_document_aware_cascade`
  runs per-document hybrid search with a quota and reranks the merged pool when the analyzer
  resolved >=2 required documents; coverage written to `agent_trace_log`. Wired through
  `chat.py` (`_resolve_required_documents`) -> `assemble_generation_payload` ->
  `RetrievalAgent.run` -> `run_retrieval_cascade`.  [Verify it is committed; if a test for it
  is missing, add one — see below.]
- **Phase 2 (ingestion metadata + inventory)**: migrations 0017 (chunk `metadata` JSONB +
  `theme_tags`/`entity_tags`/`metric_tags` + `content_kind`, GIN indexes) and 0018
  (`document_inventory` table). Deterministic generators in `app/documents/chunk_metadata.py`
  and `app/documents/document_inventory.py`, wired into `chunking.py`. Embeddings remain on
  raw content by design (reuse consistency + citation truthfulness; logged ARCHITECTURE §18).
- **Ingestion loophole fixed**: `docker-compose.yaml` mounts `uploads_volume` +
  `page_images_volume` (files were on the ephemeral layer and lost on recreate).
- **Docs**: ARCHITECTURE §7.7 (embedding speed + prod model options) and §18 rows;
  DEPLOYMENT.md "Hardening From Observed Test Behavior"; `.env.example` embedding knobs;
  tests-README; plan.md.
- **Verification to date**: full hermetic backend `pytest` = 266 passed / 12 skipped.
  Live targeted stress (before Phase 2/3): OOS 3/3=100%, NUM-04 100%, no 429/5xx/in_flight;
  SYN/NUM/INF weak due to flat-pool dominance (the gap Phase 3 targets).

## REMAINING WORK (do these, in order)

### A. Finish/verify Phase 3 document-aware retrieval
1. Confirm `_document_aware_cascade` is committed and add a deterministic test in
   `app/tests/test_retrieval_agent.py`: inject a fake `hybrid_search_fn` that returns a
   DIFFERENT candidate per `document_id_filter`, call `run_retrieval_cascade(..., db=None,
   required_document_ids=[docA, docB])`, and assert BOTH documents appear in
   `result.chunks` (coverage), and that a single-document query still uses the flat cascade.
2. Add a `test_chat.py` case: a comparison query ("Compare Document 1 and Document 3")
   resolves two documents and the FakeRetrievalAgent receives `required_document_ids`.

### B. Phase 3 refinements (metadata-aware pools)
3. Route `table_or_figure` / `document_inventory` intents to inventory + metadata-tagged
   candidates first: query `document_inventory` for counts/authors/references; prefer chunks
   with `content_kind IN ('table','figure','document_inventory','author_block','bibliography')`.
4. For `numeric_fact` intent, prefer candidates whose `metric_tags` are non-empty (unit-bearing
   evidence) and penalize entity-only matches with no numeric/unit string.
5. Add a metadata-filtered ANN pool merged with the content pool via quota-aware RRF/MMR
   (preserve diversity by document and `content_kind`; dedupe by chunk id; keep page/section).
6. Bounded recovery: if a required document is still missing after rerank, do one extra
   scoped retrieval for it before generation. Record coverage in `agent_trace_log`.

### C. Phase 4 remaining evidence-gate reasons
7. `attribute_absent`: when the analyzer detected `required_entities` present in retrieved
   chunks but none of the `requested_attributes`, return a fast no-answer (reason
   `attribute_absent`). Keep it conservative to avoid false refusals.
8. `missing_required_document`: after bounded recovery, if a required document has zero
   candidates, return no-answer (reason `missing_required_document`).
   Add tests for both in `app/tests/test_evidence_gate.py` and `test_chat.py`.

### D. Inventory-answering path
9. For `document_inventory` questions (counts/authors/references/pages), answer from the
   `document_inventory` row (cite source pages where available) instead of ordinary semantic
   generation. Add a small presenter/orchestrator path + tests.

## VERIFICATION (run in this order)
Deterministic first (hermetic):
```bash
docker compose -p assessment exec -e GEMINI_API_KEY= -e OPENAI_API_KEY= -e VOYAGE_API_KEY= -e ANTHROPIC_API_KEY= -T backend pytest app/tests/test_query_analysis.py app/tests/test_evidence_gate.py app/tests/test_chunk_metadata.py app/tests/test_document_inventory.py -q
docker compose -p assessment exec -e GEMINI_API_KEY= ... -T backend pytest app/tests/test_retrieval.py app/tests/test_retrieval_agent.py app/tests/test_orchestrator.py -q
docker compose -p assessment exec -e GEMINI_API_KEY= ... -T backend pytest app/tests/test_chat.py app/tests/test_rate_limit.py app/tests/test_cache.py app/tests/test_rag_system_integration.py -q
docker compose -p assessment exec -e GEMINI_API_KEY= ... -T backend pytest app/tests/test_migrations.py app/tests/test_schema_constraints.py app/tests/test_chunking.py -q
docker compose -p assessment exec -e GEMINI_API_KEY= ... -T backend pytest   # full suite, expect all green
```
Then targeted stress on the LIVE stack (needs a real embedding/generation key and the corpus
indexed; deterministic tests wipe the DB, so re-index first):
```bash
# 1) rebuild so the live server has your code:  docker compose -p assessment up -d --build backend   (pass GEMINI_API_KEY=... inline)
# 2) alembic upgrade head; upload the 3 stress PDFs; wait for all 'indexed'
#    (free-tier Gemini paces ~70 req/min; a 16-page doc took ~9.4 min — see ARCHITECTURE §7.7)
python3 scripts/rag_stress_benchmark.py --skip-upload --rotate-client-ip \
  --request-timeout-seconds 120 --poll-timeout-seconds 600 \
  --id SYN-01 --id SYN-03 --id SYN-05 --id SYN-06 \
  --id NUM-01 --id NUM-04 --id NUM-20 --id INF-09 --id INF-25 \
  --id OOS-08 --id OOS-21 --id OOS-25
```
Success signals: no 429/5xx/in_flight; OOS fast uncited no-answers; Chevron facts cited from
page 1; multi-document synthesis (SYN-01/06) cites BOTH documents (this is the Phase 3 win to
confirm); table/inventory questions (NUM-20/SYN-05) use inventory metadata; NUM-04 stays green.
Inspect raw answers and citations, not just the aggregate score. Do NOT run the full
100-question bank unless the targeted sample improves. `alembic upgrade head` afterward.

Gold standard (if grounding/no-answer behavior changed):
```bash
docker compose -p assessment exec backend pytest app/tests/test_gold_standard.py -vv
docker compose -p assessment exec backend pytest -m golden_set -vv
```

## Finish
Commit logically (feat/fix/test/docs), update `.codex/handover.json`, ARCHITECTURE §18 for any
divergence, tests-README for new commands, and push. Do not claim reviewer-ready unless
deterministic tests, targeted samples, and relevant gold checks pass or their limitations are
explicitly documented.
