import os
os.environ['DB_ENV'] = 'developmentAWS'

from app import create_app
from config import Config
from src.shared.database import db
from src.academias.infrastructure.models import Academia
from src.usuarios.infrastructure.models import Usuario, Rol
import pytest


@pytest.fixture
def client():
    Config.set_environment_variables()
    app = create_app()
    app.config['TESTING'] = True
    # Ensure an application context is active while tests run so
    # SQLAlchemy model helpers (e.g. Academia.query) work correctly.
    with app.app_context():
        yield app.test_client()


def login(client, email, password, expected_role=None):
    rv = client.post('/auth/login', json={'email': email, 'password': password})
    assert rv.status_code == 200, rv.get_json()
    data = rv.get_json()
    if expected_role:
        assert data['role'] == expected_role
    access = data['tokens']['access_token']
    refresh = data['tokens']['refresh_token']

    class TokenPair:
        def __init__(self, access, refresh):
            self.access = access
            self.refresh = refresh
        def __iter__(self):
            yield self.access
            yield self.refresh
        def __str__(self):
            return self.access
        def __repr__(self):
            return f"TokenPair(access={self.access!r}, refresh={self.refresh!r})"

    return TokenPair(access, refresh)


def logout(client, token_or_pair):
    # Accept either raw refresh token string or TokenPair
    refresh = None
    if hasattr(token_or_pair, 'refresh'):
        refresh = token_or_pair.refresh
    else:
        refresh = token_or_pair
    rv = client.post('/auth/logout', headers={'Authorization': f'Bearer {refresh}'} )
    assert rv.status_code == 200, rv.get_json()


@pytest.mark.meta(title='Listar academias (Plataforma)', desc='Listar todas las academias como Admin_plataforma')
def test_list_academias_admin_plataforma(client):
    token = login(client, 'admin_plataforma@academia.com', 'password_admin_plataforma', expected_role='Admin_plataforma')
    rv = client.get('/academias', headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['ok'] is True
    assert isinstance(data['result'], list)
    logout(client, token)


@pytest.mark.meta(title='Listar academias prohibido', desc='Comprobar que roles no plataforma no pueden listar academias')
def test_list_academias_forbidden_other_roles(client):
    token = login(client, 'admin_academia@academia.com', 'password_admin_academia', expected_role='Admin_academia')
    rv = client.get('/academias', headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 403
    logout(client, token)


@pytest.mark.meta(title='Obtener academia (Plataforma)', desc='Admin_plataforma puede obtener una academia por id')
def test_get_academia_admin_plataforma(client):
    token = login(client, 'admin_plataforma@academia.com', 'password_admin_plataforma', expected_role='Admin_plataforma')
    # assume seeder creó academias
    academias = Academia.query.limit(1).all()
    assert academias
    a = academias[0]
    rv = client.get(f'/academias/{a.id}', headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200
    logout(client, token)


@pytest.mark.meta(title='Obtener academia (Admin academia)', desc='Admin_academia puede obtener su academia vinculada')
def test_get_academia_admin_academia_linked(client):
    token = login(client, 'admin_academia@academia.com', 'password_admin_academia', expected_role='Admin_academia')
    user = Usuario.query.filter_by(email='admin_academia@academia.com').first()
    assert user and user.academia_id
    rv = client.get(f'/academias/{user.academia_id}', headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200
    logout(client, token)


@pytest.mark.meta(title='Obtener academia no vinculada', desc='Admin_academia no puede ver academias de otra academia')
def test_get_academia_admin_academia_not_linked_forbidden(client):
    token = login(client, 'admin_academia@academia.com', 'password_admin_academia', expected_role='Admin_academia')
    # find an academia not equal to user's academia
    user = Usuario.query.filter_by(email='admin_academia@academia.com').first()
    academia_not_mine = Academia.query.filter(Academia.id != user.academia_id).first()
    assert academia_not_mine
    rv = client.get(f'/academias/{academia_not_mine.id}', headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 403
    logout(client, token)


@pytest.mark.meta(title='Modificar academia (Plataforma)', desc='Admin_plataforma puede modificar cualquier academia')
def test_patch_academia_admin_plataforma(client):
    token = login(client, 'admin_plataforma@academia.com', 'password_admin_plataforma', expected_role='Admin_plataforma')
    a = Academia.query.first()
    rv = client.patch(f'/academias/{a.id}', json={'nombre': 'Academia Patched X'}, headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200
    d = rv.get_json()
    assert d['ok'] is True
    assert d['result']['nombre'] == 'Academia Patched X'
    logout(client, token)


@pytest.mark.meta(title='Modificar academia (Admin academia)', desc='Admin_academia puede modificar su academia vinculada')
def test_patch_academia_admin_academia_linked(client):
    token = login(client, 'admin_academia@academia.com', 'password_admin_academia', expected_role='Admin_academia')
    user = Usuario.query.filter_by(email='admin_academia@academia.com').first()
    a = db.session.get(Academia, user.academia_id)
    rv = client.patch(f'/academias/{a.id}', json={'nombre': 'Academia Patched Y'}, headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 200
    logout(client, token)


@pytest.mark.meta(title='Modificar academia no vinculada', desc='Admin_academia no puede modificar academias de otra academia')
def test_patch_academia_admin_academia_not_linked_forbidden(client):
    token = login(client, 'admin_academia@academia.com', 'password_admin_academia', expected_role='Admin_academia')
    user = Usuario.query.filter_by(email='admin_academia@academia.com').first()
    academia_not_mine = Academia.query.filter(Academia.id != user.academia_id).first()
    rv = client.patch(f'/academias/{academia_not_mine.id}', json={'nombre': 'Academia Patch Z'}, headers={'Authorization': f'Bearer {token}'})
    assert rv.status_code == 403
    logout(client, token)