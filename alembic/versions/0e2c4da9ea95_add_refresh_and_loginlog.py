"""add refresh and loginlog

Revision ID: 0e2c4da9ea95
Revises: 0001_baseline
Create Date: 2025-10-01 11:03:27.009456

Trimmed migration: only adds RefreshToken and UserLoginLog tables and the
token_version/lock columns on Usuario. This avoids destructive operations
on existing databases; the original auto-generated migration was noisy
because of naming mismatches.

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.sqlite import INTEGER

# revision identifiers, used by Alembic.
revision = '0e2c4da9ea95'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Defensive / idempotent creation: check whether tables/indexes exist first
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    try:
        tables = inspector.get_table_names()
    except Exception:
        tables = []
    # Build a case-insensitive mapping from lower-name -> actual name returned by inspector
    tables_map = {t.lower(): t for t in tables}

    # RefreshToken
    # MySQL table name casing may differ depending on server settings; compare lowercased
    if 'refreshtoken' not in tables_map:
        # Modificar el tipo de columna para SQLite
        if op.get_bind().dialect.name == 'sqlite':
            id_column = sa.Column('id', INTEGER(), primary_key=True, autoincrement=True)
        else:
            id_column = sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True)

        op.create_table(
            'RefreshToken',
            id_column,
            sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('Usuario.id'), nullable=False),
            sa.Column('token_hash', sa.String(length=64), nullable=False),
            sa.Column('issued_at', sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('revoked_at', sa.DateTime(), nullable=True),
            sa.Column('replaced_by_id', sa.BigInteger(), nullable=True),
            sa.Column('ip', sa.LargeBinary(length=16), nullable=True),
            sa.Column('user_agent', sa.String(length=255), nullable=True),
            sa.Column('device_id', sa.String(length=100), nullable=True),
            sa.Column('scope', sa.String(length=200), nullable=True),
            sa.UniqueConstraint('token_hash', name='uk_refreshtoken_hash')
        )
        op.create_index('idx_refreshtoken_usuario_exp', 'RefreshToken', ['usuario_id', 'expires_at'])
        op.create_index('idx_refreshtoken_revoked', 'RefreshToken', ['revoked_at'])
    else:
        # ensure indexes exist (use actual table name as returned by inspector)
        actual_rt_table = tables_map.get('refreshtoken')
        try:
            idxs = {i['name'] for i in inspector.get_indexes(actual_rt_table)}
        except Exception:
            idxs = set()
        if 'idx_refreshtoken_usuario_exp' not in idxs:
            op.create_index('idx_refreshtoken_usuario_exp', actual_rt_table or 'RefreshToken', ['usuario_id', 'expires_at'])
        if 'idx_refreshtoken_revoked' not in idxs:
            op.create_index('idx_refreshtoken_revoked', actual_rt_table or 'RefreshToken', ['revoked_at'])

    # UserLoginLog
    if 'userloginlog' not in tables_map:
        op.create_table(
            'UserLoginLog',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('Usuario.id'), nullable=False),
            sa.Column('login_at', sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
            sa.Column('logout_at', sa.DateTime(), nullable=True),
            sa.Column('success', sa.Boolean(), nullable=False),
            sa.Column('fail_reason', sa.String(length=100), nullable=True),
            sa.Column('ip', sa.LargeBinary(length=16), nullable=True),
            sa.Column('user_agent', sa.String(length=255), nullable=True),
            sa.Column('device_id', sa.String(length=100), nullable=True),
            sa.Column('client', sa.String(length=50), nullable=True),
        )
        op.create_index('idx_ull_usuario_login', 'UserLoginLog', ['usuario_id', 'login_at'])
        op.create_index('idx_ull_success_login', 'UserLoginLog', ['success', 'login_at'])
    else:
        actual_ull_table = tables_map.get('userloginlog')
        try:
            idxs = {i['name'] for i in inspector.get_indexes(actual_ull_table)}
        except Exception:
            idxs = set()
        if 'idx_ull_usuario_login' not in idxs:
            op.create_index('idx_ull_usuario_login', actual_ull_table or 'UserLoginLog', ['usuario_id', 'login_at'])
        if 'idx_ull_success_login' not in idxs:
            op.create_index('idx_ull_success_login', actual_ull_table or 'UserLoginLog', ['success', 'login_at'])

    # Refresh inspector for Usuario column checks (some DBs may require re-inspection)
    # Re-inspect tables/columns now; use actual Usuario table name if present
    try:
        usuario_table_actual = tables_map.get('usuario', 'Usuario')
        cols = {c['name'] for c in inspector.get_columns(usuario_table_actual)}
    except Exception:
        cols = set()

    if 'token_version' not in cols:
        op.add_column('Usuario', sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'))
        try:
            op.create_index('idx_usuario_token_version', 'Usuario', ['token_version'])
        except Exception:
            pass
    if 'failed_login_count' not in cols:
        op.add_column('Usuario', sa.Column('failed_login_count', sa.Integer(), nullable=False, server_default='0'))
    if 'last_failed_login_at' not in cols:
        op.add_column('Usuario', sa.Column('last_failed_login_at', sa.DateTime(), nullable=True))
    if 'locked_until' not in cols:
        op.add_column('Usuario', sa.Column('locked_until', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove columns from Usuario (best-effort), then drop tables/indexes
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    try:
        cols = {c['name'] for c in inspector.get_columns('Usuario')}
    except Exception:
        cols = set()

    if 'locked_until' in cols:
        op.drop_column('Usuario', 'locked_until')
    if 'last_failed_login_at' in cols:
        op.drop_column('Usuario', 'last_failed_login_at')
    if 'failed_login_count' in cols:
        op.drop_column('Usuario', 'failed_login_count')
    if 'token_version' in cols:
        try:
            op.drop_index('idx_usuario_token_version', table_name='Usuario')
        except Exception:
            pass
        op.drop_column('Usuario', 'token_version')

    # Drop UserLoginLog
    try:
        op.drop_index('idx_ull_success_login', table_name='UserLoginLog')
    except Exception:
        pass
    try:
        op.drop_index('idx_ull_usuario_login', table_name='UserLoginLog')
    except Exception:
        pass
    try:
        op.drop_table('UserLoginLog')
    except Exception:
        pass

    # Drop RefreshToken
    try:
        op.drop_index('idx_refreshtoken_revoked', table_name='RefreshToken')
    except Exception:
        pass
    try:
        op.drop_index('idx_refreshtoken_usuario_exp', table_name='RefreshToken')
    except Exception:
        pass
    try:
        op.drop_table('RefreshToken')
    except Exception:
        pass
