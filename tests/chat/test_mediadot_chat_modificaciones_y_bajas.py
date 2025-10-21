import os
os.environ['DB_ENV'] = 'developmentAWS'

import uuid
import requests
import pytest
import time

# Configuración común (alineada con otros tests de chat)
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


# ----------------------- TESTS DE MODIFICACIONES Y BAJAS -----------------------

def test_chat_modificar_mi_usuario_a_angelito():
    """
    POST con: "quiero que modifiques mi usuario para que pase a llamarme angelito"
    Valida 200 y envelope de éxito.
    """
    print("[TEST] Modificar mi usuario a 'angelito'")
    access = login_and_get_access(TEST_EMAIL, TEST_PASSWORD)
    assert wait_for_mediator(MEDIATOR_URL, timeout=90), f"Mediator at {MEDIATOR_URL} not available"
    url = f"{MEDIATOR_URL.rstrip('/')}/chat"
    messages = [ {'role': 'user', 'content': 'quiero que modifiques mi usuario para que pase a llamarme angelito'} ]
    resp = send_chat(url, access, messages=messages)
    env = assert_success_envelope(resp)
    msg = env.get('message') or ''
    print(f"[MODIFICAR_MI_USUARIO_ANGELITO] message_head={msg[:160]}")


def test_chat_confirmacion_te_confirmo():
    """
    POST con: "te confirmo"
    Valida 200 y envelope de éxito.
    """
    print("[TEST] Confirmación: 'te confirmo'")
    access = login_and_get_access(TEST_EMAIL, TEST_PASSWORD)
    assert wait_for_mediator(MEDIATOR_URL, timeout=90), f"Mediator at {MEDIATOR_URL} not available"
    url = f"{MEDIATOR_URL.rstrip('/')}/chat"
    messages = [ {'role': 'user', 'content': 'te confirmo'} ]
    resp = send_chat(url, access, messages=messages)
    env = assert_success_envelope(resp)
    msg = env.get('message') or ''
    print(f"[CONFIRMACION_TE_CONFIRMO] message_head={msg[:160]}")


def test_chat_modificar_mi_usuario_a_angelillo_confirmo():
    """
    POST con: "quiero que modifiques mi usuario para que se pase a llamar angelillo. Te confirmo que por favor realices ya la modificacion"
    Valida 200 y envelope de éxito.
    """
    print("[TEST] Modificar mi usuario a 'angelillo' con confirmación en el mismo mensaje")
    access = login_and_get_access(TEST_EMAIL, TEST_PASSWORD)
    assert wait_for_mediator(MEDIATOR_URL, timeout=90), f"Mediator at {MEDIATOR_URL} not available"
    url = f"{MEDIATOR_URL.rstrip('/')}/chat"
    messages = [ {'role': 'user', 'content': 'quiero que modifiques mi usuario para que se pase a llamar angelillo. Te confirmo que por favor realices ya la modificacion'} ]
    resp = send_chat(url, access, messages=messages)
    env = assert_success_envelope(resp)
    msg = env.get('message') or ''
    print(f"[MODIFICAR_MI_USUARIO_ANGELILLO_CONFIRMO] message_head={msg[:160]}")


def test_chat_modificar_usuario_por_email_a_alberto():
    """
    POST con: "quiero que modifiques el usuario cuyo email es admin_plataforma@academia.com para que su nombre sea Alberto"
    Valida 200 y envelope de éxito.
    """
    print("[TEST] Modificar usuario por email a nombre 'Alberto'")
    access = login_and_get_access(TEST_EMAIL, TEST_PASSWORD)
    assert wait_for_mediator(MEDIATOR_URL, timeout=90), f"Mediator at {MEDIATOR_URL} not available"
    url = f"{MEDIATOR_URL.rstrip('/')}/chat"
    messages = [ {'role': 'user', 'content': 'quiero que modifiques el usuario cuyo email es admin_plataforma@academia.com para que su nombre sea Alberto'} ]
    resp = send_chat(url, access, messages=messages)
    env = assert_success_envelope(resp)
    msg = env.get('message') or ''
    print(f"[MODIFICAR_USUARIO_EMAIL_ALBERTO] message_head={msg[:160]}")


def test_chat_confirmacion_si_modificalo():
    """
    POST con: "Sí, modificalo."
    Valida 200 y envelope de éxito.
    """
    print("[TEST] Confirmación: 'Sí, modificalo.'")
    access = login_and_get_access(TEST_EMAIL, TEST_PASSWORD)
    assert wait_for_mediator(MEDIATOR_URL, timeout=90), f"Mediator at {MEDIATOR_URL} not available"
    url = f"{MEDIATOR_URL.rstrip('/')}/chat"
    messages = [ {'role': 'user', 'content': 'Sí, modificalo.'} ]
    resp = send_chat(url, access, messages=messages)
    env = assert_success_envelope(resp)
    msg = env.get('message') or ''
    print(f"[CONFIRMACION_SI_MODIFICALO] message_head={msg[:160]}")
