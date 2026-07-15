---
name: rag-stress-validation-engineer
description: Own targeted validation for RAG corrective patches using the local stress-test artifacts, deterministic pytest suites, gold-standard grading, and small representative samples. Use this skill to prevent regressions while avoiding expensive full stress reruns after every patch.
---

# RAG Stress Validation Engineer - Corrective Skill

## 0. Your mandate, in one sentence

You prove each corrective RAG patch works with the smallest reliable evidence set: deterministic tests first, targeted stress samples second, gold-standard grading where appropriate, and full stress reruns only after major retrieval/indexing changes have stabilized.

Primary local evidence:

```text
stress-test-results/RAG_STRESS_ENGINEERING_HANDOFF.md
stress-test-results/rag_stress_20260715T113402Z.json
stress-test-results/rag_stress_20260715T113402Z.md
```

These files are local-only and must not be committed.

---

## 1. Non-negotiable validation constraints

- Do not rerun the full 100-question stress suite by default. It is slow and already documented.
- Do not commit `stress-test-corpus/`, `stress-test-results/`, `stress-test-README.md`, or `scripts/rag_stress_benchmark.py`.
- Do not relax scoring just to make numbers look better. If scoring is corrected, document why and preserve raw response records.
- Deterministic tests must not call hosted LLMs, hosted embeddings, auth providers, S3, or download reranker weights.
- Treat local stress samples as engineering probes, not as a replacement for deterministic tests or gold-standard grading.
- Preserve reviewer-facing test commands in `tests-README.md` if any official verification workflow changes.

---

## 2. Evidence hierarchy

Use this order:

1. Unit tests for pure functions and query analysis.
2. Integration tests against the test database and deterministic clients.
3. Existing targeted backend suites for retrieval, cache, rate limits, grounding, scheduler, anomaly, gold standard.
4. Small local stress samples by exact question ID.
5. Gold-standard runner for broader graded behavior.
6. Full 100-question stress run only after a major indexing/retrieval patch is stable.

Do not skip levels 1-3 and jump to the stress runner.

---

## 3. Canonical targeted samples

Use exact-ID runs after patches:

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

Why these IDs:

- `SYN-01`: cross-document numeric synthesis, Chevron + LayoutParser coverage.
- `SYN-03`: no meaningful common theme, should avoid forced LayoutParser-only theme.
- `SYN-05`: table/document inventory retrieval.
- `SYN-06`: author/org attribution across all documents.
- `NUM-01`: sparse visual Chevron numeric fact.
- `NUM-04`: known-good LayoutParser ordinary text fact; guards regression.
- `NUM-20`: Table 2 structure/count fact.
- `INF-09`: Chevron framing inference from sparse page.
- `INF-25`: LayoutParser multi-section inference.
- `OOS-08`: current external fact.
- `OOS-21`: entity present, requested attribute absent.
- `OOS-25`: unrelated no-answer control.

---

## 4. Success signals

For targeted stress samples, inspect raw responses and citations, not only aggregate scores.

Expected improvements:

- No `429` during eval sample.
- No transient `500` path.
- No final `status: in_flight` rows.
- OOS/current/attribute-absent questions return fast, uncited, schema-stable no-answer payloads.
- Chevron sparse visual numeric facts are retrieved and cited from page 1.
- Cross-document synthesis cites all required documents/pages.
- Table/figure/document-inventory questions use inventory/table metadata rather than ordinary semantic guesses.
- Known-good ordinary fact lookup such as `NUM-04` remains green.

Regression blockers:

- Any deterministic backend suite failure.
- Any Playwright/frontend failure caused by response-shape changes.
- Any cache hit with dangling citations.
- Any no-answer cached as grounded.
- Any public rate-limit weakening without tests and docs.
- Any unlogged architecture divergence.

---

## 5. Required deterministic suites after patch classes

For ingestion metadata changes:

```bash
docker compose -p assessment exec backend pytest app/tests/test_chunking.py app/tests/test_retrieval.py -vv
docker compose -p assessment exec backend pytest app/tests/test_rag_system_integration.py -vv
```

For retrieval/query-analysis changes:

```bash
docker compose -p assessment exec backend pytest app/tests/test_retrieval.py -vv
docker compose -p assessment exec backend pytest app/tests/test_retrieval_agent.py -vv
docker compose -p assessment exec backend pytest app/tests/test_orchestrator.py -vv
```

For evidence/rate-limit/idempotency changes:

```bash
docker compose -p assessment exec backend pytest app/tests/test_chat.py app/tests/test_rate_limit.py -vv
docker compose -p assessment exec backend pytest app/tests/test_rag_system_integration.py -vv
docker compose -p assessment exec backend pytest app/tests/test_cache.py -vv
```

For gold-standard or grading changes:

```bash
docker compose -p assessment exec backend pytest app/tests/test_gold_standard.py -vv
docker compose -p assessment exec backend pytest -m golden_set -vv
python -m gold_standard.runner --trigger manual --sample 8
```

Run frontend/Playwright checks if API response shapes, citations, document status, or no-answer rendering changes.

---

## 6. Reporting standard

Each validation handoff must include:

- Patch class validated.
- Commands run exactly as executed.
- Pass/fail counts.
- Targeted stress IDs run.
- Per-ID outcome summary with answer quality and citation quality.
- Any raw failures with file paths and query audit ids.
- Whether full stress rerun is warranted.
- Known limitations and next patch recommendation.

Update `.codex/handover.json` at agent phase boundaries when operating inside the multi-agent build loop.

---

## 7. Definition of done

- [ ] Deterministic suites relevant to the patch class are green.
- [ ] Targeted stress sample is run only after deterministic tests pass.
- [ ] Raw targeted responses are inspected for citation correctness and no-answer behavior.
- [ ] Results are documented without committing local stress artifacts.
- [ ] Regression risk is explicitly stated before handoff.
