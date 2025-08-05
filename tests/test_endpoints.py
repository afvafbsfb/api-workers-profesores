import pytest
from app import app

def test_health():
    client = app.test_client()
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.is_json
    data = resp.get_json()
    assert 'ok' in data or 'up' in data

def test_turnos_libres():
    client = app.test_client()
    resp = client.get('/vlodeiro/secretaria/turnos_libres')
    assert resp.status_code == 200
    assert resp.is_json
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert 'plazas_libres' in data[0]

def test_inscribir_and_pago():
    client = app.test_client()
    # Inscribir alumno 3 en turno 1
    resp = client.post('/vlodeiro/secretaria/inscribir', json={"alumno_id": 3, "turno_id": 1})
    assert resp.status_code == 200 or resp.status_code == 400
    # Registrar pago para alumno 3
    resp = client.post('/vlodeiro/secretaria/registrar_pago', json={"alumno_id": 3, "importe": 500, "concepto": "Matricula"})
    assert resp.status_code == 200 or resp.status_code == 400
