# Documentación y pasos recomendados para ejecutar estos tests
# - Objetivo: los tests en este fichero NO deben crear/editar/borrar datos de la
#   base de datos. Los datos de prueba (usuarios, rol, etc.) deben prepararse
#   previamente con `init_db.py` (idempotente). Los tests sólo llaman al
#   endpoint `/auth/login` y comprueban las respuestas.
#
# Requisitos y premisas
# - Ejecutar contra el entorno de desarrollo (`DB_ENV='development'`).
# - El script `init_db.py` garantiza la existencia de los usuarios de prueba
#   y del rol necesario; ejecuta `init_db.py` antes de lanzar los tests.
# - Credenciales usadas por los tests (provistas por `init_db.py`):
#     activo@academia.com    / password_activo    (estado: Activo)
#     bloqueado@academia.com / password_bloqueado (estado: Bloqueado)
#     baja@academia.com      / password_baja      (estado: Baja)
#
# Comandos PowerShell recomendados (ejecutar uno a uno):
# 1) Activar el virtualenv (opcional si ya está activo):
#    & .\.venv\Scripts\Activate.ps1
#
# 2) Fijar el entorno de BD a development:
#    $env:DB_ENV='development'
#
# 3) Asegurar que `Config` exporta la URL de conexión requerida (muestra la URL):
#    python -c "from config import Config; Config.set_environment_variables(); import os; print('DATABASE_URL=', os.environ.get('DATABASE_URL'))"
#
# 4) Inicializar/asegurar los datos de prueba (idempotente):
#    python init_db.py
#    # (opcional y destructivo) python init_db.py --reset
#
# 5) Ejecutar únicamente este fichero de tests y ver los prints en consola:
#    python -m pytest tests/usuarios/test_login.py -q -s
#
# Notas:
# - La fixture del test ya llama a `Config.set_environment_variables()` antes de
#   crear la app para garantizar que la app y los tests usan la misma conexión.
# - `app.config['TESTING'] = True` se activa en la fixture para propagar
#   excepciones y facilitar el debug durante las pruebas.
# - Si prefieres aislar pruebas de efectos en la BD, considera ejecutar los
#   tests contra una BD temporal o usar fixtures transaccionales (no implementado
#   aquí porque la política actual es usar `init_db.py` para preparar datos).
#

import os
import pytest
from flask.testing import FlaskClient
from app import create_app
from typing import Generator
from config import Config  # Importar la configuración

@pytest.fixture
def client() -> Generator[FlaskClient, None, None]:
    # Asegurar la configuración de BD antes de crear la app para que
    # tanto init_db.py como los tests usen la misma conexión.
    Config.set_environment_variables()
    app = create_app()
    app.config['TESTING'] = True

    # No tocar la base de datos en la fixture: init_db.py debe preparar los datos.
    yield app.test_client()

def test_login_usuario_activo(client):
    """
    Prueba 1: Inicio de sesión con un usuario activo.
    Entrada: Correo electrónico y contraseña válidos para un usuario activo.
    Salida esperada: Código de estado 200 OK con tokens en la respuesta.
    Detalles: Se devuelven los tokens de acceso y de actualización.
    """
    print("Prueba 1: Ejecutando test_login_usuario_activo - Inicio de sesión con un usuario activo.")
    # Asumir que init_db.py ya ha creado el usuario 'activo@academia.com'
    response = client.post('/auth/login', json={
        'email': 'activo@academia.com',
        'password': 'password_activo'
    })
    print("Respuesta obtenida:", response.get_json())
    assert response.status_code == 200
    data = response.get_json()
    assert 'tokens' in data
    assert 'access_token' in data['tokens']
    assert 'refresh_token' in data['tokens']

def test_login_usuario_no_existente(client):
    """
    Prueba 2: Inicio de sesión con un usuario inexistente.
    Entrada: Correo electrónico y contraseña para un usuario que no existe.
    Salida esperada: Código de estado 401 No autorizado.
    """
    print("Prueba 2: Ejecutando test_login_usuario_no_existente - Inicio de sesión con un usuario inexistente.")
    response = client.post('/auth/login', json={
        'email': 'noexiste@academia.com',
        'password': 'password_incorrecta'
    })
    print("Respuesta obtenida:", response.get_json())
    assert response.status_code == 401

def test_login_usuario_bloqueado(client):
    """
    Prueba 3: Inicio de sesión con un usuario bloqueado.
    Entrada: Correo electrónico y contraseña válidos para un usuario bloqueado.
    Salida esperada: Código de estado 403 Prohibido.
    """
    print("Prueba 3: Ejecutando test_login_usuario_bloqueado - Inicio de sesión con un usuario bloqueado.")
    # Asumir que init_db.py ya ha creado el usuario 'bloqueado@academia.com'
    response = client.post('/auth/login', json={
        'email': 'bloqueado@academia.com',
        'password': 'password_bloqueado'
    })
    print("Respuesta obtenida:", response.get_json())
    assert response.status_code == 403

def test_routes(client):
    """
    Prueba 4: Verificar que la ruta '/auth/login' está disponible en la aplicación.
    Entrada: Ninguna.
    Salida esperada: La ruta '/auth/login' está disponible.
    """
    print("Prueba 4: Ejecutando test_routes - Verificar que la ruta '/auth/login' está disponible en la aplicación.")
    with client.application.app_context():
        routes = [rule.rule for rule in client.application.url_map.iter_rules()]
    print("Rutas disponibles:", routes)
    assert '/auth/login' in routes

def test_list_routes(client):
    """
    Prueba 5: Listar todas las rutas disponibles en la aplicación.
    Entrada: Ninguna.
    Salida esperada: Lista de todas las rutas disponibles en la aplicación.
    """
    print("Prueba 5: Ejecutando test_list_routes - Listar todas las rutas disponibles en la aplicación.")
    with client.application.app_context():
        routes = [rule.rule for rule in client.application.url_map.iter_rules()]
    print("Rutas disponibles:", routes)
    assert '/auth/login' in routes


#Los blueprints son una funcionalidad de Flask que permite organizar 
# y estructurar una aplicación en componentes o módulos reutilizables. 
# En lugar de definir todas las rutas y vistas en un único archivo, 
# puedes dividirlas en diferentes blueprints, 
# lo que facilita el mantenimiento y la escalabilidad de la aplicación.

def test_blueprint_registration(client):
    """
    Prueba 6: Verificar el registro de blueprints. El test 6 verifica que el blueprint 'login_bp' ha sido registrado correctamente en la aplicación. Esto asegura que las rutas y funcionalidades asociadas a ese blueprint están disponibles. Si el blueprint no está registrado, las rutas definidas en él no funcionarán.
    Entrada: Ninguna.
    Salida esperada: El blueprint 'login_bp' está registrado.
    """
    print("Prueba 6: Ejecutando test_blueprint_registration - Verificar el registro de blueprints.")
    with client.application.app_context():
        blueprints = client.application.blueprints.keys()
    print("Blueprints registrados:", blueprints)
    assert 'login_bp' in blueprints