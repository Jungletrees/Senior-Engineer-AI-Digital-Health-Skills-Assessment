# PR BC28 - Corrective Docs Fold-Back

## Summary
- Folded BC21-BC27 decisions and environment variables into architecture and env docs.
- Updated README/tests-README with Docker build strategy, exact numeric grounding, gold-eval workflow, and Playwright status.
- Added `.codex/handover.json` final handover records for implementation and verification.

## Verification
- `python3 -m compileall backend/app gold_standard`
- `docker compose -p assessment exec backend pytest`
- `npm test --prefix frontend -- --runInBand`
