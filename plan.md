# Development Build Plan (plan.md)

## Current Status: [ ] In Progress
**Active Build Cycle:** BC3 — PDF Upload Endpoint & Validation Limits

---

## 📅 Completed Cycles
- [x] **BC0 — Verify Starter Repo Integrity** (All services healthy, table test-fixture PDF available)
- [x] **BC1 — Scaffolding & Multi-Agent Orchestration Commit** (All 12 files verified, committed with clean Git tracking)
- [x] **BC2 — Database Schema & Alembic Migrations** (Alembic extensions, core tables, exact/semantic caches, logging, grading view, and constraints 100% verified and committed)

---

## 🎯 Objectives (BC3)
Build the secure backend `/api/v1/documents` endpoint that accepts a PDF file upload, enforces size/page count/MIME-type validations at the API boundary, persists metadata into the `documents` table with `status=processing`, and handles content-hash deduplication. Create `GET` and `DELETE` endpoints for document polling, list display, and cascading delete management.

---

## 📋 Build Cycle Plan (BC3)

### Phase 1: Planning & Ingestion (Orchestrator)
- [x] Read `/build-plans-architecture/BUILD_PLAN.md` and `/build-plans-architecture/ARCHITECTURE.md` §4.
- [x] Update `plan.md` to initialize `BC3` objectives and test targets.

### Phase 2: Build Implementation (Backend Build Agent)
- [ ] **Task 2.1**: Implement `POST /api/v1/documents` async FastAPI endpoint accepting a multipart file upload.
- [ ] **Task 2.2**: Implement strict sequential validation at the API edge (before full database writing/processing):
  - Check file size against `MAX_PDF_SIZE_MB` (reject `413`).
  - Verify file headers via magic-byte checking (reject non-PDF fake extensions with `415`).
  - Read page count cheaply (e.g., via `pdfplumber` metadata) and validate against `MAX_PDF_PAGES` (reject `413`).
- [ ] **Task 2.3**: Implement `SHA-256` content-hash computation on upload.
- [ ] **Task 2.4**: Implement idempotent content-hash dedup: if a matching hash already exists in the database and is `status=indexed`, short-circuit and return its existing ID and status rather than re-creating.
- [ ] **Task 2.5**: Implement local storage writing (`UPLOAD_STORAGE_BACKEND=local`) for new PDFs.
- [ ] **Task 2.6**: Implement read endpoints `GET /api/v1/documents/{document_id}` (polling) and `GET /api/v1/documents` (documents listing).
- [ ] **Task 2.7**: Implement `DELETE /api/v1/documents/{document_id}` using existing Postgres cascading deletes.
- [ ] **Task 2.8**: Add a clear placeholder stub for JWT authentication dependencies, noting that full auth lands in `BC15`.

### Phase 3: Testing & Verification (Test Agent)
- [ ] **Task 3.1**: Write backend unit tests (`test_upload_validation.py`) verifying:
  - File header magic-byte validation correctly rejects a renamed `.txt` or `.png` renamed to `.pdf` with `415`.
  - Oversized files (exceeding `MAX_PDF_SIZE_MB`) are correctly rejected with `413`.
  - Oversized page counts (exceeding `MAX_PDF_PAGES`) are correctly rejected with `413`.
- [ ] **Task 3.2**: Write integration tests (`test_upload_integration.py`) verifying:
  - Successful upload of a valid PDF creates a `documents` row with `status=processing`.
  - Repeat upload of an identical PDF triggers idempotent short-circuit (dedup).
  - Status polling (`GET`) and listing returns correct metadata and statuses.
  - Document deletion (`DELETE`) removes physical file and cascades cleanly across SQL rows.
- [ ] **Task 3.3**: Execute the tests inside the backend container to confirm a green state.

### Phase 4: Workflow Tracking & Commit (GitPR Agent)
- [ ] Stage and commit upload controllers, service schemas, and tests in logical micro-commits.
- [ ] Generate the pull request draft at `.codex/pull_requests/PR_BC3.md`.

### Phase 5: Cycle Closure (Orchestrator)
- [ ] Mark BC3 as `[x] Completed` in `plan.md`.
- [ ] Transition to structure detection and page rasterization (BC4).

---

## 🧪 Test Coverage Goals
*   **Unit Tests**: Validation gates (size, MIME, page count) cleanly tested with robust mock files.
*   **Integration Tests**: File upload, dedup, read, and delete endpoints 100% covered.

---

## 🚀 Git & PR Tracking
*   **GitPR Agent Status**: Ready.
*   **Primary Branch**: `master`
