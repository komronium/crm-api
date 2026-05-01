"""add form_data column and migrate lead statuses

Revision ID: 9b2d4a7f1c01
Revises: 3c1a7c2d9f1a
Create Date: 2026-05-01 17:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "9b2d4a7f1c01"
down_revision: Union[str, None] = "3c1a7c2d9f1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Map old statuses -> new statuses
STATUS_MAPPING = {
    "contacted": "callback",
    "negotiation": "thinking",
    "closed": "sale",
}


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    lead_cols = {c["name"] for c in insp.get_columns("lead")}
    if "form_data" not in lead_cols:
        op.add_column("lead", sa.Column("form_data", JSONB, nullable=True))

    for old, new in STATUS_MAPPING.items():
        op.execute(
            sa.text("UPDATE lead SET status = :new WHERE status = :old").bindparams(
                old=old, new=new
            )
        )


def downgrade() -> None:
    bind = op.get_bind()

    reverse = {v: k for k, v in STATUS_MAPPING.items()}
    for new, old in reverse.items():
        op.execute(
            sa.text("UPDATE lead SET status = :old WHERE status = :new").bindparams(
                old=old, new=new
            )
        )

    op.drop_column("lead", "form_data")
