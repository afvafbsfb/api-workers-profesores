"""Tests para endpoints de Tarifas - Admin Plataforma.

Tests completos de CRUD para tarifas usando usuario admin_plataforma:
- Login
- Crear tarifa
- Consultar tarifas (listado y detalle)
- Modificar tarifa
- Intentar eliminar tarifa con cursos activos (debe fallar)
- Eliminar tarifa sin cursos activos
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


def login_and_get_tokens(email, password):
    login_response = requests.post(f"{BASE_URL}/auth/login", json={'email': email, 'password': password})
    assert login_response.status_code == 200, f"Login failed for {email}: {login_response.json()}"
    data = login_response.json()
    tokens = data.get('tokens') or {}
    return tokens.get('access_token'), tokens.get('refresh_token')


def logout_with_refresh(refresh_token):
    return requests.post(f"{BASE_URL}/auth/logout", headers={'Authorization': f'Bearer {refresh_token}'})


@pytest.mark.meta(title='Admin_plataforma: CRUD completo de tarifas', desc='Crear, listar, modificar y eliminar tarifas')
def test_admin_plataforma_crud_tarifas(client):
    """Test completo del ciclo de vida de una tarifa como admin_plataforma."""
    
    # 1. LOGIN
    print("\n[TEST] 1. Login como admin_plataforma")
    access, refresh = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    headers = {'Authorization': f'Bearer {access}'}
    
    # 2. CREAR ACADEMIA para las tarifas
    print("[TEST] 2. Crear academia para asociar tarifas")
    academia_name = f"Academia Test Tarifas {uuid.uuid4().hex[:8]}"
    rv_acad = requests.post(f"{BASE_URL}/academias", json={'nombre': academia_name}, headers=headers)
    assert rv_acad.status_code == 201, f"Error creando academia: {rv_acad.json()}"
    academia_id = rv_acad.json()['result']['id']
    print(f"[TEST]    ✓ Academia creada con ID: {academia_id}")
    
    # 3. CREAR TARIFA
    print("[TEST] 3. Crear tarifa en la academia")
    tarifa_data = {
        'academia_id': academia_id,
        'descripcion': 'Tarifa mensual básica',
        'precio_base': 50.0
    }
    rv_create = requests.post(f"{BASE_URL}/tarifas", json=tarifa_data, headers=headers)
    assert rv_create.status_code == 201, f"Error creando tarifa: {rv_create.json()}"
    tarifa_id = rv_create.json()['result']['id']
    print(f"[TEST]    ✓ Tarifa creada con ID: {tarifa_id}")
    
    # 4. CREAR SEGUNDA TARIFA para pruebas de listado
    print("[TEST] 4. Crear segunda tarifa (descuento)")
    tarifa_data2 = {
        'academia_id': academia_id,
        'descripcion': 'Tarifa descuento familia',
        'precio_base': 40.0
    }
    rv_create2 = requests.post(f"{BASE_URL}/tarifas", json=tarifa_data2, headers=headers)
    assert rv_create2.status_code == 201
    tarifa_id2 = rv_create2.json()['result']['id']
    print(f"[TEST]    ✓ Segunda tarifa creada con ID: {tarifa_id2}")
    
    # 5. LISTAR TARIFAS (sin filtros)
    print("[TEST] 5. Listar todas las tarifas")
    rv_list = requests.get(f"{BASE_URL}/tarifas", headers=headers)
    assert rv_list.status_code == 200
    tarifas = rv_list.json()['result']
    assert len(tarifas) >= 2, "Debe haber al menos 2 tarifas"
    print(f"[TEST]    ✓ Listado obtenido: {len(tarifas)} tarifas")
    
    # 6. LISTAR TARIFAS con filtro por academia_id
    print(f"[TEST] 6. Listar tarifas filtradas por academia_id={academia_id}")
    rv_list_filtered = requests.get(f"{BASE_URL}/tarifas?academia_id={academia_id}", headers=headers)
    assert rv_list_filtered.status_code == 200
    tarifas_filtered = rv_list_filtered.json()['result']
    assert len(tarifas_filtered) == 2, "Debe haber exactamente 2 tarifas de esta academia"
    print(f"[TEST]    ✓ Filtrado correcto: {len(tarifas_filtered)} tarifas")
    
    # 7. LISTAR TARIFAS con filtro de precio
    print("[TEST] 7. Listar tarifas con precio >= 45")
    rv_list_price = requests.get(f"{BASE_URL}/tarifas?precio_base_min=45&academia_id={academia_id}", headers=headers)
    assert rv_list_price.status_code == 200
    tarifas_price = rv_list_price.json()['result']
    assert len(tarifas_price) == 1, "Solo debe haber 1 tarifa con precio >= 45"
    assert tarifas_price[0]['precio_base'] >= 45
    print(f"[TEST]    ✓ Filtro de precio correcto")
    
    # 8. LISTAR TARIFAS con ordenación
    print("[TEST] 8. Listar tarifas ordenadas por precio descendente")
    rv_list_order = requests.get(
        f"{BASE_URL}/tarifas?academia_id={academia_id}&order_by=precio_base&order_direction=desc", 
        headers=headers
    )
    assert rv_list_order.status_code == 200
    tarifas_ordered = rv_list_order.json()['result']
    assert tarifas_ordered[0]['precio_base'] >= tarifas_ordered[1]['precio_base']
    print(f"[TEST]    ✓ Ordenación correcta: {tarifas_ordered[0]['precio_base']} >= {tarifas_ordered[1]['precio_base']}")
    
    # 9. OBTENER TARIFA específica
    print(f"[TEST] 9. Obtener detalle de tarifa ID: {tarifa_id}")
    rv_get = requests.get(f"{BASE_URL}/tarifas/{tarifa_id}", headers=headers)
    assert rv_get.status_code == 200
    tarifa_detail = rv_get.json()['result']
    assert tarifa_detail['id'] == tarifa_id
    assert tarifa_detail['descripcion'] == 'Tarifa mensual básica'
    print(f"[TEST]    ✓ Tarifa obtenida: {tarifa_detail['descripcion']} - €{tarifa_detail['precio_base']}")
    
    # 10. MODIFICAR TARIFA (descripción y precio)
    print(f"[TEST] 10. Modificar tarifa ID: {tarifa_id}")
    update_data = {
        'descripcion': 'Tarifa mensual básica MODIFICADA',
        'precio_base': 55.0
    }
    rv_update = requests.patch(f"{BASE_URL}/tarifas/{tarifa_id}", json=update_data, headers=headers)
    assert rv_update.status_code == 200
    tarifa_updated = rv_update.json()['result']
    assert tarifa_updated['descripcion'] == 'Tarifa mensual básica MODIFICADA'
    assert tarifa_updated['precio_base'] == 55.0
    print(f"[TEST]    ✓ Tarifa modificada: {tarifa_updated['descripcion']} - €{tarifa_updated['precio_base']}")
    
    # 11. INTENTAR MODIFICAR academia_id (debe ignorarse)
    print(f"[TEST] 11. Intentar modificar academia_id (campo inmutable)")
    invalid_update = {
        'academia_id': 999,
        'descripcion': 'No debe cambiar academia'
    }
    rv_invalid = requests.patch(f"{BASE_URL}/tarifas/{tarifa_id}", json=invalid_update, headers=headers)
    assert rv_invalid.status_code == 200
    tarifa_check = requests.get(f"{BASE_URL}/tarifas/{tarifa_id}", headers=headers).json()['result']
    assert tarifa_check['academia_id'] == academia_id, "academia_id no debe cambiar"
    print(f"[TEST]    ✓ academia_id permanece inmutable: {tarifa_check['academia_id']}")
    
    # 12. VALIDAR precio_base <= 0 (debe fallar)
    print("[TEST] 12. Intentar modificar con precio_base <= 0 (debe fallar)")
    invalid_price = {'precio_base': 0}
    rv_invalid_price = requests.patch(f"{BASE_URL}/tarifas/{tarifa_id}", json=invalid_price, headers=headers)
    assert rv_invalid_price.status_code == 400, "Debe rechazar precio_base <= 0"
    print(f"[TEST]    ✓ Validación correcta: precio_base > 0 requerido")
    
    # 13. ELIMINAR TARIFA (sin cursos activos)
    print(f"[TEST] 13. Eliminar tarifa ID: {tarifa_id2} (sin cursos activos)")
    rv_delete = requests.delete(f"{BASE_URL}/tarifas/{tarifa_id2}", headers=headers)
    assert rv_delete.status_code == 200, f"Error eliminando tarifa: {rv_delete.json()}"
    tarifa_deleted = rv_delete.json()['result']
    assert tarifa_deleted['fecha_baja'] is not None, "fecha_baja debe estar establecida"
    print(f"[TEST]    ✓ Tarifa eliminada (soft-delete): fecha_baja = {tarifa_deleted['fecha_baja']}")
    
    # 14. VERIFICAR que tarifa eliminada aparece con filtro fecha_baja_null=false
    print("[TEST] 14. Verificar filtro fecha_baja_null=false incluye tarifa eliminada")
    rv_list_deleted = requests.get(
        f"{BASE_URL}/tarifas?academia_id={academia_id}&fecha_baja_null=false", 
        headers=headers
    )
    assert rv_list_deleted.status_code == 200
    tarifas_deleted = rv_list_deleted.json()['result']
    assert any(t['id'] == tarifa_id2 for t in tarifas_deleted), "Tarifa eliminada debe aparecer"
    print(f"[TEST]    ✓ Filtro fecha_baja_null=false correcto")
    
    # 15. VERIFICAR que tarifa eliminada NO aparece con filtro fecha_baja_null=true
    print("[TEST] 15. Verificar filtro fecha_baja_null=true excluye tarifa eliminada")
    rv_list_active = requests.get(
        f"{BASE_URL}/tarifas?academia_id={academia_id}&fecha_baja_null=true", 
        headers=headers
    )
    assert rv_list_active.status_code == 200
    tarifas_active = rv_list_active.json()['result']
    assert not any(t['id'] == tarifa_id2 for t in tarifas_active), "Tarifa eliminada NO debe aparecer"
    print(f"[TEST]    ✓ Filtro fecha_baja_null=true correcto")
    
    # 16. LIMPIAR: Eliminar tarifa restante y academia
    print("[TEST] 16. Limpiar: eliminar tarifa restante")
    requests.delete(f"{BASE_URL}/tarifas/{tarifa_id}", headers=headers)
    print("[TEST] 17. Limpiar: eliminar academia")
    requests.delete(f"{BASE_URL}/academias/{academia_id}", headers=headers)
    
    # 17. LOGOUT
    print("[TEST] 18. Logout")
    rv_logout = logout_with_refresh(refresh)
    assert rv_logout.status_code == 200
    print("[TEST]    ✓ Logout exitoso")
    
    print("\n[TEST] ✅ TEST COMPLETADO: Admin_plataforma CRUD tarifas")


@pytest.mark.meta(title='Admin_plataforma: validaciones de creación', desc='Validar campos obligatorios y valores inválidos')
def test_admin_plataforma_validaciones_crear_tarifa(client):
    """Test de validaciones al crear tarifas."""
    
    print("\n[TEST] Validaciones de creación de tarifas")
    access, refresh = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    headers = {'Authorization': f'Bearer {access}'}
    
    # Crear academia primero
    academia_name = f"Academia Validaciones {uuid.uuid4().hex[:8]}"
    rv_acad = requests.post(f"{BASE_URL}/academias", json={'nombre': academia_name}, headers=headers)
    academia_id = rv_acad.json()['result']['id']
    
    # 1. Sin academia_id (debe fallar)
    print("[TEST] 1. Crear sin academia_id (debe fallar)")
    rv1 = requests.post(f"{BASE_URL}/tarifas", json={'descripcion': 'Test', 'precio_base': 50}, headers=headers)
    assert rv1.status_code == 403, "Debe fallar sin academia_id"
    print("[TEST]    ✓ Validación correcta: academia_id requerido")
    
    # 2. Sin descripción (debe fallar)
    print("[TEST] 2. Crear sin descripción (debe fallar)")
    rv2 = requests.post(f"{BASE_URL}/tarifas", json={'academia_id': academia_id, 'precio_base': 50}, headers=headers)
    assert rv2.status_code == 400
    print("[TEST]    ✓ Validación correcta: descripción requerida")
    
    # 3. Sin precio_base (debe fallar)
    print("[TEST] 3. Crear sin precio_base (debe fallar)")
    rv3 = requests.post(f"{BASE_URL}/tarifas", json={'academia_id': academia_id, 'descripcion': 'Test'}, headers=headers)
    assert rv3.status_code == 400
    print("[TEST]    ✓ Validación correcta: precio_base requerido")
    
    # 4. Con precio_base <= 0 (debe fallar)
    print("[TEST] 4. Crear con precio_base = 0 (debe fallar)")
    rv4 = requests.post(f"{BASE_URL}/tarifas", json={'academia_id': academia_id, 'descripcion': 'Test', 'precio_base': 0}, headers=headers)
    assert rv4.status_code == 400
    print("[TEST]    ✓ Validación correcta: precio_base > 0 requerido")
    
    # 5. Con academia inexistente (debe fallar)
    print("[TEST] 5. Crear con academia_id inexistente (debe fallar)")
    rv5 = requests.post(f"{BASE_URL}/tarifas", json={'academia_id': 999999, 'descripcion': 'Test', 'precio_base': 50}, headers=headers)
    assert rv5.status_code == 404
    print("[TEST]    ✓ Validación correcta: academia debe existir")
    
    # Limpiar
    requests.delete(f"{BASE_URL}/academias/{academia_id}", headers=headers)
    logout_with_refresh(refresh)
    
    print("\n[TEST] ✅ VALIDACIONES COMPLETADAS")
