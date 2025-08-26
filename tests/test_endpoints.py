# =====================
# TESTS DE SEGURIDAD Y AUTENTICACIÓN
# =====================
def test_auth_sin_api_key(client):
    # Quitar la cabecera X-Api-Key manualmente
    resp = client.get('/vlodeiro/secretaria/alumnos', headers={})
    assert resp.status_code == 401

def test_auth_api_key_incorrecta(client):
    resp = client.get('/vlodeiro/secretaria/alumnos', headers={"X-Api-Key": "incorrecta"})
    assert resp.status_code == 401

# =====================
# TESTS DE ERRORES Y VALIDACIÓN
# =====================
def test_alumnos_detalle_id_inexistente(client):
    resp = client.get('/vlodeiro/secretaria/alumnos/999999')
    assert resp.status_code in (404, 400)

def test_inscribir_datos_incompletos(client):
    resp = client.post('/vlodeiro/secretaria/inscribir', json={})
    assert resp.status_code == 400

def test_inscribir_ids_invalidos(client):
    resp = client.post('/vlodeiro/secretaria/inscribir', json={"alumno_id": 999999, "turno_id": 999999, "tarifa_id": 999999})
    assert resp.status_code in (400, 404)

def test_registrar_pago_sin_inscripcion_activa(client):
    # Buscar un alumno sin inscripción activa (id alto)
    resp = client.post('/vlodeiro/secretaria/registrar_pago', json={"alumno_id": 999999, "importe": 100, "concepto": "Test"})
    assert resp.status_code in (400, 404, 500)

def test_tarifa_delete_id_inexistente(client):
    resp = client.delete('/vlodeiro/secretaria/tarifas/999999')
    assert resp.status_code in (404, 400)

def test_empresa_get_id_inexistente(client):
    resp = client.get('/vlodeiro/empresa/empresa/999999')
    assert resp.status_code in (404, 400)

def test_empresa_post_nombre_vacio(client):
    resp = client.post('/vlodeiro/empresa/empresa', json={"nombre": ""})
    assert resp.status_code == 400

# =====================
# TESTS DE LÍMITES Y EDGE CASES
# =====================
def test_alumnos_paginacion_size_cero(client):
    resp = client.get('/vlodeiro/secretaria/alumnos?page=0&size=0')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert 'list' in data and isinstance(data['list'], list)

def test_alumnos_paginacion_size_grande(client):
    resp = client.get('/vlodeiro/secretaria/alumnos?page=0&size=1000')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert 'list' in data and isinstance(data['list'], list)

def test_alumnos_paginacion_page_negativa(client):
    resp = client.get('/vlodeiro/secretaria/alumnos?page=-1&size=2')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert 'list' in data and isinstance(data['list'], list)

def test_alumnos_buscar_no_existe(client):
    resp = client.get('/vlodeiro/secretaria/alumnos/buscar?nombre=NOEXISTE123456')
    assert resp.status_code == 200
    resultados = resp.get_json()
    assert isinstance(resultados, list)
    assert len(resultados) == 0

def test_turnos_alumnos_sin_alumnos(client):
    # Buscar un turno sin alumnos (id alto)
    resp = client.get('/vlodeiro/secretaria/turnos/999999/alumnos')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)

# =====================
# TESTS DE EFECTOS SECUNDARIOS
# =====================
def test_tarifa_crud_side_effects(client):
    # Crear tarifa
    from main import app
    with app.app_context():
        from models import Empresa, Tarifa, db
        empresa = Empresa.query.first()
        assert empresa is not None
        resp = client.post('/vlodeiro/secretaria/tarifas', json={
            "empresa_id": empresa.id,
            "descripcion": "Tarifa SideEffect",
            "duracion_min": 60,
            "precio_base": 99.0
        })
        assert resp.status_code in (201, 400)
        # Comprobar que aparece en el listado
        resp_list = client.get('/vlodeiro/secretaria/tarifas')
        assert resp_list.status_code == 200
        tarifas = resp_list.get_json()
        assert any(t.get('descripcion') == "Tarifa SideEffect" for t in tarifas)

# =====================
# TESTS DE IDEMPOTENCIA Y REPETICIÓN
# =====================
def test_inscribir_dos_veces_mismo_alumno(client):
    from main import app
    with app.app_context():
        from models import Alumno, Turno, Tarifa, db
        alumno = Alumno.query.first()
        turno = Turno.query.first()
        tarifa = Tarifa.query.first()
        assert alumno and turno and tarifa
        # Primera inscripción
        resp1 = client.post('/vlodeiro/secretaria/inscribir', json={"alumno_id": alumno.id, "turno_id": turno.id, "tarifa_id": tarifa.id})
        # Segunda inscripción (debe fallar o devolver 400)
        resp2 = client.post('/vlodeiro/secretaria/inscribir', json={"alumno_id": alumno.id, "turno_id": turno.id, "tarifa_id": tarifa.id})
        assert resp2.status_code in (400, 409)

def test_baja_inscripcion_ya_baja(client):
    from main import app
    with app.app_context():
        from models import Alumno, Turno, Tarifa, Inscripcion, db
        alumno = Alumno.query.first()
        turno = Turno.query.first()
        tarifa = Tarifa.query.first()
        assert alumno and turno and tarifa
        # Asegurar inscripción activa
        ins = Inscripcion.query.filter_by(alumno_id=alumno.id, turno_id=turno.id, fecha_fin=None).first()
        if not ins:
            ins = Inscripcion(alumno_id=alumno.id, turno_id=turno.id, tarifa_id=tarifa.id, fecha_inicio=__import__('datetime').date.today())
            db.session.add(ins)
            db.session.commit()
        # Dar de baja
        resp1 = client.post(f'/vlodeiro/secretaria/inscripciones/{ins.id}/baja')
        # Segunda baja (debe fallar o devolver 400)
        resp2 = client.post(f'/vlodeiro/secretaria/inscripciones/{ins.id}/baja')
        assert resp2.status_code in (400, 409)
import os
API_KEY = os.getenv("API_KEY", "devkey")
# -----------------------------------------------------------------------------
# PROPÓSITO DE ESTE SCRIPT
#
# Este archivo contiene pruebas automáticas de integración y lógica de negocio
# para la API REST (CRUD, flujos, validaciones, etc). Está pensado para:
#   - Validar la lógica de negocio y la integridad de la API en local (SQLite)
#   - Validar la API en entornos de integración o producción (MySQL, remota)
#
# Usa pytest y puede manipular la base de datos local (si no usas USE_LIVE=1).
#
# Cuándo usarlo:
#   - Antes de hacer un despliegue, para asegurar que la lógica y los flujos funcionan.
#   - En desarrollo, para pruebas rápidas y cobertura de cambios en la lógica.
#   - En CI/CD, para validación automática.
#
# No valida la documentación OpenAPI ni la conectividad de todos los endpoints declarados.
# Para eso, usa tests_get_endpoints.py
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE ENTORNOS PARA PRUEBAS AUTOMÁTICAS
#
# Este fichero de tests funciona igual para:
#   - SQLite local (por defecto)
#   - MySQL local/remoto
#   - Producción (API remota)
#
# Por defecto, los tests usan la API local y la base de datos configurada en tu entorno.
#
# Para apuntar a una API remota (por ejemplo, producción o MySQL en servidor):
#   - En PowerShell:
#       $env:USE_LIVE=1; $env:BASE_URL="https://tu-api-remota.com"; pytest
#   - En Linux/macOS:
#       USE_LIVE=1 BASE_URL="https://tu-api-remota.com" pytest
#
# Si USE_LIVE=1, los tests usan peticiones HTTP reales y no manipulan la base de datos local.
# Si USE_LIVE no está definido, los tests usan el cliente Flask y la base de datos local (SQLite o la que tengas configurada).
# -----------------------------------------------------------------------------

def test_alumnos_paginacion_primera_pagina(client):
    page_size = 2
    resp = client.get(f'/vlodeiro/secretaria/alumnos?page=0&size={page_size}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert 'list' in data and isinstance(data['list'], list)
    assert data['page'] == 0
    assert data['size'] == page_size
    assert len(data['list']) <= page_size
    assert data.get('hasMore') is not None

def test_alumnos_paginacion_segunda_pagina(client):
    page_size = 2
    resp = client.get(f'/vlodeiro/secretaria/alumnos?page=1&size={page_size}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert 'list' in data and isinstance(data['list'], list)
    assert data['page'] == 1
    assert data['size'] == page_size
    assert len(data['list']) <= page_size
    assert data.get('hasMore') is not None

def test_alumnos_paginacion_ultima_pagina(client):
    page_size = 2
    # Obtener el total de alumnos
    resp_all = client.get('/vlodeiro/secretaria/alumnos')
    assert resp_all.status_code == 200
    data_all = resp_all.get_json()
    total = data_all.get('total', len(data_all.get('list', [])))
    last_page = (total // page_size)
    resp = client.get(f'/vlodeiro/secretaria/alumnos?page={last_page}&size={page_size}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert 'list' in data and isinstance(data['list'], list)
    assert data['page'] == last_page
    assert data['size'] == page_size
    assert data.get('hasMore') is not None
    if len(data['list']) < page_size or (last_page+1)*page_size >= total:
        assert data['hasMore'] is False

def test_alumnos_paginacion_pagina_vacia(client):
    page_size = 2
    resp = client.get(f'/vlodeiro/secretaria/alumnos?page=9999&size={page_size}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert 'list' in data and isinstance(data['list'], list)
    assert len(data['list']) == 0
    assert data.get('hasMore') is False

def test_alumnos_paginacion_tamano_personalizado(client):
    custom_size = 3
    resp = client.get(f'/vlodeiro/secretaria/alumnos?page=0&size={custom_size}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert 'list' in data and isinstance(data['list'], list)
    assert data['size'] == custom_size
    assert len(data['list']) <= custom_size
import os
import uuid
import requests
import pytest
from main import app
from models import db, Empresa, Turno, Alumno, Tarifa, Inscripcion

USE_LIVE = os.getenv("USE_LIVE") == "1"
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000").rstrip("/")


class RequestsResponseAdapter:
    def __init__(self, resp: requests.Response):
        self._resp = resp

    @property
    def status_code(self):
        return self._resp.status_code

    @property
    def is_json(self):
        ctype = self._resp.headers.get("Content-Type", "")
        if "json" in ctype:
            return True
        try:
            self._resp.json()
            return True
        except Exception:
            return False

    def get_json(self):
        try:
            return self._resp.json()
        except Exception:
            return None


class RequestsClient:
    def __init__(self, base_url: str):
        self._base = base_url.rstrip("/")
        self._session = requests.Session()
        self._headers = {"X-Api-Key": API_KEY}

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self._base}{path}"

    def get(self, path: str):
        return RequestsResponseAdapter(self._session.get(self._url(path), headers=self._headers))

    def post(self, path: str, json=None):
        return RequestsResponseAdapter(self._session.post(self._url(path), json=json, headers=self._headers))


@pytest.fixture(autouse=True, scope="module")
def ensure_db_seed():
    """Asegura tablas y datos mínimos en modo in-app; no aplica en modo live."""
    if USE_LIVE:
        # En modo live no tocamos la BD directamente
        yield
        return
    with app.app_context():
        db.create_all()
        empresa = Empresa.query.first()
        if not empresa:
            empresa = Empresa(nombre="Empresa Seed")
            db.session.add(empresa)
            db.session.commit()

        if Tarifa.query.count() == 0:
            t = Tarifa(empresa_id=empresa.id, descripcion="seed", duracion_min=60, precio_base=10.0)
            db.session.add(t)
            db.session.commit()

        if Turno.query.count() == 0:
            turnos = [
                Turno(empresa_id=empresa.id, tipo_alumno="adulto", dia_semana="lunes", hora_inicio="19:30", hora_fin="21:30", duracion_min=120, capacidad=15, activo=True),
                Turno(empresa_id=empresa.id, tipo_alumno="niño", dia_semana="martes", hora_inicio="17:30", hora_fin="19:00", duracion_min=90, capacidad=20, activo=True),
            ]
            db.session.add_all(turnos)
            db.session.commit()

        if Alumno.query.count() == 0:
            alumnos = [Alumno(nombre=f"Alumno {i}", email=f"alumno{i}@example.com") for i in range(1, 6)]
            db.session.add_all(alumnos)
            db.session.commit()
    yield


@pytest.fixture(scope="module")
def client():
    if USE_LIVE:
        return RequestsClient(BASE_URL)
    # Flask test client: añade la cabecera X-Api-Key a cada petición
    test_client = app.test_client()
    class AuthClient:
        def get(self, path, **kwargs):
            headers = kwargs.pop("headers", None)
            if headers is None:
                headers = {"X-Api-Key": API_KEY}
            elif headers == {}:
                # No añadir cabecera si el usuario pasa headers vacíos
                pass
            elif "X-Api-Key" not in headers:
                headers = dict(headers)
                headers["X-Api-Key"] = API_KEY
            return test_client.get(path, headers=headers, **kwargs)
        def post(self, path, **kwargs):
            headers = kwargs.pop("headers", None)
            if headers is None:
                headers = {"X-Api-Key": API_KEY}
            elif headers == {}:
                pass
            elif "X-Api-Key" not in headers:
                headers = dict(headers)
                headers["X-Api-Key"] = API_KEY
            return test_client.post(path, headers=headers, **kwargs)
        def put(self, path, **kwargs):
            headers = kwargs.pop("headers", None)
            if headers is None:
                headers = {"X-Api-Key": API_KEY}
            elif headers == {}:
                pass
            elif "X-Api-Key" not in headers:
                headers = dict(headers)
                headers["X-Api-Key"] = API_KEY
            return test_client.put(path, headers=headers, **kwargs)
        def delete(self, path, **kwargs):
            headers = kwargs.pop("headers", None)
            if headers is None:
                headers = {"X-Api-Key": API_KEY}
            elif headers == {}:
                pass
            elif "X-Api-Key" not in headers:
                headers = dict(headers)
                headers["X-Api-Key"] = API_KEY
            return test_client.delete(path, headers=headers, **kwargs)
    return AuthClient()

def test_health(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    assert getattr(resp, 'is_json', True)
    data = resp.get_json()
    assert 'ok' in data or 'up' in data

def test_turnos_libres(client):
    resp = client.get('/vlodeiro/secretaria/turnos_libres')
    assert resp.status_code == 200
    assert getattr(resp, 'is_json', True)
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert 'plazas_libres' in data[0]

def test_inscribir_and_pago(client):
    # Obtener ids para prueba
    with app.app_context():
        tarifa = Tarifa.query.filter_by(activo=True).first()
        assert tarifa is not None
        turno = Turno.query.first()
        alumno = Alumno.query.first()
        assert turno is not None and alumno is not None
        tarifa_id = tarifa.id
        turno_id = turno.id
        alumno_id = alumno.id
        # Asegurar inscripción activa
        from models import Inscripcion, db
        ins = Inscripcion.query.filter_by(alumno_id=alumno_id, turno_id=turno_id, fecha_fin=None).first()
        if not ins:
            ins = Inscripcion(alumno_id=alumno_id, turno_id=turno_id, tarifa_id=tarifa_id, fecha_inicio=__import__('datetime').date.today())
            db.session.add(ins)
            db.session.commit()
    # Inscribir alumno con tarifa explícita (puede devolver 400 si ya está inscrito)
    resp = client.post('/vlodeiro/secretaria/inscribir', json={"alumno_id": alumno_id, "turno_id": turno_id, "tarifa_id": tarifa_id})
    assert resp.status_code in (200, 400)
    # Registrar pago para alumno con inscripción activa
    resp = client.post('/vlodeiro/secretaria/registrar_pago', json={"alumno_id": alumno_id, "importe": 500, "concepto": "Matricula"})
    assert resp.status_code == 200 or resp.status_code == 400


def test_empresa_endpoints_crud(client):

    # 400 al crear sin nombre
    resp = client.post('/vlodeiro/empresa/empresa', json={})
    assert resp.status_code == 400

    # Crear empresa OK
    nombre = f"Empresa PyTest {uuid.uuid4().hex[:6]}"
    resp = client.post('/vlodeiro/empresa/empresa', json={"nombre": nombre, "descripcion": "demo"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert 'id' in data and 'nombre' in data
    empresa_id = data['id']

    # Obtener empresa por id
    resp = client.get(f'/vlodeiro/empresa/empresa/{empresa_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('id') == empresa_id

    # Listado incluye la empresa
    resp = client.get('/vlodeiro/empresa/empresa')
    assert resp.status_code == 200
    lista = resp.get_json()
    assert any(e.get('id') == empresa_id for e in lista)


def test_alumnos_listado_y_consulta(client):
    # Listado
    resp = client.get('/vlodeiro/secretaria/alumnos')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert 'list' in data and isinstance(data['list'], list)
    assert len(data['list']) >= 1
    primer_id = data['list'][0]['id']

    # Detalle por id
    resp = client.get(f'/vlodeiro/secretaria/alumnos/{primer_id}')
    assert resp.status_code == 200
    detalle = resp.get_json()
    assert detalle.get('id') == primer_id

    # Búsqueda por nombre (usa parte del nombre del primer alumno)
    nombre = data['list'][0]['nombre'].split(' ')[0]
    resp = client.get(f'/vlodeiro/secretaria/alumnos/buscar?nombre={nombre}')
    assert resp.status_code == 200
    resultados = resp.get_json()
    assert isinstance(resultados, list)


def test_tarifas_crud_y_inscritos_y_baja(client):
    # Crear tarifa
    with app.app_context():
        empresa = Empresa.query.first()
        assert empresa is not None
        empresa_id = empresa.id
    resp = client.post('/vlodeiro/secretaria/tarifas', json={
        "empresa_id": empresa_id,
        "descripcion": "Tarifa Test",
        "duracion_min": 60,
        "precio_base": 25.0
    })
    assert resp.status_code in (201, 400)
    # Listar tarifas
    resp = client.get('/vlodeiro/secretaria/tarifas')
    assert resp.status_code == 200
    tarifas = resp.get_json()
    assert isinstance(tarifas, list)
    if tarifas:
        tid = tarifas[0].get('id')
        # Actualizar tarifa
        resp = client.put(f'/vlodeiro/secretaria/tarifas/{tid}', json={"descuento": 5})
        assert resp.status_code in (200, 404)
    # Alumnos inscritos en un turno
    with app.app_context():
        turno = Turno.query.first()
        alumno = Alumno.query.first()
        tarifa = Tarifa.query.first()
        assert turno and alumno and tarifa
        # Asegurar una inscripción para poder probar la baja
        ins = Inscripcion.query.filter_by(alumno_id=alumno.id, turno_id=turno.id, fecha_fin=None).first()
        if not ins:
            ins = Inscripcion(alumno_id=alumno.id, turno_id=turno.id, tarifa_id=tarifa.id, fecha_inicio=__import__('datetime').date.today())
            db.session.add(ins)
            db.session.commit()
        ins_id = ins.id
        turno_id = turno.id
    resp = client.get(f'/vlodeiro/secretaria/turnos/{turno_id}/alumnos')
    assert resp.status_code == 200
    lst = resp.get_json()
    assert isinstance(lst, list)
    # Dar de baja inscripción
    resp = client.post(f'/vlodeiro/secretaria/inscripciones/{ins_id}/baja')
    assert resp.status_code in (200, 404)
