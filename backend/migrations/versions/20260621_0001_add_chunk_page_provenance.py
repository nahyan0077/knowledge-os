"""add page provenance to document chunks

Revision ID: 20260621_0001
Revises: 2f32957df35e
Create Date: 2026-06-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260621_0001"
down_revision: str | None = "2f32957df35e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("document_chunks", sa.Column("page_start", sa.Integer(), nullable=True))
    op.add_column("document_chunks", sa.Column("page_end", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_chunks", "page_end")
    op.drop_column("document_chunks", "page_start")
