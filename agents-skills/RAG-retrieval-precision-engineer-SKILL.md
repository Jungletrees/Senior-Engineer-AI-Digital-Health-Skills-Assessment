---
name: rag-retrieval-precision-engineer
description: Own retrieval-side corrective patches from the local stress-test report: query intent analysis, document-aware retrieval quotas, metadata-filtered ANN pools, thematic vector search, reranking diversity, and citation coverage for cross-document RAG questions. Use this skill when improving hybrid_search, RetrievalAgent, rerank assembly, and source-selection behavior.
---

# RAG Retrieval Precision Engineer - Corrective Skill

## 0. Your mandate, in one sentence

You make retrieval select the right evidence: classify the user's question, search the right ANN/lexical/metadata pools, preserve document diversity, and return enough cited context for accurate synthesis without weakening the existing RAG safety gates.

This skill is grounded in:

```text
stress-test-results/RAG_STRESS_ENGINEERING_HANDOFF.md
```

Use that report as the evidence base. Do not rerun the whole stress test unless targeted samples have improved.

---

## 1. Non-negotiable project constraints

- Keep Postgres + pgvector HNSW as the vector store. Do not introduce a second vector database.
- Preserve `SET LOCAL hnsw.ef_search` inside the same transaction as ANN queries.
- Preserve the existing hybrid retrieval shape unless a measured patch justifies a local extension: vector search + full-text search + RRF + rerank.
- RRF is ranking fusion only. Never treat raw RRF score as a 0-1 confidence signal.
- Keep rerank confidence semantics owned by the reranker result, not by ANN distance alone.
- Do not download reranker weights or call hosted providers in deterministic tests.
- Keep `/chat` idempotency, rate-limit, cache, retrieval, generation, and output-filter ordering intact unless a deliberate change is documented and tested.

---

## 2. Stress-test findings you own

The run failed especially on:

- Cross-document synthesis: `SYN-01`, `SYN-03`, `SYN-05`, `SYN-06`, `SYN-18`.
- Semantic inference: `INF-09`, `INF-25`, and many LayoutParser concept questions.
- Citation coverage: 35 missing expected document citations, 43 missing expected page citations.

Root cause: retrieval currently builds one flat candidate pool. A single dominant document can consume the final context, and topically related chunks can beat the specific evidence needed for a comparison or absent-attribute question.

---

## 3. Query analyzer contract

Add a deterministic query analyzer before retrieval. Keep it small, typed, and testable.

Recommended output:

```python
class QueryAnalysis(BaseModel):
    intent: Literal[
        "single_fact",
        "numeric_fact",
        "multi_document_comparison",
        "all_documents",
        "table_or_figure",
        "document_inventory",
        "out_of_scope_current_fact",
        "entity_present_attribute_absent",
        "unknown",
    ]
    document_aliases: list[str]
    required_document_ids: list[UUID]
    required_entities: list[str]
    requested_attributes: list[str]
    requires_numeric_evidence: bool
    requires_page_citation: bool = True
```

Alias handling must recognize:

- `Document 1`, `Doc 1`, `the first document`
- `Document 2`, `Lorem Ipsum`
- `Document 3`, `LayoutParser`
- filename/title fragments
- "all three documents" and "across the uploaded documents"

Prefer deterministic rules plus existing document metadata. Do not use a hosted model for query analysis in tests.

---

## 4. Document-aware retrieval

For `multi_document_comparison` and `all_documents`:

- Run retrieval per required document with a per-document quota.
- Do not let one document fill the final `top_n`.
- Require at least one candidate per required document unless evidence is genuinely absent.
- Preserve page numbers and section paths through candidate merging.
- Add trace details showing required documents and coverage.

For table/figure/document-inventory intents:

- Search inventory facts and metadata-tagged chunks before ordinary semantic chunks.
- Prefer `content_kind IN ('table', 'figure', 'document_inventory', 'author_block', 'bibliography')` when the query asks for those structures.

For numeric facts:

- Prefer candidates with `metric_tags` or unit-bearing numeric facts.
- Penalize candidates that match the entity but contain no requested numeric/unit evidence.

---

## 5. Metadata-filtered ANN pools

When metadata exists, use multiple candidate pools instead of one undifferentiated HNSW query:

- raw content embedding pool
- thematic embedding pool, if implemented
- lexical full-text pool
- metadata-filtered pool
- numeric/table/figure pool

Merge pools using quota-aware RRF or MMR:

- Preserve diversity by document.
- Preserve diversity by `content_kind`.
- Keep exact chunk ids deduplicated.
- Prefer higher rerank scores inside each quota.

Do not overcomplicate this with a new service. This is a local retrieval algorithm inside the existing FastAPI process.

---

## 6. Reranking and context assembly

The reranker should score query/chunk relevance, but final assembly must also enforce coverage constraints:

- Cross-document questions need enough final chunks to support the comparison.
- If required documents are missing after rerank, attempt a bounded second retrieval for missing documents before generation.
- Increase final context size only for intents that need it. Avoid globally increasing `rerank_top_n` in a way that harms latency/cost.
- Record the final selected document/page coverage in `agent_trace_log`.

Do not use generation prompts as a substitute for missing evidence. If retrieval did not supply the supporting chunks, the answer should refuse or say evidence is missing.

---

## 7. Testing you own

Add deterministic tests for:

- Query analyzer intent and document alias detection.
- Per-document retrieval quotas for "all three documents" questions.
- Metadata-filtered search prefers table/inventory chunks for table/count questions.
- Numeric questions prefer unit-bearing candidates.
- Missing required document triggers bounded recovery retrieval.
- Final context assembly preserves chunk ids and page numbers.
- RRF remains ordering-only; confidence gate still uses rerank score.
- No hosted providers or reranker downloads in deterministic tests.

Targeted stress samples:

```bash
python3 scripts/rag_stress_benchmark.py --skip-upload --rotate-client-ip \
  --id SYN-01 --id SYN-03 --id SYN-05 --id SYN-06 --id SYN-18 \
  --id INF-09 --id INF-25
```

---

## 8. Definition of done

- [ ] Query analysis is typed, deterministic, and tested.
- [ ] Retrieval enforces document and content-kind coverage for comparison/table/inventory intents.
- [ ] Metadata-filtered ANN/lexical pools are merged without losing citation metadata.
- [ ] Targeted stress samples show better document/page recall.
- [ ] Full deterministic backend tests remain green.
- [ ] Any architecture divergence is logged in `ARCHITECTURE (4).md` §18.
