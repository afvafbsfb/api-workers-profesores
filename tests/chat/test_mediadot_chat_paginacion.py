import os
os.environ['DB_ENV'] = 'developmentAWS'

import uuid
import time
import base64
import json
import requests
import pytest

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


def send_chat(url: str, access: str, flow_id: str, messages):
    headers = {
        'Authorization': f'Bearer {access}',
        'Content-Type': 'application/json',
        'X-Flow-Diagram': 'true',
        'X-Flow-Id': flow_id,
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


def _get_ui_suggestions(env: dict):
    if not isinstance(env, dict):
        return []
    return env.get('uiSuggestions') or env.get('ui_suggestions') or []


def _pick_pagination_token(ui_suggestions: list, want: str = 'next') -> str | None:
    want = (want or '').lower()
    for s in (ui_suggestions or []):
        try:
            if s.get('type') == 'Paginacion':
                pag = s.get('pagination') or {}
                direction = (pag.get('direction') or '').lower()
                if direction == want:
                    tok = s.get('contextToken') or s.get('context_token')
                    if tok:
                        return tok
        except Exception:
            pass
    # fallback por texto, por si acaso
    for s in (ui_suggestions or []):
        try:
            text = (s.get('displayText') or s.get('text') or '').lower()
            if want == 'next' and (('siguiente' in text) or ('ver más' in text) or ('ver mas' in text)):
                tok = s.get('contextToken') or s.get('context_token')
                if tok:
                    return tok
            if want == 'prev' and ('anterior' in text):
                tok = s.get('contextToken') or s.get('context_token')
                if tok:
                    return tok
        except Exception:
            pass
    return None


def _decode_context_token(token: str) -> dict | None:
    """Decodifica el contextToken generado por el backend.
    Formato esperado: base64url(JSON). A veces termina con '.' como separador, lo retiramos.
    """
    if not token or not isinstance(token, str):
        return None
    try:
        t = token.strip()
        if t.endswith('.'):
            t = t[:-1]
        # padding a múltiplo de 4
        padding = '=' * ((4 - (len(t) % 4)) % 4)
        raw = base64.urlsafe_b64decode(t + padding)
        js = json.loads(raw.decode('utf-8'))
        if isinstance(js, dict):
            return js
    except Exception:
        pass
    return None


def _has_pagination_suggestion(ui_suggestions: list, want: str) -> bool:
    want = (want or '').lower()
    for s in (ui_suggestions or []):
        try:
            if s.get('type') == 'Paginacion':
                pag = s.get('pagination') or {}
                direction = (pag.get('direction') or '').lower()
                if direction == want:
                    return True
        except Exception:
            pass
    # fallback textual
    for s in (ui_suggestions or []):
        try:
            text = (s.get('displayText') or s.get('text') or '').lower()
            if want == 'next' and (('siguiente' in text) or ('ver más' in text) or ('ver mas' in text)):
                return True
            if want == 'prev' and ('anterior' in text):
                return True
        except Exception:
            pass
    return False


def test_chat_paginacion_minimo_siguiente_y_anterior():
    access = login_and_get_access(TEST_EMAIL, TEST_PASSWORD)

    mediator_url = MEDIATOR_URL
    assert wait_for_mediator(mediator_url, timeout=90), f"Mediator at {mediator_url} not available"
    url = f"{mediator_url.rstrip('/')}/chat"

    flow_id = str(uuid.uuid4())

    # 1) Primer post: pedir listado de usuarios
    resp1 = send_chat(url, access, flow_id, messages=[{'role': 'user', 'content': 'quiero el listado de usuarios'}])
    env1 = assert_success_envelope(resp1)

    # 2) Extraer token 'next' de ui_suggestions y navegar a Siguiente
    ui1 = _get_ui_suggestions(env1)
    token_next = _pick_pagination_token(ui1, 'next')
    # En primera página no debe existir 'Anterior'
    assert not _has_pagination_suggestion(ui1, 'prev'), "No debería aparecer 'Anterior' en la página 1"
    # Debe existir 'Siguiente' (con o sin token) y, si hay token, validarlo
    assert _has_pagination_suggestion(ui1, 'next'), "Debería existir sugerencia 'Siguiente' en la página 1"
    if token_next:
        tok1 = _decode_context_token(token_next)
        assert tok1 is not None, 'contextToken de Siguiente no es decodificable'
        # Validar target_page/size solo si están presentes
        if 'target_page' in tok1:
            assert int(tok1.get('target_page', 0)) == 2, f"target_page esperado=2, got {tok1}"
        if 'size' in tok1:
            assert int(tok1.get('size', 0)) == 50, f"size esperado=50, got {tok1}"
    # Si no hay token, seguir igualmente sin inyectarlo (el modelo puede deducir page=2). Registrar aviso.
    if token_next:
        nav_to_2 = [
            {'role': 'assistant', 'content': 'Mostrando página 1 de usuarios'},
            {'role': 'assistant', 'content': f'Paginacion_token: {{"token":"{token_next}"}}'},
            {'role': 'user', 'content': 'Siguiente'}
        ]
    else:
        print('[TEST] Aviso: ui_suggestions no incluye contextToken para Siguiente; navegando sin token')
        nav_to_2 = [
            {'role': 'assistant', 'content': 'Mostrando página 1 de usuarios'},
            {'role': 'user', 'content': 'Siguiente'}
        ]
    resp2 = send_chat(url, access, flow_id, messages=nav_to_2)
    env2 = assert_success_envelope(resp2)

    # 3) Extraer token 'prev' y navegar a Anterior (volver a 1)
    ui2 = _get_ui_suggestions(env2)
    token_prev = _pick_pagination_token(ui2, 'prev')
    # En página 2 debe existir 'Anterior'; 'Siguiente' dependerá de hasMore
    assert _has_pagination_suggestion(ui2, 'prev'), "Debería existir sugerencia 'Anterior' en la página 2"
    if token_prev:
        tok2 = _decode_context_token(token_prev)
        assert tok2 is not None, 'contextToken de Anterior no es decodificable'
        if 'target_page' in tok2:
            assert int(tok2.get('target_page', 0)) == 1, f"target_page esperado=1, got {tok2}"
        if 'size' in tok2:
            assert int(tok2.get('size', 0)) == 50, f"size esperado=50, got {tok2}"
    if token_prev:
        back_to_1 = [
            {'role': 'assistant', 'content': 'Mostrando página 2 de usuarios'},
            {'role': 'assistant', 'content': f'Paginacion_token: {{"token":"{token_prev}"}}'},
            {'role': 'user', 'content': 'Anterior'}
        ]
    else:
        print('[TEST] Aviso: ui_suggestions no incluye contextToken para Anterior; navegando sin token')
        back_to_1 = [
            {'role': 'assistant', 'content': 'Mostrando página 2 de usuarios'},
            {'role': 'user', 'content': 'Anterior'}
        ]
    resp3 = send_chat(url, access, flow_id, messages=back_to_1)
    env3 = assert_success_envelope(resp3)

    # Validaciones ligeras: estructura OK y que la paginación tenga sentido
    data2 = env2.get('data') or {}
    data3 = env3.get('data') or {}
    pag2 = data2.get('pagination') or {}
    pag3 = data3.get('pagination') or {}

    if pag2:
        assert str(pag2.get('page')) == '2', f"Se esperaba page=2 tras 'Siguiente', got {pag2}"
    if pag3:
        assert str(pag3.get('page')) == '1', f"Se esperaba page=1 tras 'Anterior', got {pag3}"
    # De vuelta a la página 1: debe existir Siguiente y NO Anterior (con o sin token)
    ui3 = _get_ui_suggestions(env3)
    assert not _has_pagination_suggestion(ui3, 'prev'), "No debería aparecer 'Anterior' tras volver a la página 1"
    assert _has_pagination_suggestion(ui3, 'next'), "Debería aparecer 'Siguiente' tras volver a la página 1"
