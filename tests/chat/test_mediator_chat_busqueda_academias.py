import os
os.environ['DB_ENV'] = 'developmentAWS'

import pytest
import requests
from config import Config

# Configuration at top of file (always set here):
API_WORKER_URL = 'http://127.0.0.1:5000'
MEDIATOR_URL = 'http://localhost:8080'
TEST_EMAIL = 'admin_academia@academia.com'
TEST_PASSWORD = 'password_admin_academia'

def login_and_get_access(email: str, password: str) -> str:
    base_url = TEST_API_URL

    login_response = requests.post(f"{base_url}/auth/login", json={'email': email, 'password': password})
    assert login_response.status_code == 200
    data = login_response.json()
    tokens = data.get('tokens') or {}
    access = tokens.get('access_token')
    assert access, 'No access token returned from login'
    return access


import uuid
import time
import unicodedata


def wait_for_mediator(mediator_url: str, timeout: int = 30):
    health = f"{mediator_url.rstrip('/')}" + '/actuator/health'
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(health, timeout=90)
            if r.status_code == 200 and r.json().get('status') == 'UP':
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


@pytest.mark.parametrize("email,password,role_desc", [
    ("admin_academia@academia.com", "password_admin_academia", "Admin_academia"),
])
def test_mediator_welcome_after_login_admin_academia(email, password, role_desc):
    """Integración (admin_academia): login y saludo del mediador (/chat)."""
    access = login_and_get_access(email, password)
    login_info = requests.post(f"{API_WORKER_URL}/auth/login", json={'email': email, 'password': password}).json()
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

    # Usar el rol recuperado en el payload
    payload = {'messages': [{'role': role, 'content': 'Dame la bienvenida'}]}

    resp = requests.post(url, json=payload, headers=headers, timeout=90)
    assert resp.status_code == 200, f"Mediator /chat returned {resp.status_code}: {resp.text}"

    try:
        envelope = resp.json()
    except Exception:
        pytest.fail('Mediator did not return JSON envelope')

    assert isinstance(envelope, dict), 'Envelope debe ser dict'
    assert envelope.get('status') == 'success', f"status inesperado: {envelope.get('status')}"
    # Mensaje principal debe contener bienvenida o academia
    main_message = (envelope.get('message') or '').lower()
    if main_message:
        assert any(k in main_message for k in ('bienven', 'academ', 'ayud', 'gest')), f"Mensaje de bienvenida no contiene palabras clave: {main_message}"
    # data es opcional en un mensaje de bienvenida, pero si existe validar estructura
    data = envelope.get('data')
    if data:
        assert 'items' in data, 'Falta items en data'
        assert isinstance(data.get('items'), list), 'items debe ser lista'
    # error no debe estar
    assert envelope.get('error') in (None, {}), 'error debe ser nulo en success'


@pytest.mark.parametrize("email,password,role_desc,message,expected_keyword", [
    ("admin_academia@academia.com", "password_admin_academia", "Admin_academia", "Quiero ver el listado de los usuarios que están dados de alta", "usuarios"),
    ("admin_academia@academia.com", "password_admin_academia", "Admin_academia", "Quiero ver el listado de las academias", "academia"),
])
def test_mediator_list_requests_admin_academia(email, password, role_desc, message, expected_keyword):
    """Integración (admin_academia): mediador responde a solicitudes de listados."""
    access = login_and_get_access(email, password)
    login_info = requests.post(f"{TEST_API_URL}/auth/login", json={'email': email, 'password': password}).json()
    assert 'role' in login_info, 'Role not returned in login response'  # Validar que el rol esté presente
    role = login_info['role']  # Obtener el rol directamente de la respuesta del login

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

    # Usar el rol recuperado en el payload
    openai_role = 'user'  # Mapear todos los roles a 'user'
    payload = {
        'messages': [
            {'role': openai_role, 'content': message}
        ]
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=90)
    assert resp.status_code == 200, f"Mediator /chat returned {resp.status_code}: {resp.text}"

    try:
        envelope = resp.json()
    except Exception:
        pytest.fail('Mediator did not return JSON envelope')

    assert isinstance(envelope, dict), 'Envelope debe ser dict'
    assert envelope.get('status') == 'success', f"status inesperado: {envelope.get('status')}"
    data = envelope.get('data') or {}
    assert 'items' in data, 'Falta items en data'
    assert isinstance(data.get('items'), list), 'items debe ser lista'
    # Validar keyword en message o en type o en items
    main_message = (envelope.get('message') or '').lower()
    items_join = ' '.join([str(it).lower() for it in data.get('items')])
    assert (
        expected_keyword in main_message
        or data.get('type') == expected_keyword
        or expected_keyword in items_join
    ), f"No se detecta '{expected_keyword}' en envelope: {envelope}"
    assert envelope.get('error') in (None, {}), 'error debe ser nulo en success'
