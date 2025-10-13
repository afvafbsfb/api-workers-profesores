import os
os.environ['DB_ENV'] = 'developmentAWS'

import pytest
from app import create_app
from config import Config
import requests

BASE_URL = "http://127.0.0.1:5000"


@pytest.fixture
def client():
    Config.set_environment_variables()
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        yield app.test_client()


@pytest.fixture
def ensure_active_academia_for_admin_academia():
    """Ensure the seeded admin_academia user has an active Academia.

    If the user has no academia or it's soft-deleted, create a new one and
    assign the user to it directly in the DB. Runs inside app context.
    """
    from src.usuarios.infrastructure.models import Usuario
    from src.academias.infrastructure.models import Academia
    from src.shared.database import db

    # Find the admin_academia user
    user = Usuario.query.filter_by(email='admin_academia@academia.com').first()
    if not user:
        raise RuntimeError('admin_academia user not found in DB seed')

    acad = None
    if user.academia_id:
        acad = db.session.get(Academia, user.academia_id)
        # consider academy active only if fecha_baja is None
        if acad and getattr(acad, 'fecha_baja', None) is not None:
            acad = None

    if not acad:
        # create a new active academia and assign
        a = Academia(nombre=f"Academia_for_admin_academia_{user.id}")
        db.session.add(a)
        db.session.flush()  # ensure id
        user.academia_id = a.id
        db.session.add(user)
        db.session.commit()
        yield a.id
    else:
        yield acad.id


def login_and_get_tokens(email, password):
    login_response = requests.post(f"{BASE_URL}/auth/login", json={'email': email, 'password': password})
    assert login_response.status_code == 200, f"Login failed for {email}: {login_response.json()}"
    data = login_response.json()
    tokens = data.get('tokens') or {}
    return tokens.get('access_token'), tokens.get('refresh_token')


def logout_with_refresh(refresh_token):
    return requests.post(f"{BASE_URL}/auth/logout", headers={'Authorization': f'Bearer {refresh_token}'})


@pytest.mark.meta(title='Admin_plataforma: alta y baja de academias', desc='Crear y dar de baja una academia (solo platform admin)')
def test_admin_plataforma_can_create_and_delete_academia(client):
    access, refresh = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    # Crear con nombre único para evitar conflictos con datos seed
    import uuid
    unique_name = f"Academia Test AltaBaja {uuid.uuid4().hex[:8]}"
    rv = requests.post(f"{BASE_URL}/academias", json={'nombre': unique_name}, headers={'Authorization': f'Bearer {access}'})
    assert rv.status_code == 201
    data = rv.json()
    assert data.get('ok') is True
    created_id = data['result']['id']

    # Borrar
    rv2 = requests.delete(f"{BASE_URL}/academias/{created_id}", headers={'Authorization': f'Bearer {access}'})
    assert rv2.status_code == 200
    logout_with_refresh(refresh)


@pytest.mark.meta(title='Admin_academia: modificar academia propia', desc='Admin_academia puede modificar su academia, pero no crear ni dar de baja')
def test_admin_academia_can_modify_but_not_create_or_delete(client, ensure_active_academia_for_admin_academia):
    access, refresh = login_and_get_tokens('admin_academia@academia.com', 'password_admin_academia')
    # Ensure fixture provided an active academia id
    my_acad = ensure_active_academia_for_admin_academia
    # Intentar crear -> debe fallar por rol
    rv_create = requests.post(f"{BASE_URL}/academias", json={'nombre': 'Academia Forbidden Create'}, headers={'Authorization': f'Bearer {access}'})
    assert rv_create.status_code == 403
    # Modificar su academia -> ok
    import uuid as _uuid
    unique_patch_name = f"Academia Modificada Por AdminAcademia {_uuid.uuid4().hex[:8]}"
    rv_patch = requests.patch(f"{BASE_URL}/academias/{my_acad}", json={'nombre': unique_patch_name}, headers={'Authorization': f'Bearer {access}'})
    assert rv_patch.status_code == 200
    # Intentar borrar -> forbidden
    rv_delete = requests.delete(f"{BASE_URL}/academias/{my_acad}", headers={'Authorization': f'Bearer {access}'})
    assert rv_delete.status_code == 403
    logout_with_refresh(refresh)


# ----------------------
# Unit tests for permissions (moved from tests/shared/test_permissions_unit.py)
# These are lightweight, do not require the HTTP client or DB and test the
# permission logic directly.
from types import SimpleNamespace
from src.shared.application import permissions


def make_user(role_name=None, academia_id=None, uid=1):
    rol = SimpleNamespace(nombre=role_name) if role_name else None
    return SimpleNamespace(id=uid, rol=rol, academia_id=academia_id)


class DummyAcademia:
    def __init__(self, id):
        self.id = id


@pytest.mark.meta(title='Unit: can_query_academias admin_plataforma', desc='Permisos: admin_plataforma puede consultar academias globalmente')
def test_can_query_academias_admin_plataforma_unit():
    user = make_user('Admin_plataforma')
    ok, filters, reason = permissions.can_query_academias(user, {})
    assert ok and filters == {}


@pytest.mark.meta(title='Unit: can_query_academias admin_academia', desc='Permisos: admin_academia debe ser forzado a su academia')
def test_can_query_academias_admin_academia_forces_id_unit():
    user = make_user('Admin_academia', academia_id=42)
    ok, filters, reason = permissions.can_query_academias(user, {})
    assert ok and filters.get('id') == 42


@pytest.mark.meta(title='Unit: can_create_academia', desc='Permisos: solo admin_plataforma puede crear academias')
def test_can_create_academia_only_platform_admin_unit():
    ap = make_user('Admin_plataforma')
    allowed, payload, reason = permissions.can_create_academia(ap, {'nombre': 'X'})
    assert allowed
    aa = make_user('Admin_academia', academia_id=1)
    allowed2, _, _ = permissions.can_create_academia(aa, {'nombre': 'Y'})
    assert not allowed2


@pytest.mark.meta(title='Unit: can_modify_academia', desc='Permisos: admin_plataforma o admin_academia (propia) pueden modificar')
def test_can_modify_academia_scoping_unit():
    ap = make_user('Admin_plataforma')
    acad = DummyAcademia(10)
    ok, s, r = permissions.can_modify_academia(ap, acad, {'nombre': 'N'})
    assert ok
    aa = make_user('Admin_academia', academia_id=10)
    ok2, s2, r2 = permissions.can_modify_academia(aa, acad, {'nombre': 'N2'})
    assert ok2 and s2.get('nombre') == 'N2'
    aa_other = make_user('Admin_academia', academia_id=99)
    ok3, s3, r3 = permissions.can_modify_academia(aa_other, acad, {'nombre': 'X'})
    assert not ok3


@pytest.mark.meta(title='Unit: can_delete_academia', desc='Permisos: solo admin_plataforma puede dar de baja academias')
def test_can_delete_academia_only_platform_admin_unit():
    ap = make_user('Admin_plataforma')
    acad = DummyAcademia(1)
    assert permissions.can_delete_academia(ap, acad)[0]
    aa = make_user('Admin_academia', academia_id=1)
    assert not permissions.can_delete_academia(aa, acad)[0]


@pytest.mark.meta(title='Profesor_academia: solo consultar academias', desc='Profesor no puede crear, modificar ni dar de baja academias')
def test_profesor_academia_cannot_create_modify_or_delete(client):
    access, refresh = login_and_get_tokens('reserve_user_academia_1_1@academia.com', 'password_reserve_user_academia_1_1')
    # Listar academias (debe devolver su academia)
    rv = requests.get(f"{BASE_URL}/academias", headers={'Authorization': f'Bearer {access}'})
    assert rv.status_code == 200
    # Intentar crear
    rv_c = requests.post(f"{BASE_URL}/academias", json={'nombre': 'Academia Profesor Create'}, headers={'Authorization': f'Bearer {access}'})
    assert rv_c.status_code == 403
    # Intentar modificar
    me = requests.get(f"{BASE_URL}/usuarios/me", headers={'Authorization': f'Bearer {access}'}).json()
    my_acad = me.get('academia_id')
    rv_m = requests.patch(f"{BASE_URL}/academias/{my_acad}", json={'nombre': 'Academia Profesor Patch'}, headers={'Authorization': f'Bearer {access}'})
    assert rv_m.status_code == 403
    # Intentar borrar
    rv_d = requests.delete(f"{BASE_URL}/academias/{my_acad}", headers={'Authorization': f'Bearer {access}'})
    assert rv_d.status_code == 403
    logout_with_refresh(refresh)
