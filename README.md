
## Last Mile Health — Senior Full-Stack Engineer, AI & Digital Health Practice Assessment

Welcome to the practice assessment for the **Senior Full-Stack Engineer, AI & Digital Health** position at Last Mile Health.

This repository contains the starter code for your submission. Please read everything below before you begin.

---

### How to Run the Project Locally

> **Start here.** The full assessment instructions are served by the application itself — run the project first, then visit the frontend URL below.

1. **Build and start all services:**

   ```sh
   docker compose -p assessment up -d --build
   ```

2. **Access the application:**

   | Service | URL |
   |---|---|
   | Frontend / **Instructions** | [http://localhost:3000](http://localhost:3000) |
   | Frontend / **Documents** | [http://localhost:3000/documents](http://localhost:3000/documents) |
   | Chainlit (Chat UI) | [http://localhost:8000](http://localhost:8000) |
   | Backend (API) | [http://localhost:6100](http://localhost:6100) |
   | Database (PostgreSQL) | `localhost:5432` |

   Open [http://localhost:3000](http://localhost:3000) in your browser to read the full assessment requirements.

   Document-management endpoints (`/api/v1/documents*`) require a signed JWT session token after BC15. Issue one with `POST /api/v1/auth/session` and send it as `Authorization: Bearer <token>`. The chat endpoint remains open to anonymous clients when `ANONYMOUS_CHAT_ALLOWED=true`; set it to `false` to require the same JWT for `/api/v1/chat`.

3. **Stop all services:**

   ```sh
   docker compose -p assessment down
   ```

### Testing

Backend and frontend deterministic checks:

```sh
docker compose -p assessment exec backend pytest
npm test --prefix frontend -- --runInBand
```

The backend image includes Poppler and Tesseract for PDF rasterization/OCR. If backend tests reset the database during migration checks, restore the app database with:

```sh
docker compose -p assessment exec backend alembic upgrade head
```

Playwright is not scaffolded in the current frontend package. When e2e specs are added, run them with the target frontend URL in the shell, not `.env.example`:

```sh
PLAYWRIGHT_BASE_URL=http://localhost:3000 npx playwright test --prefix frontend
```

### Gold-Standard Evaluation

The `gold_standard/` package contains the scheduled regression-eval workflow. Do not commit downloaded PDFs.

```sh
python -m gold_standard.fetch_corpus
python -m gold_standard.verify_expected --search
python -m gold_standard.runner --trigger manual --sample 8
python -m gold_standard.runner --trigger ci --floor 85
```

The first corpus fetch pins SHA-256 values into `gold_standard/corpus/corpus_manifest.yaml`; scores should not be trusted until expected answers are verified and `verified:false` questions remain skipped.

---

### Submission Guidelines
- Fork this repository to your own GitHub account.
- Submit your solution by sharing a **link to your forked repository**.
- You have **3 days** to complete and submit your work.
- Include clear local setup instructions and a production deployment plan in your submission (see the instructions page for details).
- Do not push any changes to the repository after the deadline.


---
