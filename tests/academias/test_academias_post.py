#python -m pytest tests/academias -q -s

import os
os.environ['DB_ENV'] = 'developmentAWS'

import pytest
from app import create_app
from config import Config
from flask.testing import FlaskClient
from typing import Generator
from src.shared.database import db
from src.academias.infrastructure.models import Academia
import requests

BASE_URL = "http://127.0.0.1:5000"


@pytest.fixture
def client() -> Generator[FlaskClient, None, None]:
    Config.set_environment_variables()
    app = create_app()
    app.config['TESTING'] = True
    # Run tests inside the Flask application context so that
    # database model queries and other context-bound APIs work.
    with app.app_context():
        yield app.test_client()


def login_and_get_token(email, password, expected_role='Admin_plataforma'):
    """Realiza el login, valida el rol esperado y obtiene los tokens de acceso y refresco para un usuario válido."""
    login_response = requests.post(f"{BASE_URL}/auth/login", json={'email': email, 'password': password})
    assert login_response.status_code == 200, f"Error en login: {login_response.json()}"
    data = login_response.json()
    assert data['role'] == expected_role, f"Rol incorrecto: {data['role']}"
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

    return TokenPair(access, refresh)


def logout(client, refresh_token):
    """Realiza el logout para un usuario autenticado usando el refresh token."""
    rv = requests.post(f"{BASE_URL}/auth/logout", headers={'Authorization': f'Bearer {refresh_token}'})
    assert rv.status_code == 200, f"Error en logout: {rv.json()}"


# Actualizar las credenciales para usar un usuario válido
VALID_USER_EMAIL = 'admin_plataforma@academia.com'  # Correo actualizado para coincidir con init_db_pruebas_test.py
VALID_USER_PASSWORD = 'password_admin_plataforma'  # Contraseña actualizada para coincidir con init_db_pruebas_test.py


@pytest.mark.meta(title='Crear academia (happy path)', desc='Login como Admin_plataforma y crear una nueva academia')
def test_login_crear_academia_logout_happy_path(client):
    access_token, refresh_token = login_and_get_token(VALID_USER_EMAIL, VALID_USER_PASSWORD, expected_role='Admin_plataforma')
    rv = requests.post(f"{BASE_URL}/academias", json={'nombre': 'Academia Test X'}, headers={'Authorization': f'Bearer {access_token}'},)
    assert rv.status_code == 201, f"Error en creación: {rv.json()}"
    data = rv.json()
    assert data['ok'] is True
    assert 'result' in data and data['result']['nombre'] == 'Academia Test X'
    logout(client, refresh_token)


@pytest.mark.meta(title='Crear academia conflict', desc='Intentar crear academia duplicada y recibir 409')
def test_login_crear_academia_logout_conflict(client):
    access_token, refresh_token = login_and_get_token(VALID_USER_EMAIL, VALID_USER_PASSWORD, expected_role='Admin_plataforma')
    rv1 = requests.post(f"{BASE_URL}/academias", json={'nombre': 'Academia Conflict'}, headers={'Authorization': f'Bearer {access_token}'},)
    assert rv1.status_code in (200, 201), f"Error en primera creación: {rv1.json()}"
    rv2 = requests.post(f"{BASE_URL}/academias", json={'nombre': 'Academia Conflict'}, headers={'Authorization': f'Bearer {access_token}'},)
    assert rv2.status_code == 409, f"Error en conflicto: {rv2.json()}"
    logout(client, refresh_token)


@pytest.mark.meta(title='Crear academia sin nombre', desc='Validación: nombre requerido devuelve 400')
def test_login_crear_academia_logout_sin_nombre(client):
    access_token, refresh_token = login_and_get_token(VALID_USER_EMAIL, VALID_USER_PASSWORD, expected_role='Admin_plataforma')
    rv = requests.post(f"{BASE_URL}/academias", json={}, headers={'Authorization': f'Bearer {access_token}'},)
    assert rv.status_code == 400, f"Error en validación de nombre: {rv.json()}"
    logout(client, refresh_token)


@pytest.mark.meta(title='Crear academia prohibido por rol', desc='Admin_academia no puede crear academias')
def test_crear_academia_forbidden_por_rol(client):
    # Usar un admin de academia (no plataforma) o un usuario normal
    token = login_and_get_token('admin_academia@academia.com', 'password_admin_academia', expected_role='Admin_academia')
    rv = requests.post(f"{BASE_URL}/academias", json={'nombre': 'Academia Forbidden'}, headers={'Authorization': f'Bearer {token}'},)
    assert rv.status_code == 403


@pytest.mark.meta(title='Crear academia sin autenticar', desc='Petición sin token devuelve 401')
def test_crear_academia_unauthenticated(client):
    rv = requests.post(f"{BASE_URL}/academias", json={'nombre': 'Academia NoAuth'})
    assert rv.status_code == 401
