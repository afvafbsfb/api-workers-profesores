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


def login_and_get_tokens(email, password):
    login_response = requests.post(f"{BASE_URL}/auth/login", json={'email': email, 'password': password})
    assert login_response.status_code == 200, f"Login failed for {email}: {login_response.json()}"
    data = login_response.json()
    tokens = data.get('tokens') or {}
    return tokens.get('access_token'), tokens.get('refresh_token')


def list_academias(access_token, params=None):
    headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
    qs = ''
    if params:
        from urllib.parse import urlencode
        qs = '?' + urlencode(params)
    path = f"{BASE_URL}/academias{qs}"
    return requests.get(path, headers=headers)


def logout_with_refresh(refresh_token):
    return requests.post(f"{BASE_URL}/auth/logout", headers={'Authorization': f'Bearer {refresh_token}'})


@pytest.mark.meta(title='Admin_academia: listar propia', desc='Login y listar sin id debe devolver solo su academia')
def test_login_admin_academia_and_list_academias_without_id_should_return_own_academia(client):
    """Admin_academia lista academias sin id: debe devolver solo su academia"""
    access, refresh = login_and_get_tokens('admin_academia@academia.com', 'password_admin_academia')
    rv = list_academias(access)
    assert rv.status_code == 200
    payload = rv.json()
    data = payload.get('result', [])
    assert isinstance(data, list) and len(data) > 0
    me = requests.get(f"{BASE_URL}/usuarios/me", headers={'Authorization': f'Bearer {access}'}).json()
    my_acad = me.get('academia_id')
    assert all(a.get('id') == my_acad for a in data)


@pytest.mark.meta(title='Admin_academia: listar por id propia', desc='Pedir id igual a la academia del usuario debe funcionar')
def test_admin_academia_list_with_own_id_should_succeed(client):
    access, refresh = login_and_get_tokens('admin_academia@academia.com', 'password_admin_academia')
    me = requests.get(f"{BASE_URL}/usuarios/me", headers={'Authorization': f'Bearer {access}'}).json()
    my_acad = me.get('academia_id')
    rv = list_academias(access, params={'id': my_acad})
    assert rv.status_code == 200
    payload = rv.json()
    data = payload.get('result', [])
    assert len(data) >= 1
    assert data[0].get('id') == my_acad


@pytest.mark.meta(title='Admin_plataforma: listar todas', desc='Login como plataforma debe listar todas las academias')
def test_login_admin_plataforma_and_list_all_academias_should_succeed(client):
    access, refresh = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    rv = list_academias(access)
    assert rv.status_code == 200
    payload = rv.json()
    data = payload.get('result', [])
    assert isinstance(data, list) and len(data) >= 2  # seeder crea al menos 2 academias


@pytest.mark.meta(title='Admin_plataforma: listar por id', desc='Pedir una id concreta debe devolver esa academia')
def test_admin_plataforma_list_with_specific_id_should_succeed(client):
    access, refresh = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    rv_all = list_academias(access)
    payload_all = rv_all.json()
    data = payload_all.get('result', [])
    assert len(data) >= 1
    some_id = data[0].get('id')
    rv = list_academias(access, params={'id': some_id})
    assert rv.status_code == 200
    payload = rv.json()
    data2 = payload.get('result', [])
    assert data2[0].get('id') == some_id


@pytest.mark.meta(title='Profesor_academia: listar propia', desc='Profesor debe ver solo su academia al listar sin id')
def test_profesor_academia_list_forced_to_own_academia(client):
    access, refresh = login_and_get_tokens('reserve_user_academia_1_1@academia.com', 'password_reserve_user_academia_1_1')
    rv = list_academias(access)
    assert rv.status_code == 200
    payload = rv.json()
    data = payload.get('result', [])
    me = requests.get(f"{BASE_URL}/usuarios/me", headers={'Authorization': f'Bearer {access}'}).json()
    my_acad = me.get('academia_id')
    assert all(a.get('id') == my_acad for a in data)


@pytest.mark.meta(title='Profesor_academia: listar otra academia prohibido', desc='Pedir id de otra academia debe devolver 403')
def test_profesor_academia_list_other_academia_should_fail(client):
    access, refresh = login_and_get_tokens('reserve_user_academia_1_1@academia.com', 'password_reserve_user_academia_1_1')
    # Obtener una academia distinta usando admin_plataforma
    ap_access, _ = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    all_acads = list_academias(ap_access).json().get('result', [])
    other = None
    my_acad = requests.get(f"{BASE_URL}/usuarios/me", headers={'Authorization': f'Bearer {access}'}).json().get('academia_id')
    for a in all_acads:
        if a.get('id') != my_acad:
            other = a.get('id')
            break
    assert other is not None
    rv = list_academias(access, params={'id': other})
    assert rv.status_code == 403


def test_admin_plataforma_academias_pagination(client):
    """Pagination smoke test for academias: page/size restrict and pages differ."""
    access, refresh = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    rv = list_academias(access, params={'page': 1, 'size': 1})
    assert rv.status_code == 200
    p1 = rv.json().get('result', [])
    assert isinstance(p1, list)
    assert len(p1) <= 1

    rv2 = list_academias(access, params={'page': 2, 'size': 1})
    assert rv2.status_code == 200
    p2 = rv2.json().get('result', [])
    assert isinstance(p2, list)
    assert p1 != p2 or len(p2) == 0


def test_admin_plataforma_academias_filter_plus_pagination(client):
    """Filter by nombre combined with pagination (size=1) should respect both."""
    access, refresh = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    rv_all = list_academias(access)
    assert rv_all.status_code == 200
    all_acads = rv_all.json().get('result', [])
    if not all_acads:
        pytest.skip('No academias present to exercise filter+paging')

    sample_name = all_acads[0].get('nombre')
    if not sample_name:
        pytest.skip('Sample academia has no nombre to filter on')

    rv = list_academias(access, params={'nombre_contains': sample_name, 'page': 1, 'size': 1})
    assert rv.status_code == 200
    page = rv.json().get('result', [])
    assert isinstance(page, list)
    assert len(page) <= 1
    for a in page:
        assert sample_name.lower() in (a.get('nombre') or '').lower()
