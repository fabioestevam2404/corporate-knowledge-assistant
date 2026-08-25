"""create users table

Revision ID: 9bc3abba27de
Revises: d6f9731b6333
Create Date: 2026-08-24 22:11:13.366092

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9bc3abba27de"
down_revision: str | Sequence[str] | None = "d6f9731b6333"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Note: autogenerate also proposed dropping document_chunks.search_vector
    # and its HNSW/GIN indexes — a false positive, because those are
    # hand-written DDL (see migration d6f9731b6333) deliberately not
    # represented in ChunkModel (it's a DB-generated column, never written
    # from Python). That part of the diff was removed from this migration.
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")
