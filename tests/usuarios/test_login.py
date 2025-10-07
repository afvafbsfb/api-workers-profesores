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

#  python app.py    --> levanto el servidor (opcional, no es necesario para los tests)

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
#    python init_db_pruebas_test.py
#    # (opcional y destructivo) python init_db_pruebas_test.py --reset
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

# para lanzar todos los tests de usuarios:
#$env:DB_ENV='developmentAWS'; pytest tests/usuarios


import os
os.environ['DB_ENV'] = 'developmentAWS'  # Asegurar el entorno de desarrollo AWS

import pytest
from flask.testing import FlaskClient
from app import create_app
from typing import Generator
from config import Config  # Importar la configuración
from src.usuarios.infrastructure.models import Usuario, UserLoginLog
from src.shared.database import db
from src.shared.security import hash_password

@pytest.fixture
def client() -> Generator[FlaskClient, None, None]:
    # Asegurar la configuración de BD antes de crear la app para que
    # tanto init_db.py como los tests usen la misma conexión.
    Config.set_environment_variables()
    app = create_app()
    app.config['TESTING'] = True
    # No tocar la base de datos en la fixture: init_db.py debe preparar los datos.
    # Ejecutar dentro del application context para permitir consultas al modelo.
    with app.app_context():
        yield app.test_client()

@pytest.mark.meta(title='Login usuario activo', desc='Inicio de sesión con usuario activo devuelve 200 y tokens')
def test_login_usuario_activo(client):
    """
    Prueba 1: Inicio de sesión con un usuario activo.
    Entrada: Correo electrónico y contraseña válidos para un usuario activo.
    Salida esperada: Código de estado 200 OK con tokens en la respuesta.
    Detalles: Se devuelven los tokens de acceso y de actualización.
    """
    print("\nPrueba 1: Ejecutando test_login_usuario_activo - Inicio de sesión con un usuario activo.")
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
    assert 'role' in data
    assert 'name' in data
    assert data['role'] == 'Admin_plataforma'  # Ajustar según el rol esperado
    assert data['name'] == 'Usuario Activo'  # Ajustar según el nombre esperado


@pytest.mark.meta(title='Mi perfil tras login', desc='Después del login, GET /usuarios/me devuelve los datos del usuario')
def test_obtener_mi_perfil_despues_login(client):
    """
    Prueba: Tras un login correcto, solicitar /usuarios/me con el access token devuelve los datos del usuario.
    """
    print("\nPrueba: Ejecutando test_obtener_mi_perfil_despues_login - Login y consulta de /usuarios/me")
    # Realizar login primero
    rv = client.post('/auth/login', json={
        'email': 'activo@academia.com',
        'password': 'password_activo'
    })
    print("Respuesta login:", rv.get_json())
    assert rv.status_code == 200
    tokens = rv.get_json().get('tokens') or {}
    access = tokens.get('access_token')
    assert access, "No se recibió access_token en la respuesta de login"

    # Llamar al endpoint protegido /usuarios/me
    headers = { 'Authorization': f'Bearer {access}' }
    rv2 = client.get('/usuarios/me', headers=headers)
    print("Respuesta /usuarios/me:", rv2.get_json())
    assert rv2.status_code == 200
    perfil = rv2.get_json()
    # Comprobar campos esperados
    assert perfil.get('email') == 'activo@academia.com'
    assert perfil.get('nombre') == 'Usuario Activo'
    assert perfil.get('rol') == 'Admin_plataforma'
    assert 'id' in perfil
    assert 'fecha_alta' in perfil

@pytest.mark.meta(title='Login usuario inexistente', desc='Inicio de sesión con usuario inexistente devuelve 401')
def test_login_usuario_no_existente(client):
    """
    Prueba 2: Inicio de sesión con un usuario inexistente.
    Entrada: Correo electrónico y contraseña para un usuario que no existe.
    Salida esperada: Código de estado 401 No autorizado.
    """
    print("\nPrueba 2: Ejecutando test_login_usuario_no_existente - Inicio de sesión con un usuario inexistente.")
    response = client.post('/auth/login', json={
        'email': 'noexiste@academia.com',
        'password': 'password_incorrecta'
    })
    print("Respuesta obtenida:", response.get_json())
    assert response.status_code == 401

@pytest.mark.meta(title='Login usuario bloqueado', desc='Usuario bloqueado devuelve 403')
def test_login_usuario_bloqueado(client):
    """
    Prueba 3: Inicio de sesión con un usuario bloqueado.
    Entrada: Correo electrónico y contraseña válidos para un usuario bloqueado.
    Salida esperada: Código de estado 403 Prohibido.
    """
    print("\nPrueba 3: Ejecutando test_login_usuario_bloqueado - Inicio de sesión con un usuario bloqueado.")
    # Asumir que init_db.py ya ha creado el usuario 'bloqueado@academia.com'
    response = client.post('/auth/login', json={
        'email': 'bloqueado@academia.com',
        'password': 'password_bloqueado'
    })
    print("Respuesta obtenida:", response.get_json())
    assert response.status_code == 403

@pytest.mark.meta(title='Ruta login disponible', desc="Verificar que la ruta '/auth/login' está registrada")
def test_routes(client):
    """
    Prueba 4: Verificar que la ruta '/auth/login' está disponible en la aplicación.
    Entrada: Ninguna.
    Salida esperada: La ruta '/auth/login' está disponible.
    """
    print("\nPrueba 4: Ejecutando test_routes - Verificar que la ruta '/auth/login' está disponible en la aplicación.")
    with client.application.app_context():
        routes = [rule.rule for rule in client.application.url_map.iter_rules()]
    print("Rutas disponibles:", routes)
    assert '/auth/login' in routes

@pytest.mark.meta(title='Listar rutas', desc='Listar rutas disponibles en la aplicación')
def test_list_routes(client):
    """
    Prueba 5: Listar todas las rutas disponibles en la aplicación.
    Entrada: Ninguna.
    Salida esperada: Lista de todas las rutas disponibles en la aplicación.
    """
    print("\nPrueba 5: Ejecutando test_list_routes - Listar todas las rutas disponibles en la aplicación.")
    with client.application.app_context():
        routes = [rule.rule for rule in client.application.url_map.iter_rules()]
    print("Rutas disponibles:", routes)
    assert '/auth/login' in routes


#Los blueprints son una funcionalidad de Flask que permite organizar 
# y estructurar una aplicación en componentes o módulos reutilizables. 
# En lugar de definir todas las rutas y vistas en un único archivo, 
# puedes dividirlas en diferentes blueprints, 
# lo que facilita el mantenimiento y la escalabilidad de la aplicación.

@pytest.mark.meta(title='Registro blueprint', desc="Comprobar que el blueprint 'login_bp' está registrado")
def test_blueprint_registration(client):
    """
    Prueba 6: Verificar el registro de blueprints. El test 6 verifica que el blueprint 'login_bp' ha sido registrado correctamente en la aplicación. Esto asegura que las rutas y funcionalidades asociadas a ese blueprint están disponibles. Si el blueprint no está registrado, las rutas definidas en él no funcionarán.
    Entrada: Ninguna.
    Salida esperada: El blueprint 'login_bp' está registrado.
    """
    print("\nPrueba 6: Ejecutando test_blueprint_registration - Verificar el registro de blueprints.")
    with client.application.app_context():
        blueprints = client.application.blueprints.keys()
    print("Blueprints registrados:", blueprints)
    assert 'login_bp' in blueprints

@pytest.mark.meta(title='Login usuario baja', desc='Usuario dado de baja devuelve 403')
def test_login_usuario_baja(client):
    """
    Prueba 8: Inicio de sesión con un usuario dado de baja.
    Entrada: Correo electrónico y contraseña válidos para un usuario en estado "Baja".
    Salida esperada: Código de estado 403 Prohibido.
    """
    print("\nPrueba 8: Ejecutando test_login_usuario_baja - Inicio de sesión con un usuario dado de baja.")
    response = client.post('/auth/login', json={
        'email': 'baja@academia.com',
        'password': 'password_baja'
    })
    print("Respuesta obtenida:", response.get_json())
    assert response.status_code == 403

@pytest.mark.meta(title='Login administrador', desc='Inicio de sesión con usuario administrador devuelve 200 y tokens')
def test_login_usuario_administrador(client):
    """
    Prueba 9: Inicio de sesión con un usuario administrador.
    Entrada: Correo electrónico y contraseña válidos para un administrador.
    Salida esperada: Código de estado 200 OK con tokens en la respuesta.
    """
    print("\nPrueba 9: Ejecutando test_login_usuario_administrador - Inicio de sesión con un usuario administrador.")
    response = client.post('/auth/login', json={
        'email': 'admin_academia@academia.com',
        'password': 'password_admin_academia'
    })
    print("Respuesta obtenida:", response.get_json())
    assert response.status_code == 200
    data = response.get_json()
    assert 'tokens' in data
    assert 'access_token' in data['tokens']
    assert 'refresh_token' in data['tokens']

@pytest.mark.meta(title='Bloqueo por intentos fallidos', desc='Simular fallos hasta que el usuario quede bloqueado')
def test_login_blocking_after_failed_attempts(client):
    """
    Prueba 7: Bloqueo tras intentos fallidos.
    Entrada: usuario activo inicia sesión correctamente (resetea contador), luego intenta iniciar sesión con contraseña incorrecta repetidamente.
    Salida esperada: Los primeros 5 intentos (MAX_FAILED) devuelven 401; el intento siguiente devuelve 403 (usuario temporalmente bloqueado). Además comprobamos en la BD que el contador y los registros en UserLoginLog se actualizan.
    """
    print("\nPrueba 7: Ejecutando test_login_blocking_after_failed_attempts - Simular fallos hasta bloqueo.")
    # Asegurar la configuración de entorno para acceder a la BD
    Config.set_environment_variables()

    # Asegurar estado limpio: login correcto para resetear contadores
    # Use reserve account for destructive blocking test
    rv_ok = client.post('/auth/login', json={'email': 'reserve_activo@academia.com', 'password': 'password_reserve_activo'})
    assert rv_ok.status_code == 200

    # Obtener el usuario desde la BD para comprobar counters (necesita app context)
    with client.application.app_context():
        usuario = Usuario.query.filter_by(email='reserve_activo@academia.com').first()
        assert usuario is not None
        # tras login correcto el contador debe ser 0
        assert usuario.failed_login_count == 0 or usuario.failed_login_count is None

    # 5 intentos con contraseña incorrecta -> 401 cada uno
    MAX_FAILED = 5
    for i in range(1, MAX_FAILED + 1):
        rv = client.post('/auth/login', json={'email': 'reserve_activo@academia.com', 'password': 'wrong_password'})
        print(f"Intento incorrecto #{i}, status_code={rv.status_code}, body={rv.get_json()}")
        assert rv.status_code == 401

    # Refrescar usuario desde BD (dentro de app context)
    with client.application.app_context():
        usuario = Usuario.query.filter_by(email='reserve_activo@academia.com').first()
        assert usuario.failed_login_count >= MAX_FAILED
        # Comprobar que el estado del usuario es 'Bloqueado'
        assert usuario.estado == 'Bloqueado', f"Estado esperado: 'Bloqueado', estado actual: {usuario.estado}"

    # Intento adicional -> 403 (bloqueado)
    rv_blocked = client.post('/auth/login', json={'email': 'reserve_activo@academia.com', 'password': 'wrong_password'})
    print("Intento después de alcanzar MAX_FAILED, status_code=", rv_blocked.status_code, "body=", rv_blocked.get_json())
    assert rv_blocked.status_code == 403

    # Comprobar que existe al menos un UserLoginLog con fail_reason BAD_CREDENTIALS y uno con LOCKED
    with client.application.app_context():
        logs_bad = UserLoginLog.query.filter_by(usuario_id=usuario.id, fail_reason='BAD_CREDENTIALS').count()
        logs_locked = UserLoginLog.query.filter_by(usuario_id=usuario.id, fail_reason='LOCKED').count()
        assert logs_bad >= MAX_FAILED
        # El registro con LOCKED se genera cuando se intenta loguear tras el bloqueo temporal
        assert logs_locked >= 1


def test_login_blocking_after_failed_attempts_academia_user(client):
    """
    Prueba 10: Bloqueo tras intentos fallidos para un usuario activo vinculado a una academia.
    Entrada: usuario activo inicia sesión correctamente (resetea contador), luego intenta iniciar sesión con contraseña incorrecta repetidamente.
    Salida esperada: Los primeros 5 intentos (MAX_FAILED) devuelven 401; el intento siguiente devuelve 403 (usuario temporalmente bloqueado).
    """
    print("\nPrueba 10: Ejecutando test_login_blocking_after_failed_attempts_academia_user - Simular fallos hasta bloqueo para usuario de academia.")

    # Asegurar estado limpio: resetear estado, contador y contraseña del usuario
    with client.application.app_context():
        usuario = Usuario.query.filter_by(email='reserve_user_academia_1_1@academia.com').first()
        assert usuario is not None, "El usuario user_academia_1_1@academia.com no existe en la base de datos."
        print(f"Estado inicial del usuario: {usuario.estado}, failed_login_count: {usuario.failed_login_count}, contraseña almacenada: {usuario.password}")
        usuario.estado = 'Activo'
        usuario.failed_login_count = 0
        usuario.password = hash_password('password_reserve_user_academia_1_1')  # Restablecer la contraseña esperada (hasheada)
        db.session.commit()
        print("Estado del usuario después de resetear: Activo, failed_login_count: 0, contraseña actualizada.")

    # Asegurar estado limpio: login correcto para resetear contadores
    rv_ok = client.post('/auth/login', json={'email': 'reserve_user_academia_1_1@academia.com', 'password': 'password_reserve_user_academia_1_1'})
    print(f"Respuesta del servidor al intentar login correcto: {rv_ok.get_json()}")
    assert rv_ok.status_code == 200, f"Error: Se esperaba 200 OK, pero se obtuvo {rv_ok.status_code}. Respuesta: {rv_ok.get_json()}"

    # Obtener el usuario desde la BD para comprobar counters (necesita app context)
    with client.application.app_context():
        usuario = Usuario.query.filter_by(email='user_academia_1_1@academia.com').first()
        assert usuario is not None
        # tras login correcto el contador debe ser 0
        assert usuario.failed_login_count == 0 or usuario.failed_login_count is None

    # 5 intentos con contraseña incorrecta -> 401 cada uno
    MAX_FAILED = 5
    for i in range(1, MAX_FAILED + 1):
        rv = client.post('/auth/login', json={'email': 'reserve_user_academia_1_1@academia.com', 'password': 'wrong_password'})
        print(f"Intento incorrecto #{i}, status_code={rv.status_code}, body={rv.get_json()}")
        assert rv.status_code == 401

    # Refrescar usuario desde BD (dentro de app context)
    with client.application.app_context():
        usuario = Usuario.query.filter_by(email='reserve_user_academia_1_1@academia.com').first()
        assert usuario.failed_login_count >= MAX_FAILED
        # Comprobar que el estado del usuario es 'Bloqueado'
        assert usuario.estado == 'Bloqueado', f"Estado esperado: 'Bloqueado', estado actual: {usuario.estado}"

    # Intento adicional -> 403 (bloqueado)
    rv_blocked = client.post('/auth/login', json={'email': 'reserve_user_academia_1_1@academia.com', 'password': 'wrong_password'})
    print("Intento después de alcanzar MAX_FAILED, status_code=", rv_blocked.status_code, "body=", rv_blocked.get_json())
    assert rv_blocked.status_code == 403