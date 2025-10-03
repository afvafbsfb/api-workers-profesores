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


@pytest.fixture
def client():
    Config.set_environment_variables()
    app = create_app()
    app.config['TESTING'] = True
    # Ensure application context for DB access
    with app.app_context():
        yield app.test_client()


@pytest.mark.meta(title='Rotación refresh', desc='Rotar refresh token y revocar el antiguo')
def test_refresh_rotation_and_revocation(client):
    """
    Prueba: Rotación y revocación de refresh tokens.
    Entrada: Login válido para un usuario activo, uso del refresh token.
    Salida esperada: El refresh se rota (nuevo refresh), el antiguo queda revocado.
    """
    print("Prueba: Ejecutando test_refresh_rotation_and_revocation - Rotación y revocación de refresh tokens.")
    # Login para obtener tokens
    rv = client.post('/auth/login', json={'email': 'admin_plataforma@academia.com', 'password': 'password_admin_plataforma'})
    assert rv.status_code == 200
    data = rv.get_json()
    refresh = data['tokens']['refresh_token']

    # Usar refresh para rotar
    headers = {'Authorization': f'Bearer {refresh}'}
    rv2 = client.post('/auth/refresh', headers=headers)
    assert rv2.status_code == 200
    d2 = rv2.get_json()
    assert d2['ok'] is True
    new_refresh = d2['refresh_token']

    # Intentar usar el refresh antiguo debe fallar (está revocado)
    rv3 = client.post('/auth/refresh', headers={'Authorization': f'Bearer {refresh}'})
    assert rv3.status_code in (401, 400)

    # El nuevo refresh debe funcionar
    rv4 = client.post('/auth/refresh', headers={'Authorization': f'Bearer {new_refresh}'})
    assert rv4.status_code == 200


@pytest.mark.meta(title='Logout revoca refresh', desc='Logout debe revocar el refresh token utilizado')
def test_logout_revokes_refresh(client):
    """
    Prueba: Logout revoca el refresh token usado.
    Entrada: Login válido para un usuario activo, uso del refresh token en /auth/logout.
    Salida esperada: El refresh token queda revocado y no puede usarse para renovar.
    """
    print("Prueba: Ejecutando test_logout_revokes_refresh - Logout revoca refresh token.")
    # Login para obtener tokens
    rv = client.post('/auth/login', json={'email': 'admin_academia@academia.com', 'password': 'password_admin_academia'})
    assert rv.status_code == 200
    data = rv.get_json()
    refresh = data['tokens']['refresh_token']

    # Logout usando el refresh
    rv2 = client.post('/auth/logout', headers={'Authorization': f'Bearer {refresh}'})
    # Logout devuelve 204 con body vacío
    assert rv2.status_code in (200, 204)

    # Intentar usar el refresh debería fallar
    rv3 = client.post('/auth/refresh', headers={'Authorization': f'Bearer {refresh}'})
    assert rv3.status_code in (401, 400)
