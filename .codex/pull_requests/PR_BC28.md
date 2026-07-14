# PR BC28 - Corrective Docs Fold-Back

## Summary
- Folded BC21-BC27 decisions and environment variables into architecture and env docs.
- Updated README/tests-README with Docker build strategy, exact numeric grounding, gold-eval workflow, and Playwright status.
- Added `.codex/handover.json` final handover records for implementation and verification.
- Checklist buildrun follow-up rewrote public-facing docs, added `SUBMISSION_CHECKLIST_STATUS.md`, documented AWS/Lambda/Bedrock deployment planning, and made current UI/worker/e2e limitations explicit.

## Verification
- `python3 -m compileall backend/app gold_standard`
- `docker compose -p assessment exec backend pytest`
- `npm test --prefix frontend -- --runInBand`

## Known Remaining Limitations
- Playwright is planned but not scaffolded or run.
- Chainlit is retained but not wired to `/api/v1/chat`.
- UI-level Chicago superscript citation rendering is incomplete.
- The upload route stores a `processing` record, but worker enqueueing is not visibly wired in the route.
- Clean-clone validation and live AWS deployment have not been performed.
