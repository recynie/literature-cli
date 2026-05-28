"""add affiliations and author fields

Revision ID: 6c2b9a7f1d10
Revises: 03b4cd44700f
Create Date: 2026-05-28 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "6c2b9a7f1d10"
down_revision: Union[str, Sequence[str], None] = "10f8534b9062"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "affiliations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("institution", sa.String(length=255), nullable=False),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution", "department"),
    )

    with op.batch_alter_table("authors") as batch_op:
        batch_op.add_column(sa.Column("affiliation_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("personal_url", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("scholar_url", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("orcid", sa.String(length=50), nullable=True))
        batch_op.create_foreign_key(
            "fk_authors_affiliation_id_affiliations",
            "affiliations",
            ["affiliation_id"],
            ["id"],
        )

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT DISTINCT affiliation FROM authors WHERE affiliation IS NOT NULL AND TRIM(affiliation) != ''"))
    for (institution,) in rows:
        result = conn.execute(
            sa.text(
                "INSERT INTO affiliations (institution, department, url) VALUES (:institution, NULL, NULL)"
            ),
            {"institution": institution.strip()},
        )
        affiliation_id = result.lastrowid
        conn.execute(
            sa.text(
                "UPDATE authors SET affiliation_id = :affiliation_id WHERE affiliation = :institution"
            ),
            {"affiliation_id": affiliation_id, "institution": institution},
        )

    with op.batch_alter_table("authors") as batch_op:
        batch_op.drop_column("affiliation")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("authors") as batch_op:
        batch_op.add_column(sa.Column("affiliation", sa.String(length=255), nullable=True))

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE authors
            SET affiliation = (
                SELECT affiliations.institution
                FROM affiliations
                WHERE affiliations.id = authors.affiliation_id
            )
            WHERE affiliation_id IS NOT NULL
            """
        )
    )

    with op.batch_alter_table("authors") as batch_op:
        batch_op.drop_constraint("fk_authors_affiliation_id_affiliations", type_="foreignkey")
        batch_op.drop_column("orcid")
        batch_op.drop_column("scholar_url")
        batch_op.drop_column("personal_url")
        batch_op.drop_column("affiliation_id")
    op.drop_table("affiliations")
