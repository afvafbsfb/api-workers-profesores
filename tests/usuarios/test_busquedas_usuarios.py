import os
os.environ['DB_ENV'] = 'developmentAWS'

import pytest
from app import create_app
from config import Config
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


def list_users(access_token, params=None):
    base_url = "http://127.0.0.1:5000"

    headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
    qs = ''
    if params:
        from urllib.parse import urlencode
        qs = '?' + urlencode(params)
    return requests.get(f"{base_url}/usuarios/{qs}", headers=headers)


def logout_with_refresh(refresh_token):
    base_url = "http://127.0.0.1:5000"

    return requests.post(f"{base_url}/auth/logout", headers={'Authorization': f'Bearer {refresh_token}'})


@pytest.mark.meta(title='Busquedas usuarios - admin_academia', desc='Login admin_academia y búsquedas restringidas a su academia')
def test_login_admin_academia_and_search_without_academia_should_succeed(client):
    """test_login_admin_academia_and_search_without_academia_should_succeed
    Login como admin_academia y listar usuarios sin pasar academia_id; la API debe forzar su academia y devolver 200.
    """
    access, refresh = login_and_get_tokens('admin_academia@academia.com', 'password_admin_academia')
    rv = list_users(access)
    assert rv.status_code == 200
    resp = rv.json()
    assert isinstance(resp, dict)
    users = resp.get('items', [])
    assert isinstance(users, list)
    assert len(users) > 0
    # Comprobar que todos los usuarios devueltos pertenecen a la academia del caller
    me = requests.get('http://127.0.0.1:5000/usuarios/me', headers={'Authorization': f'Bearer {access}'}).json()
    my_academia = me.get('academia_id')
    for u in users:
        assert u.get('academia_id') == my_academia


@pytest.mark.meta(title='Busquedas usuarios - admin_academia con id', desc='Admin academia puede filtrar por su academia explicitamente')
def test_admin_academia_search_with_academia_id_that_exists_should_succeed(client):
    """test_admin_academia_search_with_academia_id_that_exists_should_succeed
    admin_academia puede hacer consulta pasando su academia_id y obtener 200.
    """
    access, refresh = login_and_get_tokens('admin_academia@academia.com', 'password_admin_academia')
    me = requests.get('http://127.0.0.1:5000/usuarios/me', headers={'Authorization': f'Bearer {access}'}).json()
    my_academia = me.get('academia_id')
    rv = list_users(access, params={'academia_id': my_academia})
    assert rv.status_code == 200
    resp = rv.json()
    users = resp.get('items', [])
    assert all(u.get('academia_id') == my_academia for u in users)


def test_logout_admin_academia(client):
    """test_logout_admin_academia
    Logout del admin_academia usando refresh token debe revocar el refresh.
    """
    access, refresh = login_and_get_tokens('admin_academia@academia.com', 'password_admin_academia')
    rv = logout_with_refresh(refresh)
    assert rv.status_code in (200, 204)


@pytest.mark.meta(title='Busquedas usuarios - admin_plataforma', desc='Admin plataforma puede listar globalmente')
def test_login_admin_plataforma_and_search_without_academia_should_succeed(client):
    """test_login_admin_plataforma_and_search_without_academia_should_succeed
    Login admin_plataforma y listar sin academia_id debe devolver 200 y resultados variados.
    """
    access, refresh = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    rv = list_users(access)
    assert rv.status_code == 200
    resp = rv.json()
    users = resp.get('items', [])
    assert isinstance(users, list) and len(users) > 0


def test_admin_plataforma_search_with_other_academia_should_succeed(client):
    """test_admin_plataforma_search_with_other_academia_should_succeed
    Admin plataforma puede filtrar por cualquier academia_id y obtener 200.
    """
    access, refresh = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    # Obtener una academia_id presente en los resultados
    rv_all = list_users(access)
    resp_all = rv_all.json()
    users = resp_all.get('items', [])
    other_acad = None
    for u in users:
        if u.get('academia_id'):
            other_acad = u.get('academia_id')
            break
    assert other_acad is not None, "No se encontró ninguna academia en los usuarios para probar"
    rv = list_users(access, params={'academia_id': other_acad})
    assert rv.status_code == 200
    resp2 = rv.json()
    users2 = resp2.get('items', [])
    assert all(u.get('academia_id') == other_acad for u in users2)


def test_admin_plataforma_search_with_own_academia_should_succeed(client):
    """test_admin_plataforma_search_with_own_academia_should_succeed
    Admin plataforma puede filtrar por academia_id (si lo desea) y obtener 200.
    """
    access, refresh = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    # Usamos la misma lógica: tomar una academia de la lista
    rv_all = list_users(access)
    resp_all = rv_all.json()
    users = resp_all.get('items', [])
    some_acad = None
    for u in users:
        if u.get('academia_id'):
            some_acad = u.get('academia_id')
            break
    assert some_acad is not None
    rv = list_users(access, params={'academia_id': some_acad})
    assert rv.status_code == 200


def test_logout_admin_plataforma(client):
    """test_logout_admin_plataforma
    Logout del admin_plataforma.
    """
    access, refresh = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    rv = logout_with_refresh(refresh)
    assert rv.status_code in (200, 204)


@pytest.mark.meta(title='Busquedas usuarios - profesor_academia', desc='Profesor de academia: búsquedas forzadas a su academia')
def test_login_profesor_academia_and_search_without_academia_should_succeed_but_forced_to_own_academia(client):
    """test_login_profesor_academia_and_search_without_academia_should_succeed_but_forced_to_own_academia
    Login como profesor_academia y listar sin academia_id: debe devolver solo usuarios de su academia.
    """
    # Use a reserve user that is active in the seeder to avoid blocked estado
    access, refresh = login_and_get_tokens('reserve_user_academia_1_1@academia.com', 'password_reserve_user_academia_1_1')
    rv = list_users(access)
    assert rv.status_code == 200
    resp = rv.json()
    users = resp.get('items', [])
    me = requests.get('http://127.0.0.1:5000/usuarios/me', headers={'Authorization': f'Bearer {access}'}).json()
    my_academia = me.get('academia_id')
    assert all(u.get('academia_id') == my_academia for u in users)


def test_profesor_academia_search_with_other_academia_should_fail(client):
    """test_profesor_academia_search_with_other_academia_should_fail
    Profesor intenta filtrar por otra academia -> debe 403.
    """
    access, refresh = login_and_get_tokens('reserve_user_academia_1_1@academia.com', 'password_reserve_user_academia_1_1')
    # Obtener una academia diferente mediante el usuario admin_plataforma
    ap_access, _ = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    rv_all = list_users(ap_access)
    resp_all = rv_all.json()
    users = resp_all.get('items', [])
    other_acad = None
    for u in users:
        me_acad = requests.get('http://127.0.0.1:5000/usuarios/me', headers={'Authorization': f'Bearer {access}'}).json().get('academia_id')
        if u.get('academia_id') and u.get('academia_id') != me_acad:
            other_acad = u.get('academia_id')
            break
    assert other_acad is not None, "No se encontró una academia distinta para probar"
    rv = list_users(access, params={'academia_id': other_acad})
    assert rv.status_code == 403


def test_profesor_academia_search_with_own_academia_should_succeed(client):
    """test_profesor_academia_search_with_own_academia_should_succeed
    Profesor filtra por su academia -> 200.
    """
    access, refresh = login_and_get_tokens('reserve_user_academia_1_1@academia.com', 'password_reserve_user_academia_1_1')
    me = requests.get('http://127.0.0.1:5000/usuarios/me', headers={'Authorization': f'Bearer {access}'}).json()
    my_academia = me.get('academia_id')
    rv = list_users(access, params={'academia_id': my_academia})
    assert rv.status_code == 200


def test_logout_profesor_academia(client):
    """test_logout_profesor_academia
    Logout del profesor de academia.
    """
    # Use reserve active user for logout to avoid blocked estado
    access, refresh = login_and_get_tokens('reserve_user_academia_1_1@academia.com', 'password_reserve_user_academia_1_1')
    rv = logout_with_refresh(refresh)
    assert rv.status_code in (200, 204)


def test_admin_plataforma_pagination(client):
    """Small pagination smoke test for admin_plataforma: page/size limits results and pages differ."""
    access, refresh = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    rv = list_users(access, params={'page': 1, 'size': 2})
    assert rv.status_code == 200
    resp1 = rv.json()
    users_p1 = resp1.get('items', [])
    assert isinstance(users_p1, list)
    assert len(users_p1) <= 2

    rv2 = list_users(access, params={'page': 2, 'size': 2})
    assert rv2.status_code == 200
    resp2 = rv2.json()
    users_p2 = resp2.get('items', [])
    assert isinstance(users_p2, list)
    # either different content or second page empty
    assert users_p1 != users_p2 or len(users_p2) == 0


def test_admin_plataforma_filter_plus_pagination(client):
    """Combine nombre filter with pagination and ensure results respect both."""
    access, refresh = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    rv_all = list_users(access)
    assert rv_all.status_code == 200
    all_users = rv_all.json().get('items', [])
    if not all_users:
        pytest.skip('No users present to exercise filter+paging')

    sample_name = all_users[0].get('nombre')
    if not sample_name:
        pytest.skip('Sample user has no nombre to filter on')

    rv = list_users(access, params={'nombre': sample_name, 'page': 1, 'size': 1})
    assert rv.status_code == 200
    page = rv.json()
    items = page.get('items', [])
    assert isinstance(items, list)
    assert len(items) <= 1
    for u in items:
        assert sample_name.lower() in (u.get('nombre') or '').lower()
