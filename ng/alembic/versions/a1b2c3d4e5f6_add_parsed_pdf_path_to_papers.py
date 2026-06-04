"""add parsed_pdf_path to papers table

Revision ID: a1b2c3d4e5f6
Revises: 03b4cd44700f
Create Date: 2026-06-04 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "03b4cd44700f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "papers", sa.Column("parsed_pdf_path", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("papers", "parsed_pdf_path")
