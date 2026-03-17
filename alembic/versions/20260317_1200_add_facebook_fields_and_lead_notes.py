"""add facebook fields and lead notes

Revision ID: 3c1a7c2d9f1a
Revises: ee7c10962e55
Create Date: 2026-03-17 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "3c1a7c2d9f1a"
down_revision: Union[str, None] = "ee7c10962e55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    lead_cols = {c["name"] for c in insp.get_columns("lead")}
    if "source" not in lead_cols:
        op.add_column(
            "lead",
            sa.Column(
                "source",
                sa.String(length=32),
                server_default="manual",
                nullable=False,
            ),
        )
    if "external_id" not in lead_cols:
        op.add_column(
            "lead",
            sa.Column("external_id", sa.String(length=128), nullable=True),
        )
    if "raw_payload" not in lead_cols:
        op.add_column("lead", sa.Column("raw_payload", sa.Text(), nullable=True))

    lead_indexes = {ix["name"] for ix in insp.get_indexes("lead")}
    if op.f("ix_lead_external_id") not in lead_indexes:
        op.create_index(
            op.f("ix_lead_external_id"), "lead", ["external_id"], unique=True
        )

    tables = set(insp.get_table_names())
    if "lead_note" not in tables:
        op.create_table(
            "lead_note",
            sa.Column("text", sa.String(length=512), nullable=False),
            sa.Column("lead_id", sa.Integer(), nullable=False),
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(["lead_id"], ["lead.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    lead_note_indexes = {ix["name"] for ix in insp.get_indexes("lead_note")}
    if op.f("ix_lead_note_id") not in lead_note_indexes:
        op.create_index(op.f("ix_lead_note_id"), "lead_note", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_lead_note_id"), table_name="lead_note")
    op.drop_table("lead_note")

    op.drop_index(op.f("ix_lead_external_id"), table_name="lead")
    op.drop_column("lead", "raw_payload")
    op.drop_column("lead", "external_id")
    op.drop_column("lead", "source")

