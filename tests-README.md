# Test Execution & Verification Guide (tests-README FILE)

This document is the canonical reference for executing automated tests on the **Last Mile Health RAG** system. It details the setup, tools, and execution procedures for the backend FastAPI suite, the Next.js deterministic test suite, Chainlit client tests, and the Playwright e2e smoke suite.

---

## 1. Testing Architecture Overview

Automated tests are divided into three isolated, progressive layers:

1. **Backend Deterministic Suite (`pytest`):** Validates routes, schemas, database models, computed columns, Alembic migrations, rate limits, and caching systems. Highly optimized, isolated from network requests, and fully mocked.
2. **Frontend Deterministic Suite (`node --test`):** Validates the Next.js document upload helper layer, public document API calls, upload state machinery, deletions, and polling merge behavior without a browser.
3. **End-to-End (E2E) Integration Suite (`Playwright`):** Simulates public browser flows for uploading a generated table-bearing PDF, waiting for indexing, loading Chainlit, asking a table-dependent question, and verifying both the expected table-derived value and cited page note.

## Current Reviewer Test Status

| Tier | Status | Last known result / note |
|---|---|---|
| Backend deterministic full suite | Verified complete | `docker compose -p assessment exec backend pytest` -> `120 passed, 12 skipped, 4 warnings in 41.03s` in the verified BC16-BC28 run. |
| Backend targeted corrective suites | Verified complete | Scheduler singleton, cost, rate-limit indexes, semantic-cache model scope, numeric grounding, anomaly detection, judge reproducibility, gold-standard, and `-m golden_set` suites passed in the verified BC16-BC28 run. |
| Frontend deterministic suite | Verified complete | `npm test --prefix frontend -- --runInBand` passed; latest local run after production-gap changes: `1 passed`. |
| Chainlit client tests | Added | `python3 -m unittest chainlit_app.tests.test_chat -v` covers citation rendering and backend client request construction. |
| Playwright e2e | Scaffolded | `frontend/e2e/upload-chainlit-citation.spec.ts` covers upload-to-indexed-to-Chainlit citation smoke. Requires rebuilt local services and installed Playwright browser binaries. |
| Real gold manual/CI score runs | Not trusted yet | Requires corpus fetch, TOFU checksum pinning, indexing, and human expected-answer verification before running score-floor checks. |
| Clean-clone run | Not complete | Must be run from a fresh clone before claiming reviewer-ready reproducibility. |

---

## 2. Backend Testing (`pytest`)

Backend testing is conducted using `pytest` and `asyncio` to handle asynchronous FastAPI routes and database drivers.

### 2.1 Running Tests Inside Docker (Recommended)
Docker containers are pre-packaged with all required libraries (`poppler-utils`, `tesseract-ocr`). To run tests inside the containerized environment:

*   **Run all deterministic checks:**
    ```sh
    docker compose -p assessment exec backend pytest
    ```

*   **Run with a coverage report:**
    ```sh
    docker compose -p assessment exec backend pytest --cov=app --cov-report=term-missing
    ```

*   **Run a specific test file or directory:**
    ```sh
    docker compose -p assessment exec backend pytest app/tests/test_schema_constraints.py
    ```

*   **Run BC4 rasterization worker verification:**
    ```sh
    docker compose -p assessment exec backend pytest app/tests/test_rasterization.py -vv -s
    ```

*   **Run BC5 chunking and embedding verification:**
    ```sh
    docker compose -p assessment exec backend pytest app/tests/test_chunking.py -vv -s
    ```

*   **Run BC6 bounded ingestion-agent verification:**
    ```sh
    docker compose -p assessment exec backend pytest app/tests/test_ingestion_agent.py -vv -s
    ```

*   **Run BC7 retrieval verification:**
    ```sh
    docker compose -p assessment exec backend pytest app/tests/test_retrieval.py -vv -s
    ```

*   **Run BC8 reranking verification:**
    ```sh
    docker compose -p assessment exec backend pytest app/tests/test_rerank.py -vv -s
    ```

*   **Run BC9 retrieval-agent cascade verification:**
    ```sh
    docker compose -p assessment exec backend pytest app/tests/test_retrieval_agent.py -vv
    ```

*   **Run BC10 orchestrator/generation-assembly verification:**
    ```sh
    docker compose -p assessment exec backend pytest app/tests/test_orchestrator.py -vv
    ```

*   **Run BC11 exact/semantic-cache verification:**
    ```sh
    docker compose -p assessment exec backend pytest app/tests/test_cache.py -vv
    ```

*   **Run BC12 chat verification:**
    ```sh
    docker compose -p assessment exec backend pytest app/tests/test_chat.py -vv
    ```

*   **Run BC13 upload config verification:**
    ```sh
    docker compose -p assessment exec backend pytest app/tests/test_upload_config.py -vv
    ```

*   **Run BC14 guardrail verification:**
    ```sh
    docker compose -p assessment exec backend pytest app/tests/test_guardrails.py -vv
    docker compose -p assessment exec backend pytest app/tests/test_chat.py -vv
    docker compose -p assessment exec backend pytest app/tests/test_cache.py -vv
    ```

*   **Run BC15 auth/rate-limit verification:**
    ```sh
    docker compose -p assessment exec backend pytest app/tests/test_auth.py -vv
    docker compose -p assessment exec backend pytest app/tests/test_rate_limit.py -vv
    docker compose -p assessment exec backend pytest app/tests/test_migrations.py -vv
    docker compose -p assessment exec backend pytest app/tests/test_documents.py -vv
    docker compose -p assessment exec backend pytest app/tests/test_chat.py -vv
    ```

*   **Run BC21-BC28 corrective verification:**
    ```sh
    docker compose -p assessment exec backend pytest app/tests/test_scheduler_singleton.py -vv
    docker compose -p assessment exec backend pytest app/tests/test_cost.py -vv
    docker compose -p assessment exec backend pytest app/tests/test_rate_limit_indexes.py -vv
    docker compose -p assessment exec backend pytest app/tests/test_semantic_cache_model_scope.py -vv
    docker compose -p assessment exec backend pytest app/tests/test_numeric_grounding.py -vv
    docker compose -p assessment exec backend pytest app/tests/test_anomaly_detection.py -vv
    docker compose -p assessment exec backend pytest app/tests/test_judge_reproducibility.py -vv
    docker compose -p assessment exec backend pytest app/tests/test_gold_standard.py -vv
    docker compose -p assessment exec backend pytest -m golden_set -vv
    ```

### 2.2 Running Tests Locally (Without Docker)
If you are developing locally with a Python virtual environment:

1.  **Activate your virtualenv & Install dependencies:**
    ```sh
    cd backend
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
2.  **Execute Pytest:**
    ```sh
    pytest
    ```

### 2.3 Mocking & Environmental Variables
Deterministic tests do not make active calls to external LLMs or vector database providers.
- **LLM/API Mocking:** Pytest fixtures intercept and mock Anthropic (`anthropic`), OpenAI (`openai`), and OpenRouter (`openrouter`) endpoints.
- **Database Isolation:** All tests run inside a PostgreSQL transaction that automatically rolls back when the test terminates, preventing database pollution.
- **BC2 Migration Tests:** `backend/app/tests/test_migrations.py` runs `alembic upgrade head` and `alembic downgrade base` against the containerized Postgres database. `backend/app/tests/test_schema_constraints.py` rebuilds the migration head for constraint checks, then validates generated `content_tsv`, `documents.content_hash` uniqueness, `page_images` uniqueness, `query_audit_log.idempotency_key` uniqueness, `agentops_summary`, and document cascade deletion behavior.
- **BC3/BC4 Document Tests:** `backend/app/tests/test_documents.py` verifies upload validation, deduplication, status/list/delete endpoints, visible background enqueueing of the ingestion worker for new uploads, no duplicate enqueue for indexed duplicates, the BC4 `detect_page_structure` contract, OCR fallback wiring, and the upload-to-rasterization worker path that persists `page_images` rows. `backend/app/tests/test_rasterization.py` validates the instrumented worker transition from `processing` to `indexed`, including page image persistence and chunking metadata. Poppler and Tesseract calls are mocked in deterministic tests; the Docker image includes the real binaries for manual or integration runs.
- **BC5 Chunking/Embedding Tests:** `backend/app/tests/test_chunking.py` verifies chunk size limits, configured overlap behavior, heading/table-aware splitting, deterministic embedding generation, embedding dimension validation, pgvector persistence, and database-generated `content_tsv`. Hosted OpenAI/Voyage embedding calls are not made in deterministic tests; tests inject a fake embedding client, while local development without provider keys uses the deterministic fallback path.
- **BC6 Ingestion Agent Tests:** `backend/app/tests/test_ingestion_agent.py` verifies the page-scaled ingestion iteration cap, the static tool scope, agent trace logging, table-page image parity with the deterministic path, per-page fallback metadata, and prompt-injection/tool-scope containment. Hosted Anthropic calls are not made in deterministic tests; tests inject a scripted model client.
- **BC7 Retrieval Tests:** `backend/app/tests/test_retrieval.py` verifies literal Reciprocal Rank Fusion scoring, pgvector vector retrieval, generated-column full-text lexical retrieval, hybrid ordering, vector-only fallback, deleted-document exclusion, query embedding dimension mismatch, and transaction-local `hnsw.ef_search`.
- **BC8 Rerank Tests:** `backend/app/tests/test_rerank.py` verifies empty-input behavior, sigmoid-bounded score ordering, `top_n` limiting, hosted-provider strategy selection, and explicit failure when a hosted provider is configured without an adapter. Deterministic tests inject fake rerankers and do not download local cross-encoder weights.
- **BC9 Retrieval Agent Tests:** `backend/app/tests/test_retrieval_agent.py` verifies high-confidence no-expansion, low-confidence expansion, reranker-score gating instead of raw RRF `top_score`, malformed expansion fallback, merge/dedup best fused score retention, iteration-bound deterministic fallback, no public page-image route, and trace-context propagation. Deterministic tests inject fake `hybrid_search`, `rerank`, `expand_query`, and `fetch_page_image` functions; no hosted LLM or model-weight download occurs.
- **BC10/BC14 Orchestrator Tests:** `backend/app/tests/test_orchestrator.py` verifies lexical-overlap compaction, document-order restoration, zero-overlap fallback, static import-boundary enforcement, multimodal image attachment, text-only degradation, context-block payload assembly, retrieval failure propagation, and removal of the BC10 output-filter stub after BC14. Tests inject fake retrieval-agent instances and do not call retrieval internals directly.
- **BC11 Cache Tests:** `backend/app/tests/test_cache.py` verifies query normalization/hash equivalence, exact-cache retrieval/generation skip behavior, semantic threshold hit/miss behavior, hit-count/last-used updates, exact TTL expiry, semantic LRU eviction, document-deletion invalidation, prompt-cache control toggling, and write-eligibility false skips. Semantic-cache tests inject deterministic embedding clients and never call hosted embedding APIs.
- **BC12 Chat Tests:** `backend/app/tests/test_chat.py` verifies idempotency duplicate handling, concurrent duplicate suppression, conversation-summary threshold behavior, latest-summary-only context loading, exact/semantic cache hits skipping RetrievalAgent and generation, empty-corpus upload-first behavior, retrieval-unavailable responses, audit finalization, source chunk persistence, and structured citation metadata. Tests inject fake generation clients, fake RetrievalAgent instances, fake embedding clients, and no-op Chainlit step wrappers.
- **BC13 Frontend/Upload Config Tests:** `backend/app/tests/test_upload_config.py` verifies the settings-derived upload-limits endpoint. `npm test --prefix frontend -- --runInBand` runs deterministic Node tests for the `/documents` page source, frontend fetch/XHR helpers, upload validation, upload progress, mocked polling transitions, failed status rendering support, optimistic delete, rollback, and public/no-auth document calls.
- **BC14 Guardrail Tests:** `backend/app/tests/test_guardrails.py` verifies grounded/fabricated answers, leak canaries, PII provenance, empty-answer filtering, tool-result sanitizer delimiter defense, filtered-response cache blocking, input-validation audit rejection, security headers, and configured CORS. No hosted LLMs, hosted embeddings, hosted auth providers, or reranker downloads are used.
- **BC15 Auth/Rate-Limit Tests:** `backend/app/tests/test_auth.py` and `backend/app/tests/test_rate_limit.py` verify JWT issuance/verification, explicit public document-route access for the local reviewer stack, anonymous-chat flag behavior, per-session limits, per-IP limits via `query_audit_log.client_ip`, `Retry-After`, and rate-limit-before-cache behavior. Rate-limit tests use DB fixtures rather than external counters.
- **BC21-BC28 Corrective Tests:** Scheduler singleton tests verify Postgres advisory-lock execution and lock release. Cost/index/cache tests cover `MODEL_PRICING_JSON`, rate-limit indexes, and semantic-cache `embedding_model` scoping/drift cleanup. Numeric grounding tests enforce exact clinical numeric output matching, including 5 ml pass / 15 ml fail and tolerance ignored for generated answers. Anomaly/Judge/Gold tests cover cadence split, reproducible `JudgeAgent` metadata, SQLAlchemy-backed gold eval persistence, verified-question skipping, and rubric/deviation math. Deterministic tests inject fake chat and fake judge clients and never call hosted LLMs.

### 2.4 Current Cycle Verification Log

Latest BC9-BC11 targeted and full backend verification:

```text
docker compose -p assessment exec backend pytest app/tests/test_retrieval_agent.py -vv
8 passed in 8.35s

docker compose -p assessment exec backend pytest app/tests/test_orchestrator.py -vv
9 passed in 0.82s

docker compose -p assessment exec backend pytest app/tests/test_cache.py -vv
9 passed in 7.74s

docker compose -p assessment exec backend pytest
64 passed, 12 skipped, 4 warnings in 20.89s
```

Historical BC12-BC15 image-build issue, now superseded by the BC21-BC28 rebuild:

```text
python3 -m compileall backend/app
passed

npm test --prefix frontend -- --runInBand
1..1
# tests 1
# pass 1
# fail 0
# duration_ms 1696.303333

docker compose -p assessment up -d --build backend frontend
previously failed during backend image build on a pip wheel hash/download error.
The current backend image build is repaired by using no pip cache mount and a CPU-only torch wheel before sentence-transformers.
```

BC21-BC28 corrective verification status:

```text
docker compose -p assessment build backend
passed; backend image includes CPU-only torch and gold_standard package

docker compose -p assessment exec backend pytest app/tests/test_scheduler_singleton.py -vv
3 passed in 2.60s

docker compose -p assessment exec backend pytest app/tests/test_cost.py app/tests/test_numeric_grounding.py app/tests/test_anomaly_detection.py app/tests/test_judge_reproducibility.py -vv
15 passed in 0.83s

docker compose -p assessment exec backend pytest app/tests/test_rate_limit_indexes.py -vv
1 passed in 1.17s

docker compose -p assessment exec backend pytest app/tests/test_semantic_cache_model_scope.py -vv
2 passed in 2.54s

docker compose -p assessment exec backend pytest app/tests/test_gold_standard.py -vv
4 passed in 1.55s

docker compose -p assessment exec backend pytest -m golden_set -vv
1 passed, 131 deselected, 1 warning in 1.81s

docker compose -p assessment exec backend pytest
120 passed, 12 skipped, 4 warnings in 41.03s

npm test --prefix frontend -- --runInBand
1 passed

docker compose -p assessment exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:6100/health', timeout=5).read().decode())"
{"status":"ok","database":"ok"}
```

Gold-eval manual/CI floor commands require the corpus PDFs to be fetched, checksum-pinned, indexed, and human-verified first:

```sh
python -m gold_standard.fetch_corpus
python -m gold_standard.verify_expected --search
python -m gold_standard.runner --trigger manual --sample 8
python -m gold_standard.runner --trigger ci --floor 85
```

---

## 3. Frontend Testing (Node Test Runner)

Frontend deterministic tests verify the `/documents` page source and client-side validation/API helper behavior without a browser or hosted services.

### 3.1 Running Frontend Tests
To run deterministic frontend tests:

*   **Using npm commands from the project root:**
    ```sh
    npm test --prefix frontend -- --runInBand
    ```

*   **Running directly from the frontend directory:**
    ```sh
    cd frontend
    npm install
    npm test -- --runInBand
    ```

---

## 3.5 Chainlit Client Tests

Chainlit client tests use Python's built-in `unittest` runner with a stubbed Chainlit module and fake HTTP client:

```sh
python3 -m unittest chainlit_app.tests.test_chat -v
```

---

## 4. End-to-End Integration Tests (`Playwright`)

Playwright tests execute in a real headless browser environment to ensure backend services, relational databases, Chainlit, and frontend components communicate correctly. The current smoke spec generates its own table-bearing PDF fixture at runtime, so no PDF binary is committed.

### 4.1 Prerequisites
Before running E2E tests, ensure the local Docker containers are running and healthy:
```sh
docker compose -p assessment up -d --build
```

Make sure Playwright browsers are installed locally (or inside your execution host):
```sh
npm --prefix frontend run playwright:install
```

Set `PLAYWRIGHT_BASE_URL` in the shell when running specs against a non-default frontend URL:

```sh
PLAYWRIGHT_BASE_URL=http://localhost:3000 npm --prefix frontend run test:e2e
```

Optional URL overrides:

```sh
PLAYWRIGHT_BASE_URL=http://localhost:3000 \
PLAYWRIGHT_API_BASE_URL=http://localhost:6100/api/v1 \
PLAYWRIGHT_CHAINLIT_BASE_URL=http://localhost:8000 \
npm --prefix frontend run test:e2e
```

### 4.2 Playwright Commands
Use these commands to execute the E2E suite and verify the complete ingestion-to-citation-retrieval pipeline:

*   **Execute all E2E specs:**
    ```sh
    npm --prefix frontend run test:e2e
    ```

*   **Execute Playwright with the interactive UI runner (highly recommended for local debugging):**
    ```sh
    npm --prefix frontend run test:e2e -- --ui
    ```

*   **View test reports:**
    ```sh
    npm --prefix frontend run playwright:report
    ```

---

## 5. Dependency and Build Reliability Notes

- The backend Docker build originally failed on pip cache/hash corruption. The fix is to install requirements without a pip cache mount:

    ```dockerfile
    RUN pip install --no-cache-dir --default-timeout=180 --retries=10 -r /requirements.txt
    ```

- A later empty wheel payload/hash failure occurred in the `sentence-transformers` / torch dependency chain. The backend now pins CPU-only `torch==2.9.1+cpu` via the official PyTorch CPU wheel index before `sentence-transformers`, preserving the local CrossEncoder reranker while avoiding CUDA wheel downloads.
- The backend image is built from the repository root with `.dockerignore` allowing `backend/`, `gold_standard/`, and `pytest.ini` into the image. This is required so scheduled gold evaluation imports work in production-like containers.
- `poppler-utils` and `tesseract-ocr` are required at the container/system layer for PDF rasterization and OCR. They are mocked in deterministic tests but installed in the backend image for manual and integration runs.
- The Chainlit image uses `uv pip install --system --no-cache -r requirements.txt` to avoid very slow pip resolver backtracking in the Chainlit/OpenTelemetry dependency tree.

---

## 6. Troubleshooting Test Environments

*   **Error: Database Connection Refused / `ConnectionRefusedError`**
    *   *Cause:* The test runner is trying to connect to a Postgres container that is down or uninitialized.
    *   *Fix:* Make sure Postgres is up (`docker compose ps`) or configure the database URL env var (e.g., `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/assessment_test`) in your test shell.
*   **Error: Missing Poppler/Tesseract binaries on local run**
    *   *Cause:* The ingestion pipeline relies on system utilities for OCR and page rasterization.
    *   *Fix:* Run tests inside the Docker container (`docker compose exec backend pytest`) or install poppler/tesseract locally:
        *   *Ubuntu/Debian:* `sudo apt-get install poppler-utils tesseract-ocr`
        *   *macOS (Homebrew):* `brew install poppler tesseract`
*   **Error: Playwright browsers missing**
    *   *Fix:* Execute `npm --prefix frontend run playwright:install` within the target environment before initiating E2E runs.
