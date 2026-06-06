"""add_message_status_and_sequence

Revision ID: 6b1d8d7026bc
Revises: 8c3dc169c23f
Create Date: 2026-06-06 18:55:13.142289
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6b1d8d7026bc"
down_revision: str | None = "8c3dc169c23f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add columns as nullable first
    message_status = sa.Enum(
        "streaming", "complete", "interrupted", "failed", name="message_status"
    )
    message_status.create(op.get_bind(), checkfirst=True)
    op.add_column("messages", sa.Column("status", message_status, nullable=True))
    op.add_column("messages", sa.Column("sequence_number", sa.Integer(), nullable=True))

    # 2. Populate existing rows
    op.execute("UPDATE messages SET status = 'complete' WHERE status IS NULL")
    op.execute("""
        WITH ordered_messages AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY conversation_id
                       ORDER BY created_at ASC
                   ) as row_num
            FROM messages
        )
        UPDATE messages
        SET sequence_number = ordered_messages.row_num
        FROM ordered_messages
        WHERE messages.id = ordered_messages.id
    """)

    # 3. Alter columns to be non-nullable
    op.alter_column("messages", "status", nullable=False)
    op.alter_column("messages", "sequence_number", nullable=False)

    # 4. Add unique constraint
    op.create_unique_constraint(
        "uq_conversation_message_sequence", "messages", ["conversation_id", "sequence_number"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_conversation_message_sequence", "messages", type_="unique")
    op.drop_column("messages", "sequence_number")
    op.drop_column("messages", "status")

    # Drop enum type
    sa.Enum(name="message_status").drop(op.get_bind(), checkfirst=False)
