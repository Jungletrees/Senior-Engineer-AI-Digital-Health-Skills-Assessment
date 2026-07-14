# Frontend

This is the Next.js frontend for the Last Mile Health RAG platform. It provides the reviewer chat workspace at `/` and the document-management experience at `/documents`: upload validation, progress display, document polling, status rendering, and optimistic delete.

Chat is served by the separate Chainlit container on `localhost:8000`, which calls the backend `/api/v1/chat` contract and renders answer-level Chicago-style citation notes.

## Reviewer Status

| Area | Status | Notes |
|---|---|---|
| Root route | Complete | Native reviewer chat workspace wired to FastAPI `/api/v1/chat`. |
| `/documents` route | Implemented | Public local UI exists for upload, progress, document polling, status display, and delete. Upload-to-indexed is covered by the Playwright smoke when the live stack is running. |
| API helper layer | Verified complete for deterministic scope | `tests/documentsCore.test.mjs` covers base URL resolution, public/no-auth API calls, validation, upload progress, polling merge, optimistic delete, and rollback. |
| Browser chat UI | Implemented in Next.js and Chainlit | The Next.js root chat and Chainlit both call FastAPI. Chainlit remains the cited-answer E2E target. |
| Chicago citations | Implemented in Chainlit | Backend citation metadata is rendered as answer-level superscripts and notes. Per-sentence placement remains future work. |
| Playwright | Scaffolded | `frontend/e2e/upload-chainlit-citation.spec.ts` covers upload, indexing, Chainlit question, table-derived value, and cited page note. |
| Responsive browser pass | Not complete | Manual/browser checks at 375, 768, 1024, and 1440 px remain to be run. |

## Local Development

```sh
npm install
npm run dev
```

Open http://localhost:3000 for the document-grounded chat workspace and http://localhost:3000/documents for the public document UI.

Set a non-default backend URL in `frontend/.env.local`:

```sh
NEXT_PUBLIC_API_BASE_URL=http://localhost:6100/api/v1
```

## Tests

```sh
npm test -- --runInBand
npm run playwright:install
PLAYWRIGHT_BASE_URL=http://localhost:3000 npm run test:e2e
```

The current test suite uses Node's built-in test runner against `tests/documentsCore.test.mjs`. It covers upload validation, public/no-auth API helper behavior, upload progress, polling merge behavior, and optimistic delete/rollback.

## Current Limitations

- The chat message list and citation renderer live in Chainlit rather than Next.js.
- Playwright requires a rebuilt live stack and installed browser binaries.
- Browser/device responsive verification for 375, 768, 1024, and 1440 px remains a manual follow-up.
