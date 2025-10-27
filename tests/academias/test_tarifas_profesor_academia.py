"""Tests para endpoints de Tarifas - Profesor Academia.

Tests verificando que profesor_academia NO tiene acceso a ningún endpoint de tarifas:
- Login
- Intentar listar tarifas (debe fallar 403)
- Intentar crear tarifa (debe fallar 403)
- Intentar obtener tarifa (debe fallar 403)
- Intentar modificar tarifa (debe fallar 403)
- Intentar eliminar tarifa (debe fallar 403)
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


@pytest.mark.meta(title='Profesor_academia: sin acceso a tarifas', desc='Verificar que profesor_academia no puede acceder a endpoints de tarifas')
def test_profesor_academia_no_access_tarifas(client):
    """Test verificando que profesor_academia no tiene ningún permiso sobre tarifas."""
    
    # 1. LOGIN
    print("\n[TEST] 1. Login como profesor_academia")
    access, refresh = login_and_get_tokens('reserve_user_academia_1_1@academia.com', 'password_reserve_user_academia_1_1')
    headers = {'Authorization': f'Bearer {access}'}
    print("[TEST]    ✓ Login exitoso como profesor_academia")
    
    # Obtener información del usuario (academia_id)
    rv_me = requests.get(f"{BASE_URL}/usuarios/me", headers=headers)
    user_info = rv_me.json()
    my_academia_id = user_info.get('academia_id')
    print(f"[TEST]    Usuario vinculado a academia: {my_academia_id}")
    
    # 2. INTENTAR LISTAR TARIFAS (debe fallar 403)
    print("[TEST] 2. Intentar listar tarifas (debe fallar 403)")
    rv_list = requests.get(f"{BASE_URL}/tarifas", headers=headers)
    assert rv_list.status_code == 403, f"Expected 403, got {rv_list.status_code}"
    print("[TEST]    ✓ Listado bloqueado: 403 Forbidden")
    
    # 3. INTENTAR LISTAR TARIFAS con filtro de su academia (debe fallar 403)
    print(f"[TEST] 3. Intentar listar tarifas con academia_id={my_academia_id} (debe fallar 403)")
    rv_list_filtered = requests.get(f"{BASE_URL}/tarifas?academia_id={my_academia_id}", headers=headers)
    assert rv_list_filtered.status_code == 403
    print("[TEST]    ✓ Listado filtrado bloqueado: 403 Forbidden")
    
    # Crear una tarifa como admin_plataforma para probar GET/PATCH/DELETE
    print("[TEST] 4. Preparar: crear tarifa como admin_plataforma")
    access_platform, _ = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    headers_platform = {'Authorization': f'Bearer {access_platform}'}
    
    # Crear academia si es necesario
    if not my_academia_id:
        acad_rv = requests.post(
            f"{BASE_URL}/academias",
            json={'nombre': f"Academia_Test_{uuid.uuid4().hex[:8]}"},
            headers=headers_platform
        )
        my_academia_id = acad_rv.json()['result']['id']
    
    tarifa_rv = requests.post(
        f"{BASE_URL}/tarifas",
        json={'academia_id': my_academia_id, 'descripcion': 'Tarifa test profesor', 'precio_base': 45.0},
        headers=headers_platform
    )
    tarifa_id = tarifa_rv.json()['result']['id']
    print(f"[TEST]    ✓ Tarifa creada con ID: {tarifa_id} (para pruebas)")
    
    # 4. INTENTAR OBTENER TARIFA (debe fallar 403)
    print(f"[TEST] 5. Intentar obtener tarifa ID: {tarifa_id} (debe fallar 403)")
    rv_get = requests.get(f"{BASE_URL}/tarifas/{tarifa_id}", headers=headers)
    assert rv_get.status_code == 403, f"Expected 403, got {rv_get.status_code}"
    print("[TEST]    ✓ Obtener tarifa bloqueado: 403 Forbidden")
    
    # 5. INTENTAR CREAR TARIFA (debe fallar 403)
    print("[TEST] 6. Intentar crear tarifa (debe fallar 403)")
    rv_create = requests.post(
        f"{BASE_URL}/tarifas",
        json={'descripcion': 'Tarifa profesor intento', 'precio_base': 50.0},
        headers=headers
    )
    assert rv_create.status_code == 403, f"Expected 403, got {rv_create.status_code}"
    print("[TEST]    ✓ Creación bloqueada: 403 Forbidden")
    
    # 6. INTENTAR CREAR TARIFA con academia_id explícito (debe fallar 403)
    print(f"[TEST] 7. Intentar crear tarifa con academia_id={my_academia_id} (debe fallar 403)")
    rv_create_explicit = requests.post(
        f"{BASE_URL}/tarifas",
        json={'academia_id': my_academia_id, 'descripcion': 'Tarifa profesor', 'precio_base': 55.0},
        headers=headers
    )
    assert rv_create_explicit.status_code == 403
    print("[TEST]    ✓ Creación con academia_id bloqueada: 403 Forbidden")
    
    # 7. INTENTAR MODIFICAR TARIFA (debe fallar 403)
    print(f"[TEST] 8. Intentar modificar tarifa ID: {tarifa_id} (debe fallar 403)")
    rv_update = requests.patch(
        f"{BASE_URL}/tarifas/{tarifa_id}",
        json={'precio_base': 60.0},
        headers=headers
    )
    assert rv_update.status_code == 403, f"Expected 403, got {rv_update.status_code}"
    print("[TEST]    ✓ Modificación bloqueada: 403 Forbidden")
    
    # 8. INTENTAR ELIMINAR TARIFA (debe fallar 403)
    print(f"[TEST] 9. Intentar eliminar tarifa ID: {tarifa_id} (debe fallar 403)")
    rv_delete = requests.delete(f"{BASE_URL}/tarifas/{tarifa_id}", headers=headers)
    assert rv_delete.status_code == 403, f"Expected 403, got {rv_delete.status_code}"
    print("[TEST]    ✓ Eliminación bloqueada: 403 Forbidden")
    
    # Limpiar: eliminar tarifa creada
    print("[TEST] 10. Limpiar: eliminar tarifa creada")
    requests.delete(f"{BASE_URL}/tarifas/{tarifa_id}", headers=headers_platform)
    
    # 9. LOGOUT
    print("[TEST] 11. Logout")
    rv_logout = logout_with_refresh(refresh)
    assert rv_logout.status_code == 200
    print("[TEST]    ✓ Logout exitoso")
    
    print("\n[TEST] ✅ TEST COMPLETADO: Profesor_academia sin acceso a tarifas (todos los endpoints bloqueados)")


@pytest.mark.meta(title='Profesor_academia: verificar mensaje de error', desc='Verificar que los mensajes de error son apropiados')
def test_profesor_academia_error_messages(client):
    """Test verificando mensajes de error apropiados para profesor_academia."""
    
    print("\n[TEST] Verificar mensajes de error para profesor_academia")
    access, refresh = login_and_get_tokens('reserve_user_academia_1_1@academia.com', 'password_reserve_user_academia_1_1')
    headers = {'Authorization': f'Bearer {access}'}
    
    # 1. Verificar estructura de respuesta de error
    print("[TEST] 1. Verificar estructura de respuesta 403")
    rv = requests.get(f"{BASE_URL}/tarifas", headers=headers)
    assert rv.status_code == 403
    error_data = rv.json()
    assert error_data.get('ok') is False, "Campo 'ok' debe ser False"
    assert 'error' in error_data, "Debe incluir campo 'error'"
    assert error_data['error'] == 'forbidden', "Error debe ser 'forbidden'"
    print(f"[TEST]    ✓ Estructura correcta: {error_data}")
    
    # 2. Verificar que reason está presente
    print("[TEST] 2. Verificar que se incluye 'reason' en respuesta")
    assert 'reason' in error_data, "Debe incluir campo 'reason'"
    print(f"[TEST]    ✓ Reason presente: {error_data.get('reason')}")
    
    # 3. Verificar consistencia en diferentes endpoints
    print("[TEST] 3. Verificar consistencia de errores en POST")
    rv_post = requests.post(
        f"{BASE_URL}/tarifas",
        json={'descripcion': 'Test', 'precio_base': 50},
        headers=headers
    )
    assert rv_post.status_code == 403
    assert rv_post.json()['error'] == 'forbidden'
    print("[TEST]    ✓ POST retorna mismo tipo de error")
    
    # Crear tarifa para probar otros endpoints
    access_platform, _ = login_and_get_tokens('admin_plataforma@academia.com', 'password_admin_plataforma')
    rv_me = requests.get(f"{BASE_URL}/usuarios/me", headers=headers)
    acad_id = rv_me.json().get('academia_id', 1)
    tarifa_rv = requests.post(
        f"{BASE_URL}/tarifas",
        json={'academia_id': acad_id, 'descripcion': 'Test', 'precio_base': 40},
        headers={'Authorization': f'Bearer {access_platform}'}
    )
    tarifa_id = tarifa_rv.json()['result']['id']
    
    print("[TEST] 4. Verificar consistencia de errores en GET detalle")
    rv_get = requests.get(f"{BASE_URL}/tarifas/{tarifa_id}", headers=headers)
    assert rv_get.status_code == 403
    assert rv_get.json()['error'] == 'forbidden'
    print("[TEST]    ✓ GET detalle retorna mismo tipo de error")
    
    print("[TEST] 5. Verificar consistencia de errores en PATCH")
    rv_patch = requests.patch(
        f"{BASE_URL}/tarifas/{tarifa_id}",
        json={'precio_base': 45},
        headers=headers
    )
    assert rv_patch.status_code == 403
    assert rv_patch.json()['error'] == 'forbidden'
    print("[TEST]    ✓ PATCH retorna mismo tipo de error")
    
    print("[TEST] 6. Verificar consistencia de errores en DELETE")
    rv_delete = requests.delete(f"{BASE_URL}/tarifas/{tarifa_id}", headers=headers)
    assert rv_delete.status_code == 403
    assert rv_delete.json()['error'] == 'forbidden'
    print("[TEST]    ✓ DELETE retorna mismo tipo de error")
    
    # Limpiar
    requests.delete(f"{BASE_URL}/tarifas/{tarifa_id}", headers={'Authorization': f'Bearer {access_platform}'})
    logout_with_refresh(refresh)
    
    print("\n[TEST] ✅ MENSAJES DE ERROR VERIFICADOS")
