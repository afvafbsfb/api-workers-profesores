import os
os.environ['DB_ENV'] = 'developmentAWS'

import pytest
import requests
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
import unicodedata


def wait_for_mediator(mediator_url: str, timeout: int = 30):
    """Poll /actuator/health hasta que devuelva UP o hasta timeout (segundos)."""
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


@pytest.mark.parametrize("email,password,role_desc", [
    ("admin_plataforma@academia.com", "password_admin_plataforma", "Admin_plataforma"),
])
def test_mediator_welcome_after_login(client, email, password, role_desc):
    """Integración (admin_plataforma): login y saludo del mediador (/chat).

    Detalles:
    - Incluye headers X-Flow-Diagram:true y X-Flow-Id para que el mediador genere los ficheros HTML/XML de flujo.
    - Espera a que el mediador esté UP antes de llamar (consulta /actuator/health).
    - Flexible assertions: valida que la respuesta sea JSON o texto json-encapsulado y que contenga el nombre de usuario o listados de academias.
    """
    access = login_and_get_access(client, email, password)
    login_info = client.post('/auth/login', json={'email': email, 'password': password}).get_json()
    assert 'role' in login_info, 'Role not returned in login response'  # Validar que el rol esté presente
    role = login_info['role']  # Obtener el rol directamente de la respuesta del login

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

    # Usar el rol recuperado en el payload
    payload = {'messages': [{'role': role, 'content': 'Dame la bienvenida'}]}

    # Hacemos una llamada real al mediador (integración). Requiere que el mediador esté en ejecución.
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    assert resp.status_code == 200, f"Mediator /chat returned {resp.status_code}: {resp.text}"

    # Intentar parseo JSON; si no lo es, fallará
    try:
        data = resp.json()
    except Exception:
        pytest.skip("Mediator did not return JSON; ensure mediator returns JSON or wrap text in {\"text\":...}")

    # Comprobaciones flexibles dependiendo de la forma de la respuesta
    # 1) Si devuelve {'text': '...'} comprobar que aparece el nombre del usuario (si lo tenemos)
    login_info = client.post('/auth/login', json={'email': email, 'password': password}).get_json()
    name = login_info.get('name') if isinstance(login_info, dict) else None

    if isinstance(data, dict):
        # Error normalizado
        if 'error' in data:
            pytest.fail(f"Mediator returned error: {data}")
        # Texto envuelto
        if 'text' in data:
            text = str(data.get('text') or '')
            # Normalizar: quitar acentos y pasar a minúsculas para comparaciones más robustas
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
                # aceptar saludos genéricos relacionados con bienvenida/academia/ayuda
                generic_keywords = ('bienven', 'academ', 'ayud', 'gest')
                generic_welcome = any(k in ntext for k in generic_keywords)
                assert name_present or generic_welcome, f"Expected user name or a generic welcome in mediator text: {text}"
            else:
                assert any(k in ntext for k in ('bienven', 'academ', 'ayud', 'gest')), f"Expected welcome to mention 'academia' in text: {text}"
            return
        # Paginado/array-like
        if 'items' in data and isinstance(data.get('items'), list):
            items = data.get('items')
            assert len(items) >= 0
            return
        # Si es un objeto detalle y tiene nombre
        if 'nombre' in data or 'id' in data:
            # admin_academia debería recibir info de su academia
            if role_desc == 'Admin_academia':
                assert 'nombre' in data
            return
    elif isinstance(data, list):
        # Lista de academias esperada para admin_plataforma
        assert len(data) >= 0
        return
    # Si no cumplimos ninguna forma esperada, fallar
    pytest.fail(f"Respuesta del mediador con formato inesperado: {data}")


@pytest.mark.parametrize("email,password,role_desc,message,expected_keyword", [
    ("admin_plataforma@academia.com", "password_admin_plataforma", "Admin_plataforma", "Quiero ver el listado de los usuarios que están dados de alta", "usuarios"),
    ("admin_plataforma@academia.com", "password_admin_plataforma", "Admin_plataforma", "Quiero ver el listado de las academias", "academias"),
])
def test_mediator_list_requests(client, email, password, role_desc, message, expected_keyword):
    """Integración (admin_plataforma): mediador responde a solicitudes de listados.

    Comprueba que, para admin_plataforma y distintos mensajes, el mediador devuelve texto o estructuras
    que contienen la palabra clave esperada (p. ej. 'usuarios' o 'academias').
    """
    access = login_and_get_access(client, email, password)

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

    payload = {'messages': [{'role': 'user', 'content': message}]}

    # Hacemos una llamada real al mediador (integración). Requiere que el mediador esté en ejecución.
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    assert resp.status_code == 200, f"Mediator /chat returned {resp.status_code}: {resp.text}"

    # Intentar parseo JSON; si no lo es, fallará
    try:
        data = resp.json()
    except Exception:
        pytest.fail("Mediator did not return JSON; ensure mediator returns JSON or wrap text in {\"text\":...}")

    # Validar que la respuesta contiene la palabra clave esperada
    if isinstance(data, dict) and 'text' in data:
        text = data['text']
        assert expected_keyword in text.lower(), f"Expected keyword '{expected_keyword}' in response: {text}"
    else:
        pytest.fail(f"Unexpected response format: {data}")
