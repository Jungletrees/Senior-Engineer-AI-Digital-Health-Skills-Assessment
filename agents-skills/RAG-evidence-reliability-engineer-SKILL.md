---
name: rag-evidence-reliability-engineer
description: Own reliability and safety corrective patches from the local stress-test report: evidence-sufficiency gates, fast no-answer routing, schema-stable refusal responses, eval-safe rate limits, retry/idempotency state handling, provider timeout resilience, and observability for failed RAG turns.
---

# RAG Evidence Reliability Engineer - Corrective Skill

## 0. Your mandate, in one sentence

You stop unsupported answers and unstable responses before they reach the user: classify insufficient evidence, return fast schema-stable no-answers, harden retries/rate limits/idempotency, and make operational failures observable without weakening public safety controls.

Primary evidence:

```text
stress-test-results/RAG_STRESS_ENGINEERING_HANDOFF.md
```

---

## 1. Non-negotiable project constraints

- Preserve `/chat` safety ordering: validate input, claim/audit idempotency, enforce rate limits, check cache, retrieve, generate only when evidence is sufficient, present/filter output, write eligible caches.
- Do not bypass rate limits globally to make tests pass.
- Do not trust arbitrary `X-Forwarded-For` in production.
- Keep production anonymous limits strict while allowing authenticated/local eval to have its own bounded quota class.
- Keep responses typed and schema-stable for UI and benchmark clients.
- Do not cache ungrounded, filtered, retry-error, `in_flight`, or no-citation failure responses as successful answers.
- Use SQLAlchemy async sessions and explicit `text()` SQL. No raw asyncpg in app code.

---

## 2. Stress-test findings you own

The full run exposed:

- First full run hit HTTP `429 RATE_LIMIT_EXCEEDED` at question 79 because local smoke/partial attempts consumed the same IP quota.
- Many OOS questions took slow paths and hit transient `500` before retry.
- 23 result rows returned blank cache status with raw payload `{"session_id": "...", "status": "in_flight"}`.
- OOS/current/attribute-absent questions should often be fast, uncited refusals but were operationally unstable.

These are reliability defects as much as accuracy defects.

---

## 3. Evidence-sufficiency gate

Add a deterministic gate between retrieval and generation. It should decide whether the retrieved evidence can support the requested answer.

Return no-answer before generation when:

- The query asks for current/external information and web/tool search is not enabled.
- The entity exists in the corpus but the requested attribute is absent.
- Retrieved chunks are topically related but lack the requested field, number, unit, date, page, table, or citation basis.
- A numeric question lacks required numeric/unit evidence.
- Cross-document comparison lacks required document coverage after bounded recovery retrieval.

Persist machine-readable reasons:

- `external_current_fact`
- `attribute_absent`
- `low_evidence_confidence`
- `missing_numeric_evidence`
- `missing_required_document`
- `retrieval_unavailable`
- `provider_unavailable`

The refusal response must include the normal chat response fields:

- `answer`
- `cache_status`
- `source_chunk_ids`
- `citations`
- `query_audit_log_id`
- `output_filter_status`
- `output_filter_reason`
- `model_status`

---

## 4. No-answer and provider-failure behavior

No-answer should be cheap and boring.

Implementation expectations:

- Bound retrieval/rerank/generation time budgets by stage.
- If evidence sufficiency fails, do not call the generation provider.
- If retrieval itself fails, return the existing retrieval-unavailable no-answer shape.
- If the generation provider times out or returns transient errors after retrieval, return a schema-stable safe response and mark it non-cacheable.
- Add jittered exponential backoff only where a retry can succeed. Do not retry deterministic validation errors.
- Add a circuit-breaker-style guard if repeated provider failures occur in one run.

---

## 5. Rate-limit engineering

Keep public limits strict, but make evaluation reliable.

Patch expectations:

- Add an authenticated/internal eval quota class rather than weakening anonymous public limits.
- Rate-limit by actor/route/quota class when authenticated identity is available; fall back to IP/session for anonymous users.
- Return accurate rate-limit headers:
  - `Retry-After`
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`
  - limiting dimension
- Fix IP-limit retry-after calculation. Do not compute IP retry-after from session rows.
- Decide and document whether cache hits count against public rate limits. If they do, make it explicit; if not, test that ordering carefully.
- Add audit details for limit key, dimension, remaining, and retry-after.

Never use arbitrary `X-Forwarded-For` as an eval bypass in production. The local stress runner used synthetic IP rotation only to finish evidence collection in a local environment.

---

## 6. Retry, idempotency, and in-flight state

The backend should not leave benchmark/UI clients with partial chat payloads unless it exposes a documented polling contract.

Patch expectations:

- Model chat processing as explicit states:
  - `claimed`
  - `retrieving`
  - `generating`
  - `completed`
  - `failed_retryable`
  - `failed_terminal`
- Store either the final response payload or enough normalized fields to reconstruct it.
- If duplicate polling times out, return a documented `202` with retry metadata and operation id.
- If the original attempt failed terminally, mark the audit row failed and let a retry safely create a new attempt or return the terminal error.
- Ensure duplicate polling does not hold a DB connection while sleeping.
- Add cleanup/recovery for stale `in_flight` rows.

---

## 7. Testing you own

Add deterministic tests for:

- Evidence gate: current/external fact refusal.
- Evidence gate: entity present but attribute absent.
- Evidence gate: numeric question missing numeric evidence.
- Evidence gate: required document missing in cross-document query.
- Refusal response schema is complete and non-cacheable.
- Rate-limit headers and retry-after are correct for session, IP, and eval quota.
- Cache-hit rate-limit behavior matches documented policy.
- Duplicate while original running returns documented 202 without holding DB connection.
- Duplicate after success reconstructs final response.
- Duplicate after failure does not stay `in_flight`.
- Provider timeout/500 produces schema-stable safe response.

Targeted stress samples:

```bash
python3 scripts/rag_stress_benchmark.py --skip-upload --rotate-client-ip \
  --id OOS-08 --id OOS-09 --id OOS-21 --id OOS-23 --id OOS-25
```

Expected outcome: no `429`, no `500`, no `status: in_flight`, fast uncited no-answer payloads.

---

## 8. Definition of done

- [ ] Evidence-sufficiency gate prevents unsupported generation.
- [ ] No-answer paths are fast, deterministic where possible, schema-stable, and non-cacheable.
- [ ] Rate limits remain strict for anonymous users and reliable for authenticated/local eval.
- [ ] Idempotency retry paths cannot leave stale `in_flight` rows as the final client-visible result.
- [ ] Operational failures are auditable by reason and stage.
- [ ] Existing backend and frontend tests remain green.
- [ ] Any architecture divergence is logged in `ARCHITECTURE (4).md` §18.
