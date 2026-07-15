---
name: rag-ingestion-metadata-engineer
description: Own the ingestion-side RAG precision fixes from the local stress-test report: chunk-level thematic metadata, document/page inventory facts, sparse visual PDF extraction, numeric fact capture, and pgvector-ready metadata persistence. Use this skill when improving how uploaded PDFs are chunked, annotated, embedded, indexed, and reindexed without changing the project stack or deterministic-test guarantees.
---

# RAG Ingestion Metadata Engineer - Corrective Skill

## 0. Your mandate, in one sentence

You make the vector index precise before retrieval ever runs: enrich each stored chunk/page/document with deterministic metadata, structured facts, content-kind labels, numeric facts, and retrieval text that lets pgvector/HNSW find the right evidence instead of relying on raw chunk text alone.

This skill is driven by the local report:

```text
stress-test-results/RAG_STRESS_ENGINEERING_HANDOFF.md
```

Do not commit the stress corpus, generated reports, or local benchmark runner. They are local-only evidence.

---

## 1. Non-negotiable project constraints

- Preserve the existing stack: FastAPI, SQLAlchemy async sessions, explicit `text()` SQL where the repo already uses SQL, Alembic, Postgres 16, pgvector HNSW, Next.js, Chainlit.
- Do not introduce raw `asyncpg` in app code. Keep database work in the repo's SQLAlchemy async style.
- Do not add hosted LLMs, hosted embeddings, S3, auth providers, or reranker downloads to deterministic tests.
- Keep raw chunk `content` intact for citation display. Metadata may enrich retrieval, but citations must still resolve to truthful source chunks/pages.
- Keep app behavior compatible with existing caches, grounding checks, scheduler jobs, and `query_audit_log` / `agent_trace_log`.
- Log any architecture divergence in `build-plans-architecture/ARCHITECTURE (4).md` §18 in the same patch.

---

## 2. Stress-test findings you own

The completed stress run showed:

- Chevron sparse/visual facts were often missed (`NUM-01`, `NUM-02`, `NUM-03`, `INF-09`, `INF-15`, `INF-19`).
- Document-structure questions failed despite ordinary text facts passing (`SYN-05`, `NUM-18`, `NUM-19`, `NUM-20`, `NUM-21`).
- Cross-document synthesis lacked enough metadata to retrieve balanced evidence across all documents (`SYN-01`, `SYN-03`, `SYN-06`).

The current `chunks` schema stores raw content, page number, section path, token count, a single embedding, and `content_tsv`. That is not enough for precise retrieval across ANN buckets.

---

## 3. Metadata model to implement conservatively

Prefer additive schema changes. Do not rewrite existing migrations.

Recommended chunk-level fields:

- `metadata JSONB NOT NULL DEFAULT '{}'::jsonb` mapped as `metadata_` in SQLAlchemy to avoid clashing with `Base.metadata`.
- `theme_tags TEXT[] NOT NULL DEFAULT '{}'`
- `entity_tags TEXT[] NOT NULL DEFAULT '{}'`
- `metric_tags TEXT[] NOT NULL DEFAULT '{}'`
- `content_kind TEXT` with values such as:
  - `prose`
  - `table`
  - `figure`
  - `sparse_visual_page`
  - `placeholder_text`
  - `bibliography`
  - `author_block`
  - `document_inventory`
- Optional, if it can be done without destabilizing tests: `thematic_embedding VECTOR(1536)` with its own HNSW index.

Recommended indexes:

- GIN on `metadata`
- GIN on `theme_tags`
- GIN on `entity_tags`
- GIN on `metric_tags`
- HNSW on `thematic_embedding` only if the column is implemented.

Do not add metadata fields without tests that prove inserts, reads, and retrieval candidate construction preserve them.

---

## 4. Retrieval text construction

Build embeddings from metadata-enriched retrieval text, not raw chunk text alone. The enriched string should be deterministic and compact:

```text
document_title: <title or filename>
document_type: <academic_paper|corporate_report|placeholder|unknown>
page: <page_number>
section_path: <section_path>
content_kind: <kind>
themes: <comma-separated theme tags>
entities: <comma-separated entity tags>
metrics: <unit-bearing metrics and important counts>

<raw chunk content>
```

Store the metadata used to produce this string. Do not expose the enriched text as the quoted source unless explicitly intended; citations should still display source-grounded snippets from `content`.

---

## 5. Document inventory / fact index

Add an ingestion product that answers document-structure questions without abusing semantic chunk search.

Minimum facts to extract and persist:

- title or best document label
- document type
- page count
- author names and author count
- organization attribution
- institution count where present
- section heading inventory
- table count and table summaries
- figure count and figure summaries
- bibliography/reference count
- dates and publication metadata
- extracted numeric facts with units and page numbers

Implementation options:

- A normalized `document_facts` / `document_inventory` table.
- Or chunk rows with `content_kind='document_inventory'` plus typed metadata.

Choose the option that fits existing repo patterns with the least schema risk. If a new table is added, make it additive and covered by Alembic tests.

---

## 6. Sparse visual PDF handling

The Chevron page failures show that sparse visual pages need first-class treatment.

Patch expectations:

- OCR page images when native text yield is low, even if the PDF has some text.
- Preserve large numeral/caption pairs as structured facts.
- Extract unit-bearing facts such as `2.5 kg CO2e/boe`, `~70%`, `2020`, `2022`.
- Mark pages/chunks with `content_kind='sparse_visual_page'`.
- Generate deterministic page summaries from extracted/OCR text; do not require a hosted model in deterministic tests.
- Use page images as support only after retrieval selects the page; do not rely on generation to discover visual facts from unindexed images.

---

## 7. Testing you own

Add deterministic tests for:

- Alembic migration up/down for metadata fields and indexes.
- Chunk insert/read preserving metadata and tags.
- Enriched retrieval text includes title, page, section, content kind, themes, entities, and metrics.
- Sparse visual PDF/OCR fallback captures Chevron-like unit-bearing facts.
- Document inventory answers table/figure/author/reference-count queries from persisted facts.
- Reindex/backfill behavior does not duplicate chunk rows or stale metadata.
- No external network calls in tests.

Targeted stress samples after implementation:

```bash
python3 scripts/rag_stress_benchmark.py --skip-upload --rotate-client-ip \
  --id NUM-01 --id NUM-02 --id NUM-03 --id NUM-20 --id NUM-21 --id SYN-05
```

Do not rerun the full 100-question stress suite unless targeted samples prove the patch is stable.

---

## 8. Definition of done

- [ ] Metadata schema is additive, migrated, indexed, and tested.
- [ ] Ingestion persists deterministic chunk/page/document metadata.
- [ ] Sparse visual pages produce searchable numeric facts.
- [ ] Document-structure questions have a retrievable inventory source.
- [ ] Existing deterministic backend tests remain green.
- [ ] Targeted stress samples improve without introducing `500`, `429`, or `in_flight` artifacts.
- [ ] Any architecture divergence is logged in `ARCHITECTURE (4).md` §18.
