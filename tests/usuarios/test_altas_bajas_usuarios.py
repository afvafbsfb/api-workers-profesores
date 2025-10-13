import os
os.environ['DB_ENV'] = 'developmentAWS'

import pytest
from app import create_app
from config import Config
import uuid
from src.shared.database import db
from src.usuarios.infrastructure.models import Rol
import requests


@pytest.fixture
def client():
    Config.set_environment_variables()
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        yield app.test_client()


def login_and_get_tokens(email, password):
    base_url = "http://127.0.0.1:5000"

    login_response = requests.post(f"{base_url}/auth/login", json={'email': email, 'password': password})
    assert login_response.status_code == 200
    data = login_response.json()
    tokens = data.get('tokens') or {}
    return tokens.get('access_token'), tokens.get('refresh_token')


def logout_with_refresh(refresh_token):
    base_url = "http://127.0.0.1:5000"

    return requests.post(f"{base_url}/auth/logout", headers={'Authorization': f'Bearer {refresh_token}'})


def create_user(access_token, payload):
    base_url = "http://127.0.0.1:5000"

    headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
    return requests.post(f"{base_url}/usuarios/", json=payload, headers=headers)


@pytest.mark.meta(title='Altas y bajas usuarios - flujo básico', desc='Login, crear usuario, intento prohibido, borrar y logout')
def test_altas_bajas_usuarios_admin_plataforma_and_admin_academia_behaviour(client):
    # Login como admin_plataforma
    ap_access, ap_refresh = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')

    # admin_plataforma crea un usuario nuevo (buscamos un rol no-admin dinámicamente)
    unique = str(uuid.uuid4())[:8]
    # buscar un rol que NO sea admin_plataforma
    with client.application.app_context():
        non_admin_role = db.session.query(Rol).filter(Rol.nombre.ilike('%admin_plataforma%') == False).first()
        assert non_admin_role is not None, 'No non-admin role found in DB seeds'
        non_admin_role_id = non_admin_role.id

    payload = {
        'nombre': f'Test User {unique}',
        'email': f'test_user_{unique}@example.com',
        'password': 'secret123',
        'rol_id': non_admin_role_id
    }
    rv = create_user(ap_access, payload)
    assert rv.status_code == 201, f"admin_plataforma should create user: {rv.json()}"
    created = rv.json().get('result') or {}
    created_id = created.get('id')
    assert created_id is not None

    # Login como admin_academia
    aa_access, aa_refresh = login_and_get_tokens('admin_academia@academia.com', 'password_admin_academia')

    # admin_academia intenta crear un usuario con rol admin_plataforma -> debe 403
    payload2 = {
        'nombre': f'Bad Role User {unique}',
        'email': f'badrole_{unique}@example.com',
        'password': 'secret123',
        # Intenta forzar rol admin_plataforma por nombre
        'rol': 'admin_plataforma'
    }
    rv2 = create_user(aa_access, payload2)
    assert rv2.status_code == 403

    # admin_academia crea un usuario sin rol admin_plataforma (debe tener academia_id forzada)
    # Para crear un usuario válido con admin_academia usamos también un rol no-admin
    payload3 = {
        'nombre': f'OK User {unique}',
        'email': f'okuser_{unique}@example.com',
        'password': 'secret123',
        'rol_id': non_admin_role_id
    }
    rv3 = create_user(aa_access, payload3)
    assert rv3.status_code in (200, 201), f"admin_academia should create user in own academy: {rv3.json()}"

    # admin_plataforma borra (soft-delete) el usuario creado inicialmente
    if created_id:
        base_url = "http://127.0.0.1:5000"
        rv_del = requests.delete(f"{base_url}/usuarios/{created_id}", headers={'Authorization': f'Bearer {ap_access}'})
        assert rv_del.status_code == 200

    # logout tokens
    rv_logout_ap = logout_with_refresh(ap_refresh)
    assert rv_logout_ap.status_code in (200, 204)

    rv_logout_aa = logout_with_refresh(aa_refresh)
    assert rv_logout_aa.status_code in (200, 204)


# ----------------------
# Unit tests for permissions (moved from tests/shared/test_permissions_unit.py)
from types import SimpleNamespace
from src.shared.application import permissions


def make_user(role_name=None, academia_id=None, uid=1):
    rol = SimpleNamespace(nombre=role_name) if role_name else None
    return SimpleNamespace(id=uid, rol=rol, academia_id=academia_id)


def test_can_query_users_scoping_unit():
    ap = make_user('Admin_plataforma')
    ok, f, _ = permissions.can_query_users(ap, {})
    assert ok
    aa = make_user('Admin_academia', academia_id=7)
    ok2, f2, _ = permissions.can_query_users(aa, {})
    assert ok2 and f2.get('academia_id') == 7


@pytest.mark.meta(title='Unit: can_query_users', desc='Permisos usuarios: scoping por academia')
def test_can_query_users_scoping_unit():
    ap = make_user('Admin_plataforma')
    ok, f, _ = permissions.can_query_users(ap, {})
    assert ok
    aa = make_user('Admin_academia', academia_id=7)
    ok2, f2, _ = permissions.can_query_users(aa, {})
    assert ok2 and f2.get('academia_id') == 7


def test_can_create_user_admin_academia_cannot_create_platform_admin_unit():
    aa = make_user('Admin_academia', academia_id=5)
    allowed, eff, reason = permissions.can_create_user(aa, {'rol': 'admin_plataforma'})
    assert not allowed and reason == 'forbidden_role_assignment'


@pytest.mark.meta(title='Unit: can_create_user forbidden role assignment', desc='Permisos usuarios: admin_academia no puede crear admin_plataforma')
def test_can_create_user_admin_academia_cannot_create_platform_admin_unit():
    aa = make_user('Admin_academia', academia_id=5)
    allowed, eff, reason = permissions.can_create_user(aa, {'rol': 'admin_plataforma'})
    assert not allowed and reason == 'forbidden_role_assignment'


def test_can_modify_user_permissions_unit():
    ap = make_user('Admin_plataforma')
    target = SimpleNamespace(id=2, academia_id=9)
    ok, s, _ = permissions.can_modify_user(ap, target, {'rol_id': 4})
    assert ok and s.get('rol_id') == 4
    aa = make_user('Admin_academia', academia_id=9)
    ok2, s2, _ = permissions.can_modify_user(aa, target, {'rol_id': 4, 'nombre': 'New'})
    assert ok2 and 'rol_id' not in s2 and s2.get('nombre') == 'New'
    prof = make_user('Profesor_academia', academia_id=9, uid=2)
    ok3, s3, _ = permissions.can_modify_user(prof, target, {'nombre': 'Me'})
    assert ok3


@pytest.mark.meta(title='Unit: can_modify_user', desc='Permisos usuarios: admin_plataforma, admin_academia, profesor_academia reglas')
def test_can_modify_user_permissions_unit():
    ap = make_user('Admin_plataforma')
    target = SimpleNamespace(id=2, academia_id=9)
    ok, s, _ = permissions.can_modify_user(ap, target, {'rol_id': 4})
    assert ok and s.get('rol_id') == 4
    aa = make_user('Admin_academia', academia_id=9)
    ok2, s2, _ = permissions.can_modify_user(aa, target, {'rol_id': 4, 'nombre': 'New'})
    assert ok2 and 'rol_id' not in s2 and s2.get('nombre') == 'New'
    prof = make_user('Profesor_academia', academia_id=9, uid=2)
    ok3, s3, _ = permissions.can_modify_user(prof, target, {'nombre': 'Me'})
    assert ok3


def test_can_delete_user_scoping_unit():
    ap = make_user('Admin_plataforma')
    target = SimpleNamespace(id=3, academia_id=8)
    assert permissions.can_delete_user(ap, target)[0]
    aa = make_user('Admin_academia', academia_id=8)
    assert permissions.can_delete_user(aa, target)[0]
    aa_other = make_user('Admin_academia', academia_id=99)
    assert not permissions.can_delete_user(aa_other, target)[0]


@pytest.mark.meta(title='Unit: can_delete_user', desc='Permisos usuarios: scoping para borrar usuarios')
def test_can_delete_user_scoping_unit():
    ap = make_user('Admin_plataforma')
    target = SimpleNamespace(id=3, academia_id=8)
    assert permissions.can_delete_user(ap, target)[0]
    aa = make_user('Admin_academia', academia_id=8)
    assert permissions.can_delete_user(aa, target)[0]
    aa_other = make_user('Admin_academia', academia_id=99)
    assert not permissions.can_delete_user(aa_other, target)[0]
