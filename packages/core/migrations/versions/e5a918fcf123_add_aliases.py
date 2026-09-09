"""add_aliases_table

Revision ID: e5a918fcf123
Revises: de4a23fcfbcf
Create Date: 2026-09-08 13:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e5a918fcf123'
down_revision: Union[str, None] = 'de4a23fcfbcf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'aliases',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('target_type', sa.String(), nullable=False),
        sa.Column('target_id', sa.String(), nullable=True),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_aliases_name'), 'aliases', ['name'], unique=False)
    op.create_index(op.f('ix_aliases_user_id'), 'aliases', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_aliases_user_id'), table_name='aliases')
    op.drop_index(op.f('ix_aliases_name'), table_name='aliases')
    op.drop_table('aliases')

