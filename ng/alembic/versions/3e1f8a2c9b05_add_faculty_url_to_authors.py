"""add faculty_url to authors

Revision ID: 3e1f8a2c9b05
Revises: 6c2b9a7f1d10
Create Date: 2026-05-28 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "3e1f8a2c9b05"
down_revision: Union[str, Sequence[str], None] = "6c2b9a7f1d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("authors") as batch_op:
        batch_op.add_column(sa.Column("faculty_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("authors") as batch_op:
        batch_op.drop_column("faculty_url")
