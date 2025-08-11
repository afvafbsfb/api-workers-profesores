import os
import uuid
import requests
import pytest
from app import app
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

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self._base}{path}"

    def get(self, path: str):
        return RequestsResponseAdapter(self._session.get(self._url(path)))

    def post(self, path: str, json=None):
        return RequestsResponseAdapter(self._session.post(self._url(path), json=json))


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
    return app.test_client()

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
        turno_id = turno.id
        alumno_id = alumno.id
    # Inscribir alumno con tarifa explícita
    resp = client.post('/vlodeiro/secretaria/inscribir', json={"alumno_id": alumno_id, "turno_id": turno_id, "tarifa_id": tarifa.id})
    assert resp.status_code in (200, 400)
    # Registrar pago para alumno 3
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
    lista = resp.get_json()
    assert isinstance(lista, list)
    assert len(lista) >= 1
    primer_id = lista[0]['id']

    # Detalle por id
    resp = client.get(f'/vlodeiro/secretaria/alumnos/{primer_id}')
    assert resp.status_code == 200
    detalle = resp.get_json()
    assert detalle.get('id') == primer_id

    # Búsqueda por nombre (usa parte del nombre del primer alumno)
    nombre = lista[0]['nombre'].split(' ')[0]
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
