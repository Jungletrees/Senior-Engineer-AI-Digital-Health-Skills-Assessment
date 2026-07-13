# Development Build Plan (plan.md)

## Current Status: [ ] In Progress
**Active Build Cycle:** BC1 — Scaffolding & Multi-Agent Orchestration Commit

---

## 🎯 Objectives (BC1)
Establish the working-agreement scaffolding this entire project runs on:
1. Commit `ARCHITECTURE (4).md` to the root directory as the canonical single source of truth (`ARCHITECTURE.md`).
2. Establish the specialized multi-agent operating specifications (`agents.md`, `GEMINI.md`, `agents-skills/skills.md`, `agents-skills/test-engineer-SKILL.md`, `tests-README.md`).
3. Commit the updated master `BUILD_PLAN.md` and local `.env.example` to the root.
4. Establish an automated repository hygiene test suite to enforce and verify that all necessary scaffolding documents are present and correctly located.

---

## 📋 Build Cycle Plan

### Phase 1: Planning & Ingestion (Orchestrator)
- [x] Read `/build-plans-architecture/BUILD_PLAN.md` and `/build-plans-architecture/ARCHITECTURE (4).md`.
- [x] Update `plan.md` to initialize `BC1` goals, file changes, and testing targets.

### Phase 2: Build Implementation (Build Agents)
- [ ] **Task 2.1**: Consolidate `build-plans-architecture/ARCHITECTURE (4).md` and commit it as `ARCHITECTURE.md` in the repository root.
- [ ] **Task 2.2**: Ensure `GEMINI.md` and `agents.md` are positioned at the root.
- [ ] **Task 2.3**: Verify that `agents-skills/Backend-engineer-SKILL.md`, `agents-skills/Frontend-engineer-SKILL.md`, `agents-skills/ML-engineer-SKILL.md`, `agents-skills/test-engineer-SKILL.md`, and `agents-skills/skills.md` are in place.
- [ ] **Task 2.4**: Position `.env.example`, `tests-README.md`, and `DEPLOYMENT.md` at the root.

### Phase 3: Testing & Verification (Test Agent)
- [ ] **Task 3.1**: Create a repository hygiene test suite (`backend/tests/test_repo_hygiene.py`) that uses `pytest` to programmatically assert the existence of all 11 critical scaffolding files and verify they are not empty.
- [ ] **Task 3.2**: Execute the hygiene test suite inside the backend container to confirm a green state.
- [ ] **Task 3.3**: Ensure `tests-README.md` is updated with instructions for running hygiene tests.

### Phase 4: Git tracking & Commit (GitPR Agent)
- [ ] **Task 4.1**: Stage the modified `.gitignore` and untrack the empty `.env` file.
- [ ] **Task 4.2**: Stage and commit files in logical micro-groups with conventional messages:
  - `docs: commit ARCHITECTURE.md as root decision record`
  - `docs: establish multi-agent guidelines and skilled agent profiles`
  - `docs: commit master BUILD_PLAN.md and DEPLOYMENT.md`
  - `test: add automated repository hygiene test suite`
- [ ] **Task 4.3**: Compile the PR description draft and save it to `.codex/pull_requests/PR_BC1.md`.

### Phase 5: Cycle Closure (Orchestrator)
- [ ] Update `plan.md` status of BC1 to `[x] Completed`.
- [ ] Transition to database schema initialization (BC2).

---

## 🧪 Test Coverage Goals
*   **Repo Hygiene Test Case (`test_repo_hygiene.py`)**: 100% assertions green on standard path parameters.

---

## 🚀 Git & PR Tracking
*   **GitPR Agent Status**: Pending Handover.
*   **Primary Branch**: `master`
