"""initial migration

Revision ID: 7e3bc4973d6f
Revises: 
Create Date: 2025-09-03 16:43:12.842087

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '7e3bc4973d6f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(text("CREATE SCHEMA IF NOT EXISTS public"))
    op.execute(text("CREATE EXTENSION IF NOT EXISTS adminpack WITH SCHEMA pg_catalog"))
    op.execute(text("CREATE EXTENSION IF NOT EXISTS pg_stat_statements"))

    op.create_table('sizes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('volume_ml',sa.Integer(),nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    schema='public'
    )
    op.create_table('drink_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('firstname', sa.String(length=50), nullable=True),
    sa.Column('phone_number', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('tg_user_id', sa.BIGINT(), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('is_bot', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tg_user_id'),
    schema='public'
    )
    op.create_table(
        'drinks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.BIGINT(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('is_draft', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.ForeignKeyConstraint(['type_id'], ['public.drink_types.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by'], ['public.users.tg_user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )



def downgrade() -> None:
    """Downgrade schema."""
    op.execute(text("DROP SCHEMA IF EXISTS public"))
    op.execute(text("DROP EXTENSION IF EXISTS adminpack WITH SCHEMA pg_catalog"))
    op.execute(text("DROP EXTENSION IF EXISTS pg_stat_statements"))

    op.drop_table('sizes', schema='public')
    op.drop_tables('drink_types',schema='public')
    op.drop_tables('users',schema='public')
    op.drop_tables('drinks',schema='public')

