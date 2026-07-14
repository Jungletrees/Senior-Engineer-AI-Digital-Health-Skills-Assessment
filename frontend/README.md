# Frontend

This is the Next.js frontend for the Last Mile Health RAG platform. It currently provides the document-management experience at `/documents`: upload validation, progress display, document polling, status rendering, and optimistic delete.

The root page renders the backend project status page from `http://localhost:6100/`. A full browser chat interface with Chicago-style superscript citations is not implemented in this package yet; the backend chat contract exists at `/api/v1/chat`, and the Chainlit container is retained separately.

## Reviewer Status

| Area | Status | Notes |
|---|---|---|
| `/documents` route | Partial | UI exists for upload, progress, document polling, status display, and delete. End-to-end upload-to-indexed verification depends on wiring the backend upload route to enqueue the ingestion worker. |
| API helper layer | Verified complete for deterministic scope | `tests/documentsCore.test.mjs` covers base URL resolution, auth headers, validation, upload progress, polling merge, optimistic delete, and rollback. |
| Browser chat UI | Not complete | No Next.js chat page is implemented. Chainlit is the intended chat surface after backend wiring. |
| Chicago citations | Not complete | No superscript marker or footnote components exist yet. |
| Playwright | Not complete | No dependency, config, or e2e spec is scaffolded. |
| Responsive browser pass | Not complete | Manual/browser checks at 375, 768, 1024, and 1440 px remain to be run. |

## Local Development

```sh
npm install
npm run dev
```

Open http://localhost:3000 for the root status page and http://localhost:3000/documents for the document UI.

Set a non-default backend URL in `frontend/.env.local`:

```sh
NEXT_PUBLIC_API_BASE_URL=http://localhost:6100/api/v1
```

## Tests

```sh
npm test -- --runInBand
```

The current test suite uses Node's built-in test runner against `tests/documentsCore.test.mjs`. It covers upload validation, API helper behavior, upload progress, polling merge behavior, optimistic delete/rollback, and auth-header inclusion.

## Current Limitations

- No Playwright dependency, config, or e2e spec is scaffolded yet.
- No UI-level chat message list, streaming state, superscript citation markers, or Chicago-style footnote list exists in this package.
- Browser/device responsive verification for 375, 768, 1024, and 1440 px remains a manual follow-up.
