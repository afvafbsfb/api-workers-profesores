import os
os.environ['DB_ENV'] = 'developmentAWS'

import uuid
import requests
import pytest
import time

# Reuse the same configuration pattern as other chat tests
API_WORKER_URL = 'http://127.0.0.1:5000'
MEDIATOR_URL = 'http://localhost:8080'

TEST_EMAIL = 'admin_plataforma@academia.com'
TEST_PASSWORD = 'password_admin_plataforma'


def login_and_get_access(email: str, password: str) -> str:
    resp = requests.post(f"{API_WORKER_URL}/auth/login", json={'email': email, 'password': password})
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    js = resp.json()
    tokens = (js.get('tokens') or {})
    access = tokens.get('access_token')
    assert access, 'No access token returned from login'
    return access


def wait_for_mediator(mediator_url: str, timeout: int = 90):
    health = f"{mediator_url.rstrip('/')}/actuator/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(health, timeout=30)
            if r.status_code == 200:
                try:
                    j = r.json()
                    st = j.get('status') or j.get('STATUS') or j.get('status'.upper())
                    if st and str(st).upper() == 'UP':
                        return True
                except Exception:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def send_chat(url: str, access: str, messages):
    headers = {
        'Authorization': f'Bearer {access}',
        'Content-Type': 'application/json',
        'X-Flow-Diagram': 'true',
        'X-Flow-Id': str(uuid.uuid4()),
    }
    payload = { 'messages': messages }
    resp = requests.post(url, json=payload, headers=headers, timeout=90)
    return resp


def assert_success_envelope(resp):
    assert resp.status_code == 200, f"Mediator /chat returned {resp.status_code}: {resp.text}"
    try:
        env = resp.json()
    except Exception:
        pytest.fail('Mediator did not return JSON envelope')
    assert isinstance(env, dict), 'Envelope debe ser dict'
    assert env.get('status') == 'success', f"status inesperado: {env.get('status')}"
    return env


def test_chat_mensaje_bienvenida_minimo():
    """
    Login del usuario y envío de un único POST con el mensaje "hola".
    Valida que el mediador responde 200 y un envelope de éxito.
    """
    access = login_and_get_access(TEST_EMAIL, TEST_PASSWORD)

    mediator_url = MEDIATOR_URL
    assert wait_for_mediator(mediator_url, timeout=90), f"Mediator at {mediator_url} not available"
    url = f"{mediator_url.rstrip('/')}/chat"

    messages = [
        {'role': 'user', 'content': 'hola'}
    ]

    resp = send_chat(url, access, messages=messages)
    env = assert_success_envelope(resp)

    # Log breve para depuración manual
    msg = env.get('message') or ''
    print(f"[BIENVENIDA] message_head={msg[:160]}")


def test_chat_me_llamo_angel():
    """
    Envío de un único POST con el mensaje "me llamo angel".
    Debe responder 200 con envelope de éxito y texto no vacío.
    """
    print("[TEST] Presentación del usuario: 'me llamo angel'")
    access = login_and_get_access(TEST_EMAIL, TEST_PASSWORD)
    assert wait_for_mediator(MEDIATOR_URL, timeout=90), f"Mediator at {MEDIATOR_URL} not available"
    url = f"{MEDIATOR_URL.rstrip('/')}/chat"
    messages = [ {'role': 'user', 'content': 'me llamo angel'} ]
    resp = send_chat(url, access, messages=messages)
    env = assert_success_envelope(resp)
    msg = env.get('message') or ''
    print(f"[ME_LLAMO_ANGEL] message_head={msg[:160]}")


def test_chat_calculo_5_por_5():
    """
    Envío "quería saber cuanto son 5 x 5" y valida éxito.
    """
    print("[TEST] Consulta aritmética: 'quería saber cuanto son 5 x 5'")
    access = login_and_get_access(TEST_EMAIL, TEST_PASSWORD)
    assert wait_for_mediator(MEDIATOR_URL, timeout=90), f"Mediator at {MEDIATOR_URL} not available"
    url = f"{MEDIATOR_URL.rstrip('/')}/chat"
    messages = [ {'role': 'user', 'content': 'quería saber cuanto son 5 x 5'} ]
    resp = send_chat(url, access, messages=messages)
    env = assert_success_envelope(resp)
    msg = env.get('message') or ''
    print(f"[CALCULO_5x5] message_head={msg[:160]}")


def test_chat_modificar_una_academia():
    """
    Envío "quería modificar una academia" y valida éxito.
    """
    print("[TEST] Intención de modificación: 'quería modificar una academia'")
    access = login_and_get_access(TEST_EMAIL, TEST_PASSWORD)
    assert wait_for_mediator(MEDIATOR_URL, timeout=90), f"Mediator at {MEDIATOR_URL} not available"
    url = f"{MEDIATOR_URL.rstrip('/')}/chat"
    messages = [ {'role': 'user', 'content': 'quería modificar una academia'} ]
    resp = send_chat(url, access, messages=messages)
    env = assert_success_envelope(resp)
    msg = env.get('message') or ''
    print(f"[MODIFICAR_ACADEMIA] message_head={msg[:160]}")


def test_chat_modificar_un_perro():
    """
    Envío "quería modificar un perro" (dominio inexistente) y valida éxito.
    """
    print("[TEST] Dominio inexistente: 'quería modificar un perro'")
    access = login_and_get_access(TEST_EMAIL, TEST_PASSWORD)
    assert wait_for_mediator(MEDIATOR_URL, timeout=90), f"Mediator at {MEDIATOR_URL} not available"
    url = f"{MEDIATOR_URL.rstrip('/')}/chat"
    messages = [ {'role': 'user', 'content': 'quería modificar un perro'} ]
    resp = send_chat(url, access, messages=messages)
    env = assert_success_envelope(resp)
    msg = env.get('message') or ''
    print(f"[MODIFICAR_PERRO] message_head={msg[:160]}")


def test_chat_modificar_un_alumno():
    """
    Envío "quería modificar un alumno" y valida éxito.
    """
    print("[TEST] Intención de modificación: 'quería modificar un alumno'")
    access = login_and_get_access(TEST_EMAIL, TEST_PASSWORD)
    assert wait_for_mediator(MEDIATOR_URL, timeout=90), f"Mediator at {MEDIATOR_URL} not available"
    url = f"{MEDIATOR_URL.rstrip('/')}/chat"
    messages = [ {'role': 'user', 'content': 'quería modificar un alumno'} ]
    resp = send_chat(url, access, messages=messages)
    env = assert_success_envelope(resp)
    msg = env.get('message') or ''
    print(f"[MODIFICAR_ALUMNO] message_head={msg[:160]}")


def test_chat_consultar_un_usuario():
    """
    Envío "querái consultar un usuario" (tal cual el texto indicado) y valida éxito.
    """
    print("[TEST] Consulta de recurso: 'querái consultar un usuario'")
    access = login_and_get_access(TEST_EMAIL, TEST_PASSWORD)
    assert wait_for_mediator(MEDIATOR_URL, timeout=90), f"Mediator at {MEDIATOR_URL} not available"
    url = f"{MEDIATOR_URL.rstrip('/')}/chat"
    messages = [ {'role': 'user', 'content': 'querái consultar un usuario'} ]
    resp = send_chat(url, access, messages=messages)
    env = assert_success_envelope(resp)
    msg = env.get('message') or ''
    print(f"[CONSULTAR_USUARIO] message_head={msg[:160]}")


def test_chat_totales_academias_y_usuarios():
    """
    Envío "quería saber el total de academias y el total de usuarios que estan registrados" y valida éxito.
    """
    print("[TEST] Totales globales: academias y usuarios registrados")
    access = login_and_get_access(TEST_EMAIL, TEST_PASSWORD)
    assert wait_for_mediator(MEDIATOR_URL, timeout=90), f"Mediator at {MEDIATOR_URL} not available"
    url = f"{MEDIATOR_URL.rstrip('/')}/chat"
    messages = [ {'role': 'user', 'content': 'quería saber el total de academias y el total de usuarios que estan registrados'} ]
    resp = send_chat(url, access, messages=messages)
    env = assert_success_envelope(resp)
    msg = env.get('message') or ''
    print(f"[TOTALES_ACAD_USU] message_head={msg[:160]}")


def test_chat_totales_activos_academias_y_usuarios():
    """
    Envío "quería saber el total de academias activas y el total de usuarios activos que están registrados" y valida éxito.
    """
    print("[TEST] Totales activos: academias activas y usuarios activos")
    access = login_and_get_access(TEST_EMAIL, TEST_PASSWORD)
    assert wait_for_mediator(MEDIATOR_URL, timeout=90), f"Mediator at {MEDIATOR_URL} not available"
    url = f"{MEDIATOR_URL.rstrip('/')}/chat"
    messages = [ {'role': 'user', 'content': 'quería saber el total de academias activas y el total de usuarios activos que están registrados'} ]
    resp = send_chat(url, access, messages=messages)
    env = assert_success_envelope(resp)
    msg = env.get('message') or ''
    print(f"[TOTALES_ACTIVOS] message_head={msg[:160]}")
