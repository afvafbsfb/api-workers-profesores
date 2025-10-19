import os
os.environ['DB_ENV'] = 'developmentAWS'

import pytest
import requests
from config import Config

# Configuration at top of file (always set here):
# API worker and mediator addresses used by the integration tests
API_WORKER_URL = 'http://127.0.0.1:5000'
MEDIATOR_URL = 'http://localhost:8080'
# Optional creds used by some tests (override here if needed)
TEST_EMAIL = 'profesor_test_1@academia.com'
TEST_PASSWORD = 'password_profesor1'


def login_and_get_access(email: str, password: str) -> str:
    base_url = API_WORKER_URL

    login_response = requests.post(f"{base_url}/auth/login", json={'email': email, 'password': password})
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    data = login_response.json()
    tokens = data.get('tokens') or {}
    access = tokens.get('access_token')
    assert access, 'No access token returned from login'
    return access


import uuid
import time
import unicodedata


def wait_for_mediator(mediator_url: str, timeout: int = 30):
    """Poll /actuator/health hasta que devuelva UP o hasta timeout (segundos)."""
    health = f"{mediator_url.rstrip('/')}/actuator/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(health, timeout=90)
            if r.status_code == 200:
                try:
                    j = r.json()
                    status = j.get('status') or j.get('STATUS') or j.get('status'.upper())
                    if status and str(status).upper() == 'UP':
                        return True
                except Exception:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


@pytest.mark.parametrize("email,password,role_desc", [
    ("admin_plataforma@academia.com", "password_admin_plataforma", "Admin_plataforma"),
])
def test_mediator_welcome_after_login(email, password, role_desc):
    """Integración (admin_plataforma): login y saludo del mediador (/chat).

    Detalles:
    - Incluye headers X-Flow-Diagram:true y X-Flow-Id para que el mediador genere los ficheros HTML/XML de flujo.
    - Espera a que el mediador esté UP antes de llamar (consulta /actuator/health).
    - Flexible assertions: valida que la respuesta sea JSON o texto json-encapsulado y que contenga el nombre de usuario o listados de academias.
    """
    print(f">>> PRUEBA: mediador bienvenida [rol={role_desc}]")
    access = login_and_get_access(email, password)
    login_info = requests.post(f"{TEST_API_URL}/auth/login", json={'email': email, 'password': password}).json()
    assert 'role' in login_info, 'Role not returned in login response'  # Validar que el rol esté presente
    role = login_info['role']  # Obtener el rol directamente de la respuesta del login

    mediator_url = MEDIATOR_URL
    assert wait_for_mediator(mediator_url, timeout=90), f"Mediator at {mediator_url} not available"
    url = f"{mediator_url.rstrip('/')}/chat"

    flow_id = str(uuid.uuid4())
    headers = {
        'Authorization': f'Bearer {access}',
        'Content-Type': 'application/json',
        'X-Flow-Diagram': 'true',
        'X-Flow-Id': flow_id,
    }

    openai_role = 'user'  # Mapear todos los roles a 'user'
    payload = {
        'messages': [
            {'role': openai_role, 'content': 'Dame la bienvenida'}
        ]
    }

    # Hacemos una llamada real al mediador (integración). Requiere que el mediador esté en ejecución.
    resp = requests.post(url, json=payload, headers=headers, timeout=90)
    assert resp.status_code == 200, f"Mediator /chat returned {resp.status_code}: {resp.text}"

    try:
        envelope = resp.json()
    except Exception:
        pytest.fail('Mediator did not return JSON envelope')

    assert isinstance(envelope, dict), 'Envelope debe ser dict'
    assert envelope.get('status') == 'success', f"status inesperado: {envelope.get('status')}"
    # Validar mensaje de bienvenida
    main_message = (envelope.get('message') or '').lower()
    assert any(k in main_message for k in ('bienven','academ','ayud','gest')), f"Mensaje no parece bienvenida: {main_message}"
    # data opcional
    data_section = envelope.get('data')
    if data_section:
        assert 'items' in data_section, 'Falta items en data'
        assert isinstance(data_section.get('items'), list), 'items debe ser lista'
    assert envelope.get('error') in (None, {}), 'error debe ser nulo en success'


@pytest.mark.parametrize("email,password,role_desc,message,expected_keyword", [
    ("admin_plataforma@academia.com", "password_admin_plataforma", "Admin_plataforma", "Quiero ver el listado de los usuarios que están dados de alta", "usuarios"),
    ("admin_plataforma@academia.com", "password_admin_plataforma", "Admin_plataforma", "Quiero ver el listado de las academias", "academias"),
])
def test_mediator_list_requests(email, password, role_desc, message, expected_keyword):
    """Integración (admin_plataforma): mediador responde a solicitudes de listados.

    Comprueba que, para admin_plataforma y distintos mensajes, el mediador devuelve texto o estructuras
    que contienen la palabra clave esperada (p. ej. 'usuarios' o 'academias').
    """
    short_msg = (message or "")
    if len(short_msg) > 60:
        short_msg = short_msg[:57] + "..."
    print(f">>> PRUEBA: mediador listados [rol={role_desc}] msg='{short_msg}' espera='{expected_keyword}'")
    access = login_and_get_access(email, password)

    mediator_url = os.environ.get('MEDIATOR_URL', 'http://localhost:8080')
    assert wait_for_mediator(mediator_url, timeout=90), f"Mediator at {mediator_url} not available"
    url = f"{mediator_url.rstrip('/')}/chat"

    flow_id = str(uuid.uuid4())
    headers = {
        'Authorization': f'Bearer {access}',
        'Content-Type': 'application/json',
        'X-Flow-Diagram': 'true',
        'X-Flow-Id': flow_id,
    }

    payload = {'messages': [{'role': 'user', 'content': message}]}

    # Hacemos una llamada real al mediador (integración). Requiere que el mediador esté en ejecución.
    resp = requests.post(url, json=payload, headers=headers, timeout=90)
    assert resp.status_code == 200, f"Mediator /chat returned {resp.status_code}: {resp.text}"

    try:
        envelope = resp.json()
    except Exception:
        pytest.fail('Mediator did not return JSON envelope')

    assert isinstance(envelope, dict), 'Envelope debe ser dict'
    assert envelope.get('status') == 'success', f"status inesperado: {envelope.get('status')}"
    data_section = envelope.get('data') or {}
    assert 'items' in data_section, 'Falta items en data'
    assert isinstance(data_section.get('items'), list), 'items debe ser lista'
    main_message = (envelope.get('message') or '').lower()
    items_join = ' '.join([str(it).lower() for it in data_section.get('items')])
    assert (
        expected_keyword in main_message
        or expected_keyword in items_join
        or data_section.get('type') == expected_keyword
    ), f"No se detecta '{expected_keyword}' en envelope: {envelope}"
    assert envelope.get('error') in (None, {}), 'error debe ser nulo en success'
