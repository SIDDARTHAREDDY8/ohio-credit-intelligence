"""add notice_status to public.decisions

Records how each adverse-action notice was produced: 'generated' (Claude),
'fallback' (deterministic template used when Claude was unavailable or
non-compliant), or 'not_applicable' (approved/review decisions). Demonstrates a
forward schema evolution managed by Alembic rather than ad hoc DDL.

Revision ID: 0002_add_notice_status
Revises: 0001_initial_schema
Create Date: 2026-06-01
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002_add_notice_status"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.decisions
            ADD COLUMN IF NOT EXISTS notice_status TEXT
            DEFAULT 'not_applicable'
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public.decisions DROP COLUMN IF EXISTS notice_status")
