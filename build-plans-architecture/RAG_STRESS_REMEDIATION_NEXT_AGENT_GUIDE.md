# Next-Agent Prompt: RAG Precision, Evidence Reliability, And Stress-Test Remediation

You are Codex acting as Orchestrator for:

```text
/home/yusufu/myprojects/Senior-Engineer-AI-Digital-Health-Skills-Assessment
```

Your mission is to implement the next high-quality engineering patch set for the RAG weaknesses identified by the local stress test. You must use the newly created corrective agent skills and conform to the existing architecture, code style, database stack, deterministic test constraints, and multi-agent handoff workflow.

Do not rerun the full 100-question stress test by default. The previous agent already ran it and produced a local engineering handoff. Use the report as the evidence base, implement targeted fixes, and run only focused samples after deterministic tests pass.

---

## First Read And Follow

Read these files before making any code change:

```text
agents.md
agents-skills/Backend-engineer-SKILL.md
agents-skills/ML-engineer-SKILL.md
agents-skills/test-engineer-SKILL.md
agents-skills/Frontend-engineer-SKILL.md
agents-skills/skills.md
agents-skills/RAG-ingestion-metadata-engineer-SKILL.md
agents-skills/RAG-retrieval-precision-engineer-SKILL.md
agents-skills/RAG-evidence-reliability-engineer-SKILL.md
agents-skills/RAG-stress-validation-engineer-SKILL.md
plan.md
tests-README.md
README.md
local-setup.md
build-plans-architecture/ARCHITECTURE (4).md
stress-test-results/RAG_STRESS_ENGINEERING_HANDOFF.md
```

Also inspect the relevant app code before designing patches:

```text
backend/app/models.py
backend/app/documents/chunking.py
backend/app/documents/processing.py
backend/app/retrieval/hybrid_search.py
backend/app/agents/retrieval_agent.py
backend/app/agents/orchestrator.py
backend/app/api/v1/chat.py
backend/app/security/rate_limit.py
backend/app/chat/response_presenter.py
backend/app/security/guardrails.py
backend/alembic/versions/
backend/app/tests/
```

---

## Branch

Create and work on:

```bash
git checkout -b codex/rag-precision-evidence-reliability-correctives
```

Before branching, check `git status -sb`. Do not overwrite or revert unrelated user changes. Do not stage local stress-test artifacts.

---

## Local Artifacts And Confidentiality

The following are local-only engineering aids and must not be committed:

```text
stress-test-corpus/
stress-test-results/
stress-test-README.md
scripts/rag_stress_benchmark.py
```

They are ignored through `.git/info/exclude`. Keep them local. Use the report and targeted runner, but never add these files to Git.

---

## Corrective Skills To Use

Use these skills as overlays on top of the existing role skills:

1. `rag-ingestion-metadata-engineer`
   - For chunk metadata, thematic tags, document/page inventory, sparse visual PDF extraction, numeric fact capture, and pgvector-ready metadata persistence.
2. `rag-retrieval-precision-engineer`
   - For query analysis, document-aware retrieval quotas, metadata-filtered ANN pools, thematic vector search, reranking diversity, and source coverage.
3. `rag-evidence-reliability-engineer`
   - For evidence-sufficiency gates, fast no-answer routing, schema-stable refusals, eval-safe rate limits, retry/idempotency state handling, and provider failure resilience.
4. `rag-stress-validation-engineer`
   - For deterministic verification, targeted stress samples, gold-standard checks, and regression reporting without expensive full stress reruns.

Use the standard `backend-engineer`, `ml-engineer`, `test-engineer`, and `gitpr-agent` skills for implementation ownership, test discipline, and commits.

---

## Non-Negotiables

- Preserve SQLAlchemy async sessions with explicit `text()` SQL where the repo already uses SQL. No raw asyncpg in app code.
- Preserve Postgres + pgvector HNSW. Do not add a second vector database.
- Keep `SET LOCAL hnsw.ef_search` inside the same transaction as ANN queries.
- Do not treat raw RRF score as confidence. The confidence gate uses reranker score.
- Do not introduce hosted LLMs, hosted embeddings, hosted auth, S3, or reranker downloads into deterministic tests.
- Do not weaken public rate limits to make evaluation easier.
- Do not trust arbitrary `X-Forwarded-For` in production.
- Keep `/chat` idempotency, rate-limit, cache, retrieval, generation, presentation, output-filter, and cache-write ordering intact unless a deliberate divergence is logged and tested.
- Keep Chainlit step wrappers safe under pytest.
- Keep scheduler singleton-safe across replicas.
- Keep raw chunk `content` truthful for citation display. Metadata can enrich retrieval, but citations must still map to real source chunks/pages.
- If architecture diverges, log it in `build-plans-architecture/ARCHITECTURE (4).md` §18 in the same commit.
- Update `.codex/handover.json` at every agent phase.

---

## Evidence From Prior Stress Run

Use the completed run, not guesses:

```text
Full result JSON: stress-test-results/rag_stress_20260715T113402Z.json
Full result Markdown: stress-test-results/rag_stress_20260715T113402Z.md
Engineering handoff: stress-test-results/RAG_STRESS_ENGINEERING_HANDOFF.md
```

Headline result:

| Category | Count | Passed | Failed | Average score |
|---|---:|---:|---:|---:|
| Synthesis | 20 | 2 | 18 | 35.31 |
| Numerical Citation | 30 | 13 | 17 | 63.64 |
| Semantic Inference | 25 | 0 | 25 | 37.67 |
| Out-of-Scope / No Answer | 25 | 0 | 25 | 40.60 |
| Total | 100 | 15 | 85 | 45.72 |

Primary failure patterns:

- Low expected-answer coverage: 52/100.
- Missing expected page citations: 43/100.
- Missing expected document citations: 35/100.
- Missing numeric facts: 20/100.
- No-answer/refusal failures: 22/100.
- Blank or `in_flight` retry artifacts: 23 rows.
- First full run hit HTTP 429 at question 79 due local IP quota.

Treat these as engineering findings. Do not make prompt-only patches that leave retrieval/indexing/evidence behavior unchanged.

---

## Target Patch Set

Implement a coherent, minimally risky set of product-code changes that directly targets the report findings.

### Phase 1: Planning And Handoff Setup

1. Read all required files.
2. Update `.codex/handover.json` with an Orchestrator planning entry:
   - branch
   - objective
   - skills loaded
   - files expected to change
   - verification plan
3. Inspect existing migrations, models, tests, and retrieval flow.
4. Decide whether the patch set can fit safely in one branch. Keep changes scoped and staged logically.

Do not modify files until the current implementation surfaces are understood.

### Phase 2: Ingestion Metadata And Document Inventory

Use `RAG-ingestion-metadata-engineer-SKILL.md`.

Implement additive metadata support for retrieval precision:

- Add chunk-level metadata/tags/content-kind fields or a repo-style equivalent:
  - metadata JSONB mapped safely in SQLAlchemy
  - theme tags
  - entity tags
  - metric tags
  - content kind
- Add indexes appropriate for metadata/tag filtering.
- Preserve existing chunk content and citation behavior.
- Add deterministic metadata generation during chunk persistence.
- Add or extend document/page inventory support for:
  - authors and institutions
  - page count
  - tables and table summaries
  - figures
  - bibliography/reference count
  - dates
  - unit-bearing numeric facts
- Treat sparse visual pages as first-class:
  - OCR when text yield is low
  - preserve large numeral/caption pairs
  - extract facts like `2.5 kg CO2e/boe`, `~70%`, `2020`, `2022`
  - tag as `sparse_visual_page`

Engineering standard:

- Prefer deterministic parsers and heuristics already in the repo.
- If using generated summaries, keep deterministic tests faked or local-only.
- Do not add a hosted model dependency to tests.
- Add Alembic migration tests and ingestion tests.

### Phase 3: Query Analysis And Document-Aware Retrieval

Use `RAG-retrieval-precision-engineer-SKILL.md`.

Implement a typed deterministic query analyzer before retrieval:

- Detect intent:
  - single fact
  - numeric fact
  - multi-document comparison
  - all-documents
  - table/figure
  - document inventory
  - out-of-scope current fact
  - entity-present attribute-absent
- Detect document aliases:
  - Document 1 / Chevron
  - Document 2 / Lorem Ipsum
  - Document 3 / LayoutParser
  - filename/title fragments
  - all three documents
- Detect required entities, requested attributes, and numeric evidence requirements.

Extend retrieval:

- For multi-document/all-doc questions, run per-document retrieval with quotas.
- For table/figure/inventory questions, prefer metadata/inventory candidates.
- For numeric questions, prefer candidates with metric tags and unit-bearing evidence.
- Merge raw vector, lexical, metadata-filtered, and thematic pools with quota-aware RRF or MMR.
- Preserve chunk ids, document ids, page numbers, and section paths.
- Add bounded recovery retrieval if required documents are missing after rerank.
- Record retrieval coverage in `agent_trace_log`.

Engineering standard:

- Do not globally increase context size unless justified by intent.
- Do not replace retrieval with prompt instructions.
- Do not make query analysis depend on hosted LLM calls in deterministic tests.

### Phase 4: Evidence Sufficiency, No-Answer, Rate Limit, And Retry Reliability

Use `RAG-evidence-reliability-engineer-SKILL.md`.

Implement an evidence gate before generation:

- Return fast no-answer when the query asks for external/current facts and no external tool is enabled.
- Return fast no-answer when an entity is present but the requested attribute is absent.
- Return fast no-answer when numeric evidence is required but retrieved chunks lack the required number/unit.
- Return fast no-answer when cross-document requirements are not satisfied after bounded recovery retrieval.
- Persist a structured reason, such as:
  - `external_current_fact`
  - `attribute_absent`
  - `missing_numeric_evidence`
  - `missing_required_document`
  - `low_evidence_confidence`

Harden response reliability:

- Ensure refusal responses always return the normal chat response shape.
- Ensure provider failures after retrieval produce schema-stable non-cacheable responses.
- Ensure duplicate/idempotency retry paths do not leave stale `in_flight` as final result.
- Ensure duplicate polling does not hold a DB connection while sleeping.

Harden rate limiting:

- Keep anonymous public limits strict.
- Add an authenticated/internal eval quota class if needed.
- Do not trust arbitrary `X-Forwarded-For` in production.
- Return accurate rate-limit headers and retry-after metadata.
- Fix IP-limit retry-after calculation if it currently uses session state.
- Document whether cache hits count against rate limits and test the chosen behavior.

### Phase 5: Deterministic Tests

Use `test-engineer` and `RAG-stress-validation-engineer-SKILL.md`.

Add or update deterministic tests before running stress samples:

Required test areas:

- Migration/index tests for new metadata fields.
- Chunk metadata insert/read tests.
- Metadata-enriched retrieval text tests.
- Query analyzer intent and document alias tests.
- Document-aware retrieval quota tests.
- Table/inventory routing tests.
- Numeric evidence candidate preference tests.
- Evidence gate no-answer tests:
  - current external fact
  - entity present but attribute absent
  - missing numeric evidence
  - missing required document
- Rate-limit header/retry-after tests.
- Idempotency retry-state tests:
  - duplicate while running
  - duplicate after success
  - duplicate after failure
- Response schema consistency tests.
- Cache eligibility tests for refusals and provider failures.

Run targeted deterministic suites appropriate to the files changed. Start narrow, then broaden:

```bash
docker compose -p assessment exec backend pytest app/tests/test_retrieval.py -vv
docker compose -p assessment exec backend pytest app/tests/test_retrieval_agent.py -vv
docker compose -p assessment exec backend pytest app/tests/test_orchestrator.py -vv
docker compose -p assessment exec backend pytest app/tests/test_chat.py app/tests/test_rate_limit.py -vv
docker compose -p assessment exec backend pytest app/tests/test_cache.py -vv
docker compose -p assessment exec backend pytest app/tests/test_rag_system_integration.py -vv
```

If response shape, citations, document status, or no-answer rendering changes, also run:

```bash
npm test --prefix frontend -- --runInBand
python3 -m unittest chainlit_app.tests.test_chat -v
```

### Phase 6: Targeted Stress Samples

Only after deterministic tests pass, run the local targeted sample:

```bash
python3 scripts/rag_stress_benchmark.py \
  --skip-upload \
  --rotate-client-ip \
  --request-timeout-seconds 120 \
  --id SYN-01 \
  --id SYN-03 \
  --id SYN-05 \
  --id SYN-06 \
  --id NUM-01 \
  --id NUM-04 \
  --id NUM-20 \
  --id INF-09 \
  --id INF-25 \
  --id OOS-08 \
  --id OOS-21 \
  --id OOS-25
```

Expected improvement signals:

- No `429`.
- No transient `500`.
- No final `status: in_flight`.
- OOS/current/attribute-absent samples return fast uncited no-answer payloads.
- Chevron sparse visual facts are retrieved and cited from page 1.
- Multi-document synthesis cites all required documents/pages.
- Table/document-inventory questions use persisted inventory/metadata.
- `NUM-04` remains correct as a known-good ordinary LayoutParser fact.

Inspect raw answers and citations. Do not rely only on the aggregate score.

### Phase 7: Gold Standard And Broader Verification

Run gold-standard checks if the patch touches retrieval, grounding, numeric evidence, or no-answer behavior:

```bash
docker compose -p assessment exec backend pytest app/tests/test_gold_standard.py -vv
docker compose -p assessment exec backend pytest -m golden_set -vv
python -m gold_standard.runner --trigger manual --sample 8
```

Then run the broader backend suite when the targeted tests are green:

```bash
docker compose -p assessment exec backend pytest
```

If Docker image build fails, fix the image build first and rerun verification against the rebuilt image.

---

## Architecture And Documentation Requirements

Update docs only where the patch changes behavior:

- `build-plans-architecture/ARCHITECTURE (4).md` §18 for any divergence.
- `tests-README.md` for new deterministic or targeted validation commands.
- `README.md` or `local-setup.md` only if reviewer-facing commands or env vars change.
- `.env.example` for new config values, with defaults and rationale.
- `.codex/handover.json` at each phase boundary.

If adding new response statuses, metadata fields, rate-limit headers, or no-answer reasons, document them where future maintainers will look.

---

## Commit Plan

Use logical commits. Suggested sequence:

```text
feat: add chunk metadata and document inventory indexing
feat: add query analysis and document-aware retrieval
fix: add evidence sufficiency gate and stable no-answer responses
fix: harden eval rate limits and chat retry state
test: cover RAG precision and evidence reliability correctives
docs: document RAG stress remediation validation workflow
```

Stage only relevant files. Never stage local stress corpus/results/runner artifacts.

---

## Final Output Required

Your final response must include:

- Branch name.
- Commit SHAs and messages, if committed.
- Exact files changed.
- Exact tests run and results.
- Targeted stress sample IDs run and per-ID summary.
- Whether any full stress rerun was skipped, and why.
- Known limitations.
- Architecture divergences logged, or `None`.
- Next step: final stabilization/reviewer handoff.

Do not claim reviewer-ready status unless deterministic tests, targeted samples, and relevant gold checks have run and passed or their limitations are explicitly documented.
