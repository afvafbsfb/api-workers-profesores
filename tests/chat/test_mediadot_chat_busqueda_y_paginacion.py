#buscar pytest.mark.parametrize  para comprobar que mensajes se envian al chat

import os
os.environ['DB_ENV'] = 'developmentAWS'

import uuid
import json
import time
import requests
import pytest
import glob
from datetime import datetime

# Configuration at top of file (always set here):
API_WORKER_URL = 'http://127.0.0.1:5000'
MEDIATOR_URL = 'http://localhost:8080'

# Credenciales solicitadas para este test
TEST_EMAIL = 'admin_plataforma@academia.com'
TEST_PASSWORD = 'password_admin_plataforma'


# Ruta local del proyecto backend para localizar el HTML de trazas (si existe)
# Nota: en entornos CI/CD puede no estar disponible; en ese caso, solo se ignora esta parte.
BACKEND_DOC_DIR = r"c:\\Users\\Angel FV\\Desktop\\FORMACION\\chat_backend_academia\\backend-chat-openai-worker-profesores\\documentacion"


def _list_flow_htmls(doc_dir: str):
    try:
        return sorted(glob.glob(os.path.join(doc_dir, 'prueba-*.html')))
    except Exception:
        return []


def _latest_files(before: set, after: set):
    new = list(after - before)
    try:
        new.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    except Exception:
        new.sort(reverse=True)
    return new


def _print_sent_messages(step_number: int, messages):
    try:
        # Imprimir una línea por cada mensaje enviado
        for idx, m in enumerate(messages, start=1):
            role = (m.get('role') if isinstance(m, dict) else getattr(m, 'get', lambda k, d=None: d)('role')) or ''
            content = (m.get('content') if isinstance(m, dict) else getattr(m, 'get', lambda k, d=None: d)('content')) or ''
            print(f"[MENSAJE_{step_number}_ENVIADO] [{idx}] {role}: {content}")
    except Exception as _:
        # No bloquear el test por logs
        pass


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


def extract_ids(items):
    ids = []
    for it in (items or []):
        try:
            if isinstance(it, dict) and 'id' in it:
                ids.append(it['id'])
        except Exception:
            pass
    return ids


def assert_success_envelope(resp):
    assert resp.status_code == 200, f"Mediator /chat returned {resp.status_code}: {resp.text}"
    try:
        env = resp.json()
    except Exception:
        pytest.fail('Mediator did not return JSON envelope')
    assert isinstance(env, dict), 'Envelope debe ser dict'
    assert env.get('status') == 'success', f"status inesperado: {env.get('status')}"
    return env


# Parameterized test cases for each POST (5 en total)
@pytest.mark.parametrize(
    "step_number, messages, expected_description",
    [
        # 1) Bienvenida
        (1, [
            {'role': 'user', 'content': 'hola que tal estas?'}
        ], "Bienvenida"),

        # 2) Listado de usuarios (página 1)
        (2, [
            {'role': 'user', 'content': 'quiero el listado de usuarios'}
        ], "Listado de usuarios (página 1)"),

        # 3) Siguiente página con mini-historial (assistant + contexto + user)
        (3, [
            {'role': 'assistant', 'content': 'Mostrando página 1 de usuarios'},
            # Contexto mínimo requerido por el backend (no incluir campos opcionales para evitar divergencias)
            {'role': 'assistant', 'content': 'Contexto_paginacion: {"type": "usuarios", "page": 1, "size": 20, "next_page": 2}'},
            {'role': 'user', 'content': 'Siguiente'}
        ], "Navegar a página 2 (Siguiente)"),

        # 4) Anterior con mini-historial (assistant + contexto + user)
        (4, [
            {'role': 'assistant', 'content': 'Mostrando página 2 de usuarios'},
            {'role': 'assistant', 'content': 'Contexto_paginacion: {"type": "usuarios", "page": 2, "size": 20, "prev_page": 1}'},
            {'role': 'user', 'content': 'Anterior'}
        ], "Navegar a página 1 (Anterior)"),

        # 5) Cambio de tipo: academias
        (5, [
            {'role': 'user', 'content': 'ahora quiero un listado de academias'}
        ], "Listado de academias"),
    ],
)
def test_chat_busqueda_y_paginacion_steps(step_number, messages, expected_description):
    """
    Test chat busqueda y paginacion steps as independent tests.
    """
    # Snapshot de ficheros HTML antes de iniciar, para identificar el generado por este test
    before_set = set(_list_flow_htmls(BACKEND_DOC_DIR)) if os.path.isdir(BACKEND_DOC_DIR) else set()

    access = login_and_get_access(TEST_EMAIL, TEST_PASSWORD)

    mediator_url = MEDIATOR_URL
    assert wait_for_mediator(mediator_url, timeout=90), f"Mediator at {mediator_url} not available"
    url = f"{mediator_url.rstrip('/')}/chat"

    flow_id = str(uuid.uuid4())

    # Encabezado: 1 sola línea clara por test, en castellano
    try:
        user_msgs = [m.get('content') for m in messages if isinstance(m, dict) and (m.get('role') == 'user')]
        user_prompt = user_msgs[-1] if user_msgs else expected_description
        print(f"TEST {step_number}: POST {user_prompt}")
    except Exception:
        print(f"TEST {step_number}: {expected_description}")

    # Log the messages being sent
    _print_sent_messages(step_number, messages)

    # Send the chat messages
    resp = send_chat(url, access, flow_id, messages=messages)
    env = assert_success_envelope(resp)

    # Validate the response
    if step_number == 1:
        msg = env.get('message') or ''
        print(f"[STEP{step_number}] message=\n{msg}")
    elif step_number == 2:
        data = env.get('data') or {}
        items = data.get('items') or []
        pag = data.get('pagination') or {}
        ids = extract_ids(items)
        print(f"[STEP{step_number}] type={data.get('type')} page={pag.get('page')} size={pag.get('size')} returned={pag.get('returned')} next={pag.get('nextPage')} items_ids_head={ids[:5]}")
        assert isinstance(items, list) and len(items) > 0, 'Listado de usuarios vacío en página 1'
    elif step_number == 3:
        data = env.get('data') or {}
        items = data.get('items') or []
        pag = data.get('pagination') or {}
        ids = extract_ids(items)
        print(f"[STEP{step_number}] type={data.get('type')} page={pag.get('page')} size={pag.get('size')} returned={pag.get('returned')} next={pag.get('nextPage')} prev={pag.get('prevPage')} items_ids_head={ids[:5]}")
        if pag:
            assert pag.get('page') in (2, '2'), f"Se esperaba page=2, got {pag}"
        assert isinstance(items, list), 'items debe ser lista'
    elif step_number == 4:
        data = env.get('data') or {}
        items = data.get('items') or []
        pag = data.get('pagination') or {}
        ids = extract_ids(items)
        print(f"[STEP{step_number}] type={data.get('type')} page={pag.get('page')} size={pag.get('size')} returned={pag.get('returned')} next={pag.get('nextPage')} prev={pag.get('prevPage')} items_ids_head={ids[:5]}")
        if pag:
            assert pag.get('page') in (1, '1'), f"Se esperaba page=1, got {pag}"
        assert isinstance(items, list), 'items debe ser lista'
    elif step_number == 5:
        # Validación ligera: éxito y texto relacionado con academias
        msg = (env.get('message') or '')
        print(f"[STEP{step_number}] message_head={msg[:120]}")
        assert 'academia' in msg.lower() or (env.get('data') or {}).get('type') in (None, 'academias'), 'La respuesta no parece de academias'

    # Tras ejecutar los pasos, intentar localizar el HTML generado con el árbol de decisión
    if os.path.isdir(BACKEND_DOC_DIR):
        # dar un pequeño margen para escritura del fichero
        time.sleep(1)
        after_set = set(_list_flow_htmls(BACKEND_DOC_DIR))
        created = _latest_files(before_set, after_set)
        if created:
            html_path = created[0]
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(html_path)).strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                mtime = 'unknown'
            print(f"[FLOW-HTML] generado: {html_path} (mtime={mtime})")
            # Opcionalmente, inspeccionar marcas de decisión para ayudar a ubicar la rama tomada
            try:
                with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                    txt = f.read()
                took_lite = 'Segundo turno ligero aplicado' in txt
                took_fast = 'Fast-path aplicado' in txt
                took_normal = 'Segunda llamada a OpenAI' in txt and not took_lite and not took_fast
                print(f"[FLOW-DECISION] lite={took_lite} fastpath={took_fast} normal={took_normal}")
            except Exception as ex:
                print(f"[FLOW-HTML] no se pudo leer el archivo para inspección rápida: {ex}")
        else:
            print(f"[FLOW-HTML] No se detectó nuevo HTML en {BACKEND_DOC_DIR}. Asegúrate de enviar cabecera X-Flow-Diagram=true.")
    else:
        print("[FLOW-HTML] Directorio de documentación del backend no encontrado; se omite detección de HTML.")
