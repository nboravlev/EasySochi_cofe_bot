"""drink_size table

Revision ID: 41b5167893f6
Revises: 7e3bc4973d6f
Create Date: 2025-09-04 08:41:07.671269

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '41b5167893f6'
down_revision: Union[str, Sequence[str], None] = '7e3bc4973d6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создание таблицы drink_sizes
    op.create_table(
        'drink_sizes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('drink_id', sa.Integer(), nullable=False),
        sa.Column('size_id', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.ForeignKeyConstraint(['drink_id'], ['public.drinks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['size_id'], ['public.sizes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )


def downgrade() -> None:
    # Удаление таблицы drink_sizes
    #op.drop_table('drink_sizes', schema='public')
    pass