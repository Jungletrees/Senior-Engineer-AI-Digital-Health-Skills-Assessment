"""add document_inventory for structure/count questions

Document-structure questions (how many authors, references, tables, figures, pages; which
document contains X) failed even when ordinary text-fact lookup passed, because they were
answered by semantic chunk search instead of a structured fact index. This adds a
one-row-per-document inventory populated deterministically during ingestion, so those
questions are answered from persisted facts and cited to source pages where available.

Additive and cascade-scoped to `documents`; no existing table changes.
"""

from __future__ import annotations

from alembic import op

revision = "0018_document_inventory"
down_revision = "0017_chunk_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_inventory (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID NOT NULL UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
            title TEXT,
            document_type TEXT,
            page_count INTEGER,
            authors TEXT[] NOT NULL DEFAULT '{}',
            author_count INTEGER NOT NULL DEFAULT 0,
            organizations TEXT[] NOT NULL DEFAULT '{}',
            section_headings TEXT[] NOT NULL DEFAULT '{}',
            table_count INTEGER NOT NULL DEFAULT 0,
            figure_count INTEGER NOT NULL DEFAULT 0,
            reference_count INTEGER NOT NULL DEFAULT 0,
            dates TEXT[] NOT NULL DEFAULT '{}',
            numeric_facts JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS document_inventory_document_id_idx ON document_inventory (document_id)")
    op.execute("CREATE INDEX IF NOT EXISTS document_inventory_numeric_facts_gin_idx ON document_inventory USING gin (numeric_facts)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS document_inventory_numeric_facts_gin_idx")
    op.execute("DROP INDEX IF EXISTS document_inventory_document_id_idx")
    op.execute("DROP TABLE IF EXISTS document_inventory")
