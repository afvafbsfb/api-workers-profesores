"""Tests para endpoints de Tarifas - Admin Academia.

Tests de CRUD para tarifas usando usuario admin_academia:
- Login
- Crear tarifa (academia_id se fuerza a la del usuario)
- Consultar tarifas (solo de su academia)
- Modificar tarifa (solo de su academia)
- Intentar acceder a tarifas de otra academia (debe fallar)
- Eliminar tarifa (solo de su academia)
- Logout
"""
import os
os.environ['DB_ENV'] = 'developmentAWS'

import pytest
from app import create_app
from config import Config
import requests
import uuid

BASE_URL = "http://127.0.0.1:5000"


@pytest.fixture
def client():
    Config.set_environment_variables()
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        yield app.test_client()


@pytest.fixture
def ensure_active_academia_for_admin_academia():
    """Ensure the seeded admin_academia user has an active Academia."""
    from src.usuarios.infrastructure.models import Usuario
    from src.academias.infrastructure.models import Academia
    from src.shared.database import db

    user = Usuario.query.filter_by(email='admin_academia@academia.com').first()
    if not user:
        raise RuntimeError('admin_academia user not found in DB seed')

    acad = None
    if user.academia_id:
        acad = db.session.get(Academia, user.academia_id)
        if acad and getattr(acad, 'fecha_baja', None) is not None:
            acad = None

    if not acad:
        a = Academia(nombre=f"Academia_for_admin_academia_{user.id}")
        db.session.add(a)
        db.session.flush()
        user.academia_id = a.id
        db.session.add(user)
        db.session.commit()
        yield a.id
    else:
        yield acad.id


def login_and_get_tokens(email, password):
    login_response = requests.post(f"{BASE_URL}/auth/login", json={'email': email, 'password': password})
    assert login_response.status_code == 200, f"Login failed for {email}: {login_response.json()}"
    data = login_response.json()
    tokens = data.get('tokens') or {}
    return tokens.get('access_token'), tokens.get('refresh_token')


def logout_with_refresh(refresh_token):
    return requests.post(f"{BASE_URL}/auth/logout", headers={'Authorization': f'Bearer {refresh_token}'})


@pytest.mark.meta(title='Admin_academia: CRUD de tarifas en su academia', desc='Crear, listar, modificar y eliminar tarifas limitado a su academia')
def test_admin_academia_crud_tarifas_own_academy(client, ensure_active_academia_for_admin_academia):
    """Test completo del ciclo de vida de una tarifa como admin_academia."""
    
    # 1. LOGIN
    print("\n[TEST] 1. Login como admin_academia")
    access, refresh = login_and_get_tokens('admin_academia@academia.com', 'password_admin_academia')
    headers = {'Authorization': f'Bearer {access}'}
    my_academia_id = ensure_active_academia_for_admin_academia
    print(f"[TEST]    ✓ Login exitoso - Academia vinculada: {my_academia_id}")
    
    # 2. CREAR TARIFA sin especificar academia_id (debe usar la del usuario)
    print("[TEST] 2. Crear tarifa sin especificar academia_id (se fuerza la propia)")
    tarifa_data = {
        'descripcion': 'Tarifa mensual admin_academia',
        'precio_base': 60.0
    }
    rv_create = requests.post(f"{BASE_URL}/tarifas", json=tarifa_data, headers=headers)
    assert rv_create.status_code == 201, f"Error creando tarifa: {rv_create.json()}"
    tarifa_id = rv_create.json()['result']['id']
    tarifa_created = rv_create.json()['result']
    assert tarifa_created['academia_id'] == my_academia_id, "academia_id debe ser la del usuario"
    print(f"[TEST]    ✓ Tarifa creada con ID: {tarifa_id}, academia_id forzada: {tarifa_created['academia_id']}")
    
    # 3. CREAR TARIFA especificando su academia_id (debe funcionar)
    print(f"[TEST] 3. Crear tarifa especificando academia_id={my_academia_id} (válido)")
    tarifa_data2 = {
        'academia_id': my_academia_id,
        'descripcion': 'Tarifa descuento familia',
        'precio_base': 50.0
    }
    rv_create2 = requests.post(f"{BASE_URL}/tarifas", json=tarifa_data2, headers=headers)
    assert rv_create2.status_code == 201
    tarifa_id2 = rv_create2.json()['result']['id']
    print(f"[TEST]    ✓ Segunda tarifa creada con ID: {tarifa_id2}")
    
    # 4. INTENTAR CREAR TARIFA para otra academia (debe fallar)
    print("[TEST] 4. Intentar crear tarifa con academia_id diferente (debe fallar 403)")
    # Crear otra academia como admin_plataforma para probar
    access_platform, _ = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    other_acad = requests.post(
        f"{BASE_URL}/academias",
        json={'nombre': f"Academia_Other_{uuid.uuid4().hex[:8]}"},
        headers={'Authorization': f'Bearer {access_platform}'}
    ).json()['result']['id']
    
    tarifa_other = {
        'academia_id': other_acad,
        'descripcion': 'Tarifa academia ajena',
        'precio_base': 40.0
    }
    rv_create_other = requests.post(f"{BASE_URL}/tarifas", json=tarifa_other, headers=headers)
    assert rv_create_other.status_code == 403, "No debe poder crear tarifa en otra academia"
    print(f"[TEST]    ✓ Creación bloqueada correctamente: 403 Forbidden")
    
    # 5. LISTAR TARIFAS (debe ver solo las de su academia)
    print("[TEST] 5. Listar tarifas (debe ver solo las de su academia)")
    rv_list = requests.get(f"{BASE_URL}/tarifas", headers=headers)
    assert rv_list.status_code == 200
    tarifas = rv_list.json()['result']
    # Todas las tarifas devueltas deben ser de su academia
    for t in tarifas:
        assert t['academia_id'] == my_academia_id, f"Tarifa {t['id']} no es de su academia"
    print(f"[TEST]    ✓ Listado correcto: {len(tarifas)} tarifas de academia {my_academia_id}")
    
    # 6. LISTAR TARIFAS con filtro academia_id propio (debe funcionar)
    print(f"[TEST] 6. Listar con filtro academia_id={my_academia_id} (válido)")
    rv_list_filtered = requests.get(f"{BASE_URL}/tarifas?academia_id={my_academia_id}", headers=headers)
    assert rv_list_filtered.status_code == 200
    print(f"[TEST]    ✓ Filtro aceptado")
    
    # 7. INTENTAR LISTAR con filtro de otra academia (debe fallar 403)
    print(f"[TEST] 7. Intentar listar con academia_id={other_acad} (debe fallar 403)")
    rv_list_other = requests.get(f"{BASE_URL}/tarifas?academia_id={other_acad}", headers=headers)
    assert rv_list_other.status_code == 403, "No debe poder listar tarifas de otra academia"
    print(f"[TEST]    ✓ Acceso bloqueado correctamente: 403 Forbidden")
    
    # 8. OBTENER TARIFA propia (debe funcionar)
    print(f"[TEST] 8. Obtener detalle de tarifa propia ID: {tarifa_id}")
    rv_get = requests.get(f"{BASE_URL}/tarifas/{tarifa_id}", headers=headers)
    assert rv_get.status_code == 200
    tarifa_detail = rv_get.json()['result']
    assert tarifa_detail['id'] == tarifa_id
    print(f"[TEST]    ✓ Tarifa obtenida: {tarifa_detail['descripcion']} - €{tarifa_detail['precio_base']}")
    
    # 9. INTENTAR OBTENER TARIFA de otra academia (crear una primero)
    print("[TEST] 9. Intentar obtener tarifa de otra academia (debe fallar 403)")
    # Crear tarifa en otra academia como admin_plataforma
    tarifa_other_created = requests.post(
        f"{BASE_URL}/tarifas",
        json={'academia_id': other_acad, 'descripcion': 'Tarifa otra academia', 'precio_base': 70},
        headers={'Authorization': f'Bearer {access_platform}'}
    ).json()['result']
    
    rv_get_other = requests.get(f"{BASE_URL}/tarifas/{tarifa_other_created['id']}", headers=headers)
    assert rv_get_other.status_code == 403
    print(f"[TEST]    ✓ Acceso bloqueado: 403 Forbidden")
    
    # 10. MODIFICAR TARIFA propia
    print(f"[TEST] 10. Modificar tarifa propia ID: {tarifa_id}")
    update_data = {
        'descripcion': 'Tarifa mensual MODIFICADA',
        'precio_base': 65.0
    }
    rv_update = requests.patch(f"{BASE_URL}/tarifas/{tarifa_id}", json=update_data, headers=headers)
    assert rv_update.status_code == 200
    tarifa_updated = rv_update.json()['result']
    assert tarifa_updated['descripcion'] == 'Tarifa mensual MODIFICADA'
    assert tarifa_updated['precio_base'] == 65.0
    print(f"[TEST]    ✓ Tarifa modificada: {tarifa_updated['descripcion']} - €{tarifa_updated['precio_base']}")
    
    # 11. INTENTAR MODIFICAR TARIFA de otra academia (debe fallar)
    print(f"[TEST] 11. Intentar modificar tarifa de otra academia (debe fallar 403)")
    rv_update_other = requests.patch(
        f"{BASE_URL}/tarifas/{tarifa_other_created['id']}",
        json={'precio_base': 75},
        headers=headers
    )
    assert rv_update_other.status_code == 403
    print(f"[TEST]    ✓ Modificación bloqueada: 403 Forbidden")
    
    # 12. ELIMINAR TARIFA propia
    print(f"[TEST] 12. Eliminar tarifa propia ID: {tarifa_id2}")
    rv_delete = requests.delete(f"{BASE_URL}/tarifas/{tarifa_id2}", headers=headers)
    assert rv_delete.status_code == 200
    tarifa_deleted = rv_delete.json()['result']
    assert tarifa_deleted['fecha_baja'] is not None
    print(f"[TEST]    ✓ Tarifa eliminada (soft-delete): fecha_baja = {tarifa_deleted['fecha_baja']}")
    
    # 13. INTENTAR ELIMINAR TARIFA de otra academia (debe fallar)
    print(f"[TEST] 13. Intentar eliminar tarifa de otra academia (debe fallar 403)")
    rv_delete_other = requests.delete(f"{BASE_URL}/tarifas/{tarifa_other_created['id']}", headers=headers)
    assert rv_delete_other.status_code == 403
    print(f"[TEST]    ✓ Eliminación bloqueada: 403 Forbidden")
    
    # 14. LIMPIAR: eliminar tarifa restante
    print("[TEST] 14. Limpiar: eliminar tarifa restante")
    requests.delete(f"{BASE_URL}/tarifas/{tarifa_id}", headers=headers)
    
    # Limpiar academia creada para tests
    requests.delete(f"{BASE_URL}/academias/{other_acad}", headers={'Authorization': f'Bearer {access_platform}'})
    requests.delete(f"{BASE_URL}/tarifas/{tarifa_other_created['id']}", headers={'Authorization': f'Bearer {access_platform}'})
    
    # 15. LOGOUT
    print("[TEST] 15. Logout")
    rv_logout = logout_with_refresh(refresh)
    assert rv_logout.status_code == 200
    print("[TEST]    ✓ Logout exitoso")
    
    print("\n[TEST] ✅ TEST COMPLETADO: Admin_academia CRUD tarifas (scope: own_academia)")


@pytest.mark.meta(title='Admin_academia: filtros y ordenación', desc='Verificar filtros funcionan dentro del scope de su academia')
def test_admin_academia_filtros_tarifas(client, ensure_active_academia_for_admin_academia):
    """Test de filtros y ordenación de tarifas como admin_academia."""
    
    print("\n[TEST] Filtros y ordenación de tarifas - admin_academia")
    access, refresh = login_and_get_tokens('admin_academia@academia.com', 'password_admin_academia')
    headers = {'Authorization': f'Bearer {access}'}
    my_academia_id = ensure_active_academia_for_admin_academia
    
    # Crear 3 tarifas con diferentes precios
    print("[TEST] 1. Crear 3 tarifas con diferentes precios")
    tarifas_ids = []
    for i, precio in enumerate([30.0, 50.0, 70.0], 1):
        rv = requests.post(
            f"{BASE_URL}/tarifas",
            json={'descripcion': f'Tarifa {i}', 'precio_base': precio},
            headers=headers
        )
        tarifas_ids.append(rv.json()['result']['id'])
    print(f"[TEST]    ✓ Creadas 3 tarifas: precios 30, 50, 70")
    
    # Filtro precio_base_min
    print("[TEST] 2. Filtrar por precio_base_min=40")
    rv_min = requests.get(f"{BASE_URL}/tarifas?precio_base_min=40", headers=headers)
    assert rv_min.status_code == 200
    tarifas_min = rv_min.json()['result']
    assert all(t['precio_base'] >= 40 for t in tarifas_min)
    print(f"[TEST]    ✓ Filtro correcto: {len([t for t in tarifas_min if t['id'] in tarifas_ids])} tarifas >= 40")
    
    # Filtro precio_base_max
    print("[TEST] 3. Filtrar por precio_base_max=60")
    rv_max = requests.get(f"{BASE_URL}/tarifas?precio_base_max=60", headers=headers)
    assert rv_max.status_code == 200
    tarifas_max = rv_max.json()['result']
    assert all(t['precio_base'] <= 60 for t in tarifas_max)
    print(f"[TEST]    ✓ Filtro correcto: tarifas <= 60")
    
    # Ordenación descendente
    print("[TEST] 4. Ordenar por precio_base descendente")
    rv_order = requests.get(f"{BASE_URL}/tarifas?order_by=precio_base&order_direction=desc", headers=headers)
    assert rv_order.status_code == 200
    tarifas_ordered = rv_order.json()['result']
    my_tarifas = [t for t in tarifas_ordered if t['id'] in tarifas_ids]
    if len(my_tarifas) >= 2:
        assert my_tarifas[0]['precio_base'] >= my_tarifas[1]['precio_base']
    print(f"[TEST]    ✓ Ordenación correcta")
    
    # Limpiar
    print("[TEST] 5. Limpiar tarifas creadas")
    for tid in tarifas_ids:
        requests.delete(f"{BASE_URL}/tarifas/{tid}", headers=headers)
    
    logout_with_refresh(refresh)
    print("\n[TEST] ✅ FILTROS Y ORDENACIÓN COMPLETADOS")
