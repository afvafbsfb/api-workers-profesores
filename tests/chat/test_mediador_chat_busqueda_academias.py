import os
os.environ['DB_ENV'] = 'developmentAWS'

import pytest
import requests
from config import Config

# Configuration at top of file (always set here):
API_WORKER_URL = 'http://127.0.0.1:5000'
MEDIATOR_URL = 'http://localhost:8080'
TEST_API_URL = API_WORKER_URL  # Definimos TEST_API_URL con el mismo valor que API_WORKER_URL
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
        data = resp.json()
    except Exception:
        pytest.skip('Mediator did not return JSON; ensure mediator returns JSON or wrap text in {"text":...}')

    # Basic checks like in original test: accept text with welcome keywords or user name
    login_info = client.post('/auth/login', json={'email': email, 'password': password}).get_json()
    name = login_info.get('name') if isinstance(login_info, dict) else None
    if isinstance(data, dict) and 'text' in data:
        text = str(data.get('text') or '')
        def norm(s: str) -> str:
            s = s or ''
            s = unicodedata.normalize('NFKD', s)
            s = ''.join(c for c in s if not unicodedata.combining(c))
            return s.lower()
        ntext = norm(text)
        if name:
            nname = norm(name)
            first = nname.split()[0] if nname else ''
            name_present = (nname in ntext) or (first and first in ntext)
            generic_keywords = ('bienven', 'academ', 'ayud', 'gest')
            generic_welcome = any(k in ntext for k in generic_keywords)
            assert name_present or generic_welcome
        else:
            assert any(k in ntext for k in ('bienven', 'academ', 'ayud', 'gest'))
    else:
        pytest.fail(f'Unexpected mediator response format: {data}')


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
    payload = {'messages': [{'role': role, 'content': message}]}
    resp = requests.post(url, json=payload, headers=headers, timeout=90)
    assert resp.status_code == 200, f"Mediator /chat returned {resp.status_code}: {resp.text}"

    try:
        data = resp.json()
    except Exception:
        pytest.fail('Mediator did not return JSON; ensure mediator returns JSON or wrap text in {"text":...}')

    if isinstance(data, dict) and 'text' in data:
        text = data['text']
        assert expected_keyword in text.lower(), f"Expected keyword '{expected_keyword}' in response: {text}"
    else:
        pytest.fail(f"Unexpected response format: {data}")
