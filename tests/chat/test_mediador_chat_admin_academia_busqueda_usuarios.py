import os
os.environ['DB_ENV'] = 'developmentAWS'

import pytest
import requests
import jwt
from app import create_app
from config import Config


@pytest.fixture
def client():
    Config.set_environment_variables()
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        yield app.test_client()


def login_and_get_access(email: str, password: str) -> str:
    base_url = "http://127.0.0.1:5000"

    login_response = requests.post(f"{base_url}/auth/login", json={'email': email, 'password': password})
    assert login_response.status_code == 200, f"Login failed: {login_response.json()}"
    data = login_response.json()
    tokens = data.get('tokens') or {}
    access = tokens.get('access_token')
    assert access, 'No access token returned from login'
    return access


import uuid
import time


def wait_for_mediator(mediator_url: str, timeout: int = 30):
    health = f"{mediator_url.rstrip('/')}/actuator/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(health, timeout=3)
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


def test_mediador_busqueda_usuarios_admin_academia(client):
    """Login as admin_academia and request the users listing via the mediator (/chat).

    This test performs only a login and a single /chat request that asks for the list of users.
    It asserts the mediator returns JSON and that the text contains the word 'usuarios'.
    """
    email = "admin_academia@academia.com"
    password = "password_admin_academia"
    access = login_and_get_access(email, password)

    # Obtener el rol del usuario después del login
    login_info = client.post('/auth/login', json={'email': email, 'password': password}).get_json()
    assert 'role' in login_info, 'Role not returned in login response'
    role = login_info['role']  # Definir la variable `role`

    mediator_url = os.environ.get('MEDIATOR_URL', 'http://localhost:8080')
    assert wait_for_mediator(mediator_url, timeout=20), f"Mediator at {mediator_url} not available"
    url = f"{mediator_url.rstrip('/')}/chat"

    flow_id = str(uuid.uuid4())
    headers = {
        'Authorization': f'Bearer {access}',
        'Content-Type': 'application/json',
        'X-Flow-Diagram': 'true',
        'X-Flow-Id': flow_id,
    }

    # Map all roles to 'user' for OpenAI compatibility
    openai_role = 'user'

    payload = {
        'messages': [
            {'role': openai_role, 'content': 'Quiero ver el listado de los usuarios que están dados de alta'}
        ]
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    assert resp.status_code == 200, f"Mediator /chat returned {resp.status_code}: {resp.text}"

    try:
        data = resp.json()
    except Exception:
        pytest.fail('Mediator did not return JSON; ensure mediator returns JSON or wrap text in {"text":...}')

    if isinstance(data, dict) and 'text' in data:
        text = data['text']
        assert 'usuarios' in text.lower(), f"Expected keyword 'usuarios' in response: {text}"
    else:
        pytest.fail(f"Unexpected response format: {data}")
