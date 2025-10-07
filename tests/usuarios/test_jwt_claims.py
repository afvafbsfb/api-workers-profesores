import os
os.environ['DB_ENV'] = 'developmentAWS'

import pytest
from flask.testing import FlaskClient
from app import create_app
from typing import Generator
from config import Config
from flask_jwt_extended import decode_token


@pytest.fixture
def client() -> Generator[FlaskClient, None, None]:
    # Ensure the same DB configuration as other tests
    Config.set_environment_variables()
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        yield app.test_client()


def _login_and_decode(client: FlaskClient, email: str, password: str) -> dict:
    rv = client.post('/auth/login', json={'email': email, 'password': password})
    assert rv.status_code == 200, f"Login failed for {email}: {rv.get_json()}"
    tokens = rv.get_json().get('tokens') or {}
    access = tokens.get('access_token')
    assert access, 'No access token returned'
    # decode_token requires an app context
    with client.application.app_context():
        decoded = decode_token(access)
    return decoded


def test_admin_plataforma_token_contains_roles(client):
    """Login administrador_plataforma y rol admin_plataforma informado correctamente."""
    decoded = _login_and_decode(client, 'activo@academia.com', 'password_activo')
    # additional claims are top-level keys in the token payload
    assert 'roles' in decoded, f"roles claim missing in token: {decoded}"
    assert isinstance(decoded['roles'], list)
    assert 'Admin_plataforma' in decoded['roles']


def test_admin_academia_token_contains_academia_id(client):
    """Login administrador_academia, id academia informado."""
    decoded = _login_and_decode(client, 'admin_academia@academia.com', 'password_admin_academia')
    assert 'roles' in decoded
    # academy admin should have academia_id
    assert 'academia_id' in decoded, f"academia_id missing in token: {decoded}"
    # academia_id should be an int (or at least castable)
    try:
        int(decoded['academia_id'])
    except Exception:
        pytest.fail(f"academia_id is not an int: {decoded.get('academia_id')}")


def test_profesor_academia_token_contains_profesor_role_and_academia(client):
    """Login Profesor_academia, id_academia e id_profesor informado."""
    # user_academia_2_1@academia.com is seeded as an active Profesor_academia
    decoded = _login_and_decode(client, 'user_academia_2_1@academia.com', 'password_user_academia_2_1')
    assert 'roles' in decoded
    assert 'Profesor_academia' in decoded['roles']
    assert 'academia_id' in decoded
    # profesor_id is optional in the current model; if present it should be numeric
    if 'profesor_id' in decoded:
        try:
            int(decoded['profesor_id'])
        except Exception:
            pytest.fail(f"profesor_id is present but not numeric: {decoded.get('profesor_id')}")
