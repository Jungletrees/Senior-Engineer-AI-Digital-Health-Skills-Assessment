"""add chunk-level thematic metadata, tags, and content kind

The `chunks` table stored only raw content, section path, page, token count, one
embedding, and the generated `content_tsv`. That is one undifferentiated ANN space, so a
comparison / table / numeric / cross-document question could not select the right candidate
bucket (by document, theme, content kind, entity, or metric). This migration adds additive,
filterable metadata alongside the raw content — the content itself is unchanged, so citations
still resolve to truthful source chunks/pages.

- `metadata`     : arbitrary retrieval metadata (title, doc_type, enriched-text inputs)
- `theme_tags`   : coarse topic tags (document_ai, sustainability, ...)
- `entity_tags`  : named entities present (LayoutParser, Chevron, ...)
- `metric_tags`  : unit-bearing numeric facts / important counts
- `content_kind` : prose | table | figure | sparse_visual_page | bibliography | author_block | document_inventory | placeholder_text

GIN indexes make tag/JSONB containment filters cheap; a partial btree indexes `content_kind`.
"""

from __future__ import annotations

from alembic import op

revision = "0017_chunk_metadata"
down_revision = "0016_sem_cache_no_default"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS theme_tags TEXT[] NOT NULL DEFAULT '{}'")
    op.execute("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS entity_tags TEXT[] NOT NULL DEFAULT '{}'")
    op.execute("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS metric_tags TEXT[] NOT NULL DEFAULT '{}'")
    op.execute("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS content_kind TEXT")

    op.execute("CREATE INDEX IF NOT EXISTS chunks_metadata_gin_idx ON chunks USING gin (metadata)")
    op.execute("CREATE INDEX IF NOT EXISTS chunks_theme_tags_gin_idx ON chunks USING gin (theme_tags)")
    op.execute("CREATE INDEX IF NOT EXISTS chunks_entity_tags_gin_idx ON chunks USING gin (entity_tags)")
    op.execute("CREATE INDEX IF NOT EXISTS chunks_metric_tags_gin_idx ON chunks USING gin (metric_tags)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS chunks_content_kind_idx
        ON chunks (content_kind)
        WHERE content_kind IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS chunks_content_kind_idx")
    op.execute("DROP INDEX IF EXISTS chunks_metric_tags_gin_idx")
    op.execute("DROP INDEX IF EXISTS chunks_entity_tags_gin_idx")
    op.execute("DROP INDEX IF EXISTS chunks_theme_tags_gin_idx")
    op.execute("DROP INDEX IF EXISTS chunks_metadata_gin_idx")
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS content_kind")
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS metric_tags")
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS entity_tags")
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS theme_tags")
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS metadata")
