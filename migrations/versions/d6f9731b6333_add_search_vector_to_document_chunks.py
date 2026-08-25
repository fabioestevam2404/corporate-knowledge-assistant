"""add search_vector to document_chunks

Revision ID: d6f9731b6333
Revises: 99af947b5740
Create Date: 2026-08-24 16:01:45.964609

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d6f9731b6333"
down_revision: str | Sequence[str] | None = "99af947b5740"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # GENERATED ALWAYS ... STORED — not expressible via SQLAlchemy's
    # portable column types, hence hand-written DDL (see ADR-007: PostgreSQL
    # Full Text Search chosen over a dedicated search engine for the MVP).
    op.execute(
        "ALTER TABLE document_chunks "
        "ADD COLUMN search_vector tsvector "
        "GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED"
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_search_vector ON document_chunks USING gin (search_vector)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_search_vector")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS search_vector")
