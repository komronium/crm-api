"""backfill form_data from raw_payload for existing leads

Revision ID: a3f8e2c5b104
Revises: 9b2d4a7f1c01
Create Date: 2026-05-01 18:30:00.000000

"""

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.services.facebook_lead_service import _extract_form_qa


# revision identifiers, used by Alembic.
revision: str = "a3f8e2c5b104"
down_revision: Union[str, None] = "9b2d4a7f1c01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    rows = bind.execute(
        sa.text(
            "SELECT id, raw_payload FROM lead "
            "WHERE form_data IS NULL AND raw_payload IS NOT NULL"
        )
    ).fetchall()

    for row in rows:
        lead_id, raw_payload = row[0], row[1]
        try:
            parsed = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
        except (ValueError, TypeError):
            continue

        field_data = (parsed or {}).get("field_data") or []
        qa = _extract_form_qa(field_data)
        if not qa:
            continue

        bind.execute(
            sa.text("UPDATE lead SET form_data = CAST(:qa AS JSONB) WHERE id = :id").bindparams(
                qa=json.dumps(qa, ensure_ascii=False),
                id=lead_id,
            )
        )


def downgrade() -> None:
    # Backfill is non-destructive; nothing to undo.
    pass
