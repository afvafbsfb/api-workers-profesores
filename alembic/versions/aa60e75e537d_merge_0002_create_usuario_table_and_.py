"""Merge 0002_create_usuario_table and 0e2c4da9ea95

Revision ID: aa60e75e537d
Revises: 0002_create_usuario_table, 0e2c4da9ea95
Create Date: 2025-10-02 10:00:31.837375

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa60e75e537d'
down_revision: Union[str, Sequence[str], None] = ('0002_create_usuario_table', '0e2c4da9ea95')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
