# Last Mile Health RAG Platform

This repository implements a clinical-document retrieval-augmented generation system for uploaded PDF guidance. The stack keeps the original service boundaries: a Next.js document-management frontend, a Chainlit chat container, a FastAPI backend, and PostgreSQL with pgvector for document, chunk, audit, cache, and evaluation data.

The backend is the source of truth for ingestion, retrieval, generation, guardrails, caching, scheduling, and gold-standard evaluation. Uploaded PDFs are validated and stored through the API; the ingestion worker path parses page metadata, chunks content, embeds text, and indexes into PostgreSQL/pgvector, but automatic enqueueing from the upload route remains a known limitation. Chat requests run through input validation, exact/semantic cache lookup, hybrid retrieval, local cross-encoder reranking, optional query expansion, grounded answer generation, output filtering, and audit logging.

The implementation is submission-ready as a backend and document-ingestion system with deterministic test coverage. Some UI-facing requirements remain explicit limitations: the Chainlit app is still a thin shell, the root Next.js page renders backend status rather than a full chat surface, Chicago-style superscript citation rendering is not complete, and Playwright e2e tests are documented but not scaffolded.

## Reviewer Build Status

| Workstream | Status | Evidence / reviewer note |
|---|---|---|
| BC16-BC28 backend corrective scope | Verified complete for deterministic scope | Last known full backend run: `120 passed, 12 skipped, 4 warnings`; targeted scheduler, cost, cache, numeric grounding, anomaly, judge, and gold-standard tests passed. |
| FastAPI health/docs | Complete | `/health` returns `{"status":"ok","database":"ok"}` in the last smoke test; OpenAPI is available at `/docs`. |
| Documents API validation/storage | Partial | Upload validation, storage, dedup, list, poll, and delete are implemented; the route stores `processing` records but does not visibly enqueue the ingestion worker yet. |
| Ingestion worker | Verified complete in deterministic tests | Worker path indexes a `processing` document, persists chunks/page images, and marks it `indexed` under fake clients. |
| Backend `/api/v1/chat` | Verified complete for backend contract | Idempotency, rate limit, cache ordering, retrieval/generation, filtering, audit, and `source_chunk_ids` persistence are tested. |
| Chainlit chat UI | Not complete | Chainlit container starts, but the handler currently echoes messages and is not wired to `/api/v1/chat`. |
| Chicago superscript citations | Partial | Backend has source lineage, but structured citation response and UI footnote rendering are incomplete. |
| Frontend `/documents` UI | Partial | Deterministic helper tests pass; browser responsive and upload-to-indexed e2e verification are not complete. |
| Playwright e2e | Not complete | No Playwright dependency, config, or spec is scaffolded. |
| Gold-standard workflow | Implemented, not yet trusted with real scores | Runner, persistence, rubric, reports, and deterministic tests exist; real scores require corpus fetch, checksum pinning, indexing, and human expected-answer verification. |
| Clean-clone validation | Not complete | A clean clone has not been run for this checklist pass. |
| AWS deployment | Planned | AWS architecture, Lambda/Bedrock rationale, security, and CI/CD plan are documented; no live deployment or IaC exists. |

## Architecture Summary

```text
Next.js :3000 /documents
        |
        | PDF upload, document list/delete
        v
FastAPI :6100 /api/v1
        |-- auth/session, documents, chat, config, health, OpenAPI docs
        |-- upload validation, ingestion, OCR/rasterization, chunking
        |-- exact cache, semantic cache, hybrid search, rerank
        |-- guardrails, numeric grounding, audit logs, scheduled jobs
        v
PostgreSQL :5432 + pgvector
        |-- documents, chunks, page_images, chat_messages
        |-- query_audit_log, agent_trace_log, response_grade
        |-- gold_eval_run, gold_eval_result, anomaly_flag

Chainlit :8000
        |-- retained as the chat container, but not yet wired to /api/v1/chat
```

Core backend components:

- **Frontend:** Next.js `/documents` page for PDF upload, client-side validation, progress display, document polling, and delete.
- **Chat UI:** Chainlit container exists, but currently echoes messages instead of calling the backend chat API.
- **Backend:** FastAPI with async SQLAlchemy sessions, CORS/security middleware, JWT session tokens, rate limits, and OpenAPI at `/docs`.
- **Database:** PostgreSQL 16 with pgvector, HNSW vector index, generated `content_tsv`, and Alembic migrations.
- **Retrieval:** vector search plus PostgreSQL full-text search, Reciprocal Rank Fusion, local `sentence-transformers` CrossEncoder reranking, and gated query expansion.
- **Generation:** backend `/api/v1/chat` assembles grounded context and returns `source_chunk_ids`; UI-level Chicago superscript footnotes are a known gap.
- **Guardrails:** input validation, prompt-injection delimiter sanitization, output grounding checks, exact numeric/dosage grounding, and cache write eligibility.
- **Caches:** exact normalized-query cache and semantic cache scoped by embedding model.
- **Scheduler:** cache hygiene, retrospective grading, anomaly detection, and gold-eval jobs guarded by PostgreSQL advisory locks.
- **Gold evaluation:** versioned corpus/question/rubric workflow with checksum pinning, verified-answer skipping, SQL persistence, Markdown reports, and deviation alerts.

## Local Setup

Prerequisites:

- Docker Engine 24+ and Docker Compose v2+
- Node 20+ only if running frontend commands outside Docker
- Python 3.12 only if running backend or gold-standard commands outside Docker

Start the full local stack:

```sh
cp .env.example .env
docker compose -p assessment up -d --build
```

Run migrations if the database volume is new or has been reset:

```sh
docker compose -p assessment exec backend alembic upgrade head
```

Stop the stack:

```sh
docker compose -p assessment down
```

Service URLs:

| Service | URL | Notes |
|---|---|---|
| Frontend | http://localhost:3000 | Root status page and `/documents` UI |
| Documents page | http://localhost:3000/documents | Requires a JWT token in browser storage for API calls |
| Chainlit | http://localhost:8000 | Container starts; backend chat wiring remains a limitation |
| Backend | http://localhost:6100 | FastAPI app |
| Backend health | http://localhost:6100/health | Returns database health |
| Backend docs | http://localhost:6100/docs | OpenAPI docs |
| PostgreSQL | localhost:5432 | `pgvector/pgvector:pg16` |

Document-management endpoints require a JWT:

```sh
curl -s -X POST http://localhost:6100/api/v1/auth/session
```

Use the returned `access_token` as `Authorization: Bearer <token>` for `/api/v1/documents*`. The chat endpoint remains anonymous when `ANONYMOUS_CHAT_ALLOWED=true`; set it to `false` to require the same token for `/api/v1/chat`.

## Verification

Basic smoke checks:

```sh
docker compose -p assessment ps
curl -s http://localhost:6100/health
curl -I http://localhost:6100/docs
curl -I http://localhost:3000
curl -I http://localhost:3000/documents
curl -I http://localhost:8000
```

Last known green verification from the verified branch state:

```text
python3 -m compileall backend/app gold_standard
passed

docker compose -p assessment build backend
passed

docker compose -p assessment exec backend pytest
120 passed, 12 skipped, 4 warnings in 41.03s

npm test --prefix frontend -- --runInBand
1 passed

backend health smoke
{"status":"ok","database":"ok"}
```

Run the deterministic suites:

```sh
docker compose -p assessment exec backend pytest
npm test --prefix frontend -- --runInBand
```

Playwright is not scaffolded in the current frontend package. Do not claim e2e status until a Playwright dependency, config, and spec are added and this command succeeds:

```sh
PLAYWRIGHT_BASE_URL=http://localhost:3000 npx playwright test --prefix frontend
```

## Dependency and Build Reliability Notes

The backend Docker build had two dependency failures that are now documented and repaired:

- `docker-compose.yaml` passes an explicit allow-list of application environment variables into containers rather than injecting every key from the local `.env` file. This avoids accidentally exposing unrelated developer secrets to app containers.
- Initial pip cache/hash corruption was addressed by removing the Docker pip cache mount and installing with:

  ```dockerfile
  RUN pip install --no-cache-dir --default-timeout=180 --retries=10 -r /requirements.txt
  ```

- A later empty wheel payload/hash error occurred during the large `sentence-transformers` / torch dependency chain. The architecture-safe fix was to pin CPU-only `torch==2.9.1+cpu` through the official PyTorch CPU wheel index before installing `sentence-transformers`. This preserves the local CrossEncoder reranking architecture while avoiding CUDA wheel downloads and reducing image fragility, size, and cost.
- The backend Docker build context is the repository root. `.dockerignore` keeps the context small while allowing `backend/`, `gold_standard/`, and `pytest.ini` into the image so scheduled gold evaluation imports work in production-like containers.
- `poppler-utils` and `tesseract-ocr` are runtime system packages, not Python dependencies. They are installed in the backend image for PDF rasterization and OCR fallback.
- Chainlit dependency resolution is intentionally handled with `uv pip install` in `chainlit_app/Dockerfile` to avoid very slow pip resolver backtracking in the Chainlit/OpenTelemetry dependency tree.

## Gold-Standard Evaluation

The `gold_standard/` package exercises the real `/api/v1/chat` path, stores runs/results, writes a Markdown report, and can alert on score deviations.

One-time setup and verification:

```sh
python -m gold_standard.fetch_corpus
python -m gold_standard.verify_expected --search
```

Manual and CI-style runs:

```sh
python -m gold_standard.runner --trigger manual --sample 8
python -m gold_standard.runner --trigger ci --floor 85
```

Do not trust gold scores until the corpus PDFs have been fetched, SHA-256 hashes are pinned in `gold_standard/corpus/corpus_manifest.yaml`, source documents are indexed into the local app, and expected answers have been human-verified. PDFs and generated reports are ignored and must not be committed.

## Security Posture

- No real secrets are committed; `.env.example` uses placeholders.
- JWT session tokens protect document-management endpoints. Anonymous chat is an explicit environment-controlled option.
- Upload validation checks PDF magic bytes, parsed page count, MIME allow-list, and size limits before persistence.
- CORS is environment-driven through `CORS_ALLOWED_ORIGINS`; production should use explicit origins only.
- Database access uses SQLAlchemy/parameterized SQL. The pgvector/full-text retrieval SQL is written with bound parameters.
- Rate limits are enforced per session and per IP from `query_audit_log`, with indexes for the hot-path counts.
- Generated answers pass lexical grounding and exact numeric/dosage grounding before cache eligibility.
- Production storage should use S3 private buckets with KMS encryption and IAM task/Lambda roles, not static AWS keys.

## Scalability Posture

- FastAPI request handling and database access use async SQLAlchemy sessions with a configured connection pool.
- Upload requests persist a document record and are designed around background ingestion; a queue is the production next step for high-volume PDF processing.
- The backend is stateless across replicas; session, cache, audit, grading, and trace data live in PostgreSQL.
- Scheduled jobs are protected by PostgreSQL advisory locks so horizontal replicas do not duplicate cache hygiene, grading, anomaly, or gold-eval jobs.
- Exact and semantic caches reduce repeated retrieval/generation work. Semantic cache rows are scoped by embedding model to avoid cross-model vector comparisons.
- For scale, move PDFs/page images to S3, use RDS Multi-AZ with backups, add RDS Proxy where Lambda is used, and move long-running ingestion to queue-backed workers.

## Current Limitations and Assumptions

- The backend `/api/v1/chat` exists and is tested, but the Chainlit app is not yet wired to it.
- The upload endpoint stores a `processing` document record and the ingestion worker can index it, but the current route does not visibly enqueue that worker in the request path.
- The UI does not yet render Chicago notes-bibliography superscript citations. The backend returns `source_chunk_ids`; the production next step is a citation contract that includes document title, page number, and per-sentence superscript mapping assembled from retrieved metadata rather than generated by the model.
- Responsive UI verification has deterministic source tests, but no browser/device pass has been run in this checklist build. Breakpoints to verify manually are 375, 768, 1024, and 1440 px.
- Playwright e2e is planned, not implemented or run.
- Gold-standard real scores are not trusted until corpus fetch, checksum pinning, indexing, and expected-answer verification are complete.
- Clean-clone validation has not been performed in this checklist build.
- AWS deployment is a documented production plan, not evidence of a live deployment.
- The default local embedding model is `text-embedding-3-small` with `EMBEDDING_DIM=1536`; schema and runtime settings must remain aligned.
- Retrieval defaults are `RETRIEVAL_TOP_K=20`, `RERANK_TOP_N=5`, cosine pgvector search, and RRF with `RRF_K=60`.

## Production AWS Deployment Plan

The target production architecture is AWS with private networking and managed data services:

- **Frontend:** S3 + CloudFront for a static export if the app is made static, or ECS Fargate/App Runner for the current Next.js server runtime.
- **Backend API:** ECS Fargate is the best fit for the current FastAPI container because local reranking, PDF parsing, OCR, and connection pooling benefit from warm containers.
- **Chainlit:** ECS Fargate behind the same ALB once it is wired to `/api/v1/chat`; otherwise omit it from production.
- **Database:** Amazon RDS PostgreSQL 16 with pgvector enabled, Multi-AZ, encrypted storage, automated backups, and restore testing.
- **Object storage:** S3 private buckets for uploaded PDFs and rasterized page images, encrypted with KMS.
- **Secrets:** AWS Secrets Manager or SSM Parameter Store injected at runtime. IAM roles provide S3/Bedrock access; no static AWS access keys.
- **Network boundary:** CloudFront/WAF plus ALB or API Gateway. Application tasks run in private subnets with security groups allowing database access only from backend tasks.
- **Observability:** CloudWatch logs, metrics, traces, dashboards, and alarms for p95 latency, 5xx rate, cache hit rate, grounding failures, cost spikes, anomaly flags, and gold-eval regressions.

Lambda is a strong fit for bursty, event-driven work: ingestion triggers, scheduled grading kicks, corpus-eval triggers, lightweight API handlers, and idle-cost-sensitive jobs. Lambda is not a good default for long-running local model inference, large PDF parsing/OCR, or heavyweight CPU/GPU workloads; those should stay on ECS/Fargate, move to Bedrock-hosted models, or run as managed async workers. If the API is split onto Lambda, use API Gateway + Lambda + RDS Proxy, provisioned concurrency for cold-start-sensitive routes, and keep local model inference out of the function path.

Compute trade-offs:

| Option | Best fit | Trade-off |
|---|---|---|
| Lambda | Bursty jobs, schedulers, lightweight handlers | Cold starts, timeout limits, RDS pooling needs RDS Proxy |
| ECS Fargate | Current containers, PDF/OCR, local reranker | Higher idle floor than Lambda |
| App Runner | Simple container deploys | Less network/control flexibility than ECS |
| EKS | Large multi-service platform | Operational overhead is not justified here |
| EC2 | Full host control | Manual patching/scaling burden |

Amazon Bedrock should be the production model-governance layer where available. Route cheap tasks such as summarization, classification, grading prechecks, and query expansion to fast/low-cost models; reserve stronger models for final grounded answer generation and complex clinical reasoning. Keep `JudgeAgent` reproducible with pinned model, temperature, and rubric version. Track per-model token usage and cost through `MODEL_PRICING_JSON` or a Bedrock-aware equivalent, add budget alerts/anomaly detection, use exact/semantic/prompt caching only after grounding/refusal gates, and preserve exact numeric grounding regardless of model choice.

## CI/CD Plan

There is no `.github/workflows/` directory in the current repository, so CI/CD is planned rather than active.

Recommended pipeline:

- PR checks: backend `pytest`, frontend `npm test`, lint/typecheck where configured, Docker backend build, Alembic migration check.
- Main branch deploy: use explicit `needs:` gates so deploy cannot run unless checks pass.
- Images: build and push backend/frontend/Chainlit images to ECR when containers are retained.
- Infrastructure: deploy VPC, RDS, S3, Secrets Manager/SSM, IAM, ALB/API Gateway, WAF, and CloudWatch with Terraform, CDK, or CloudFormation.
- Migrations: run Alembic as a one-off migration task before backend rollout; fail deployment on migration failure.
- Environments: dev, staging, prod with separate secrets and databases.
- Production release: manual approval, smoke tests after deploy (`/health`, minimal upload, minimal chat), and rollback to the previous image/task definition.
- Optional gate: once the corpus is pinned and expected answers are verified, enforce a gold-eval score floor before production promotion.

More detail is in [DEPLOYMENT.md](./DEPLOYMENT.md) and [build-plans-architecture/ARCHITECTURE (4).md](<./build-plans-architecture/ARCHITECTURE (4).md>).
