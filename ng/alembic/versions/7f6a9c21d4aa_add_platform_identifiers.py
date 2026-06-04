"""add platform identifiers

Revision ID: 7f6a9c21d4aa
Revises: 3e1f8a2c9b05
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "7f6a9c21d4aa"
down_revision = "3e1f8a2c9b05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("papers") as batch_op:
        batch_op.add_column(sa.Column("arxiv_id", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("openreview_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("dblp_key", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("openalex_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("semantic_scholar_id", sa.String(length=255), nullable=True))

    with op.batch_alter_table("authors") as batch_op:
        batch_op.add_column(sa.Column("openalex_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("semantic_scholar_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("dblp_pid", sa.String(length=100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("authors") as batch_op:
        batch_op.drop_column("dblp_pid")
        batch_op.drop_column("semantic_scholar_id")
        batch_op.drop_column("openalex_id")

    with op.batch_alter_table("papers") as batch_op:
        batch_op.drop_column("semantic_scholar_id")
        batch_op.drop_column("openalex_id")
        batch_op.drop_column("dblp_key")
        batch_op.drop_column("openreview_id")
        batch_op.drop_column("arxiv_id")
