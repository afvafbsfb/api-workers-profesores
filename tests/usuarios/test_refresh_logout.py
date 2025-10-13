# Documentación y pasos recomendados para ejecutar estos tests
# - Objetivo: los tests en este fichero NO deben crear/editar/borrar datos de la
#   base de datos. Los datos de prueba (usuarios, rol, etc.) deben prepararse
#   previamente con `init_db_pruebas_test.py` (idempotente). Los tests sólo llaman al
#   endpoint `/auth/login`, `/auth/refresh` y `/auth/logout` y comprueban las respuestas.
#
# Requisitos y premisas
# - Ejecutar contra el entorno de desarrollo (`DB_ENV='development'`).
# - El script `init_db_pruebas_test.py` garantiza la existencia de los usuarios de prueba
#   y del rol necesario; ejecuta `init_db_pruebas_test.py` antes de lanzar los tests.
# - Credenciales usadas por los tests (provistas por `init_db_pruebas_test.py`):
#     admin_plataforma@academia.com    / password_admin_plataforma    (estado: Activo)

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
    # Ensure application context for DB access
    with app.app_context():
        yield app.test_client()


@pytest.mark.meta(title='Rotación refresh', desc='Rotar refresh token y revocar el antiguo')
def test_refresh_rotation_and_revocation():
    """Prueba: Rotación y revocación de refresh tokens."""
    base_url = "http://127.0.0.1:5000"

    print("Prueba: Ejecutando test_refresh_rotation_and_revocation")

    # Login para obtener tokens
    login_response = requests.post(f"{base_url}/auth/login", json={
        'email': 'admin_plataforma@academia.com',
        'password': 'password_admin_plataforma'
    })
    assert login_response.status_code == 200
    tokens = login_response.json().get('tokens') or {}
    refresh_token = tokens.get('refresh_token')

    # Rotar refresh token
    headers = {'Authorization': f'Bearer {refresh_token}'}
