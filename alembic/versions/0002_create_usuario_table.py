"""create usuario table

Revision ID: 0002_create_usuario_table
Revises: 0001_baseline
Create Date: 2025-10-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_create_usuario_table'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'Usuario',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password', sa.String(255), nullable=False),
        sa.Column('failed_login_count', sa.Integer, nullable=False, default=0),
        sa.Column('estado', sa.String(50), nullable=False, default='Activo')
    )

def downgrade() -> None:
    op.drop_table('Usuario')