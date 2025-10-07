import os
os.environ['DB_ENV'] = 'developmentAWS'

import pytest
from app import create_app
from config import Config


@pytest.fixture
def client():
    Config.set_environment_variables()
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        yield app.test_client()


def login_and_get_tokens(client, email, password):
    rv = client.post('/auth/login', json={'email': email, 'password': password})
    assert rv.status_code == 200, f"Login failed for {email}: {rv.get_json()}"
    data = rv.get_json()
    tokens = data.get('tokens') or {}
    return tokens.get('access_token'), tokens.get('refresh_token')


def list_academias(client, access_token, params=None):
    headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
    qs = ''
    if params:
        from urllib.parse import urlencode
        qs = '?' + urlencode(params)
    # Build path without adding an extra slash when qs is empty to avoid 308/404
    path = f'/academias{qs}'
    rv = client.get(path, headers=headers)

    # Some endpoints in the codebase return {'ok': True, 'result': [...]}
    # while other parts (and previous tests) expect a bare list. Normalize
    # so tests work with either shape by returning a small response-like
    # object whose get_json() returns the list result.
    try:
        data = rv.get_json()
    except Exception:
        data = None

    if isinstance(data, dict) and 'result' in data:
        class SimpleResp:
            def __init__(self, status_code, payload):
                self.status_code = status_code
                self._payload = payload

            def get_json(self):
                return self._payload

        return SimpleResp(rv.status_code, data['result'])

    return rv


def logout_with_refresh(client, refresh_token):
    return client.post('/auth/logout', headers={'Authorization': f'Bearer {refresh_token}'})


@pytest.mark.meta(title='Admin_academia: listar propia', desc='Login y listar sin id debe devolver solo su academia')
def test_login_admin_academia_and_list_academias_without_id_should_return_own_academia(client):
    """Admin_academia lista academias sin id: debe devolver solo su academia"""
    access, refresh = login_and_get_tokens(client, 'admin_academia@academia.com', 'password_admin_academia')
    rv = list_academias(client, access)
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, list) and len(data) > 0
    me = client.get('/usuarios/me', headers={'Authorization': f'Bearer {access}'}).get_json()
    my_acad = me.get('academia_id')
    assert all(a.get('id') == my_acad for a in data)


@pytest.mark.meta(title='Admin_academia: listar por id propia', desc='Pedir id igual a la academia del usuario debe funcionar')
def test_admin_academia_list_with_own_id_should_succeed(client):
    access, refresh = login_and_get_tokens(client, 'admin_academia@academia.com', 'password_admin_academia')
    me = client.get('/usuarios/me', headers={'Authorization': f'Bearer {access}'}).get_json()
    my_acad = me.get('academia_id')
    rv = list_academias(client, access, params={'id': my_acad})
    assert rv.status_code == 200
    data = rv.get_json()
    assert len(data) >= 1
    assert data[0].get('id') == my_acad


@pytest.mark.meta(title='Admin_plataforma: listar todas', desc='Login como plataforma debe listar todas las academias')
def test_login_admin_plataforma_and_list_all_academias_should_succeed(client):
    access, refresh = login_and_get_tokens(client, 'admin_plataforma@academia.com', 'password_admin_plataforma')
    rv = list_academias(client, access)
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, list) and len(data) >= 2  # seeder crea al menos 2 academias


@pytest.mark.meta(title='Admin_plataforma: listar por id', desc='Pedir una id concreta debe devolver esa academia')
def test_admin_plataforma_list_with_specific_id_should_succeed(client):
    access, refresh = login_and_get_tokens(client, 'admin_plataforma@academia.com', 'password_admin_plataforma')
    rv_all = list_academias(client, access)
    data = rv_all.get_json()
    assert len(data) >= 1
    some_id = data[0].get('id')
    rv = list_academias(client, access, params={'id': some_id})
    assert rv.status_code == 200
    assert rv.get_json()[0].get('id') == some_id


@pytest.mark.meta(title='Profesor_academia: listar propia', desc='Profesor debe ver solo su academia al listar sin id')
def test_profesor_academia_list_forced_to_own_academia(client):
    access, refresh = login_and_get_tokens(client, 'reserve_user_academia_1_1@academia.com', 'password_reserve_user_academia_1_1')
    rv = list_academias(client, access)
    assert rv.status_code == 200
    data = rv.get_json()
    me = client.get('/usuarios/me', headers={'Authorization': f'Bearer {access}'}).get_json()
    my_acad = me.get('academia_id')
    assert all(a.get('id') == my_acad for a in data)


@pytest.mark.meta(title='Profesor_academia: listar otra academia prohibido', desc='Pedir id de otra academia debe devolver 403')
def test_profesor_academia_list_other_academia_should_fail(client):
    access, refresh = login_and_get_tokens(client, 'reserve_user_academia_1_1@academia.com', 'password_reserve_user_academia_1_1')
    # Obtener una academia distinta usando admin_plataforma
    ap_access, _ = login_and_get_tokens(client, 'admin_plataforma@academia.com', 'password_admin_plataforma')
    all_acads = list_academias(client, ap_access).get_json()
    other = None
    my_acad = client.get('/usuarios/me', headers={'Authorization': f'Bearer {access}'}).get_json().get('academia_id')
    for a in all_acads:
        if a.get('id') != my_acad:
            other = a.get('id')
            break
    assert other is not None
    rv = list_academias(client, access, params={'id': other})
    assert rv.status_code == 403
