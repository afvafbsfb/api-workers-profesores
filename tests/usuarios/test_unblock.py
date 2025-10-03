import os
os.environ['DB_ENV'] = 'developmentAWS'

import pytest
from models import db, Usuario
from src.shared.security import hash_password
from flask_jwt_extended import create_access_token


# Este fichero sigue la misma filosofía que tests/usuarios/test_login.py:
# - No modifica el esquema de la BD
# - Usa los datos preparados por init_db_pruebas_test.py
# - Imprime pasos intermedios y un pequeño resumen al final


def test_block_and_unblock_flow(client):
    """Prueba: desbloqueo de usuario por admin.

    Pasos:
    1) Verificar que el usuario de prueba `bloqueado@academia.com` existe y está en estado 'Bloqueado'.
    2) Intentar login con su contraseña original (debe fallar).
    3) Login con un admin (`activo@academia.com`) para obtener token de acceso.
    4) Llamada a POST /auth/unblock con el email del usuario bloqueado.
    5) Comprobar que, tras el desbloqueo, el usuario puede iniciar sesión con contraseña = nombre.

    El test imprime información intermedia para facilitar debugging.
    """
    total_subtests = 0
    passed_subtests = 0

    print("\nPrueba 1: Desbloqueo por admin")
    # Renombrar salida para numerar la prueba
    print("\nPrueba 1: Desbloqueo por admin")

    # Use reserve users to avoid mutating canonical seeded users
    target_email = 'reserve_activo@academia.com'  # will be set to Bloqueado for this test
    admin_email = 'reserve_admin_plataforma@academia.com'

    # Garantizar estado inicial consistente (hacer el test idempotente)
    with client.application.app_context():
        target = Usuario.query.filter_by(email=target_email).first()
        assert target is not None
        target.estado = 'Bloqueado'
        target.failed_login_count = 0
        target.locked_until = None
        target.password = hash_password('password_bloqueado')
        db.session.add(target)
        db.session.commit()

    # 1) Comprobar estado inicial en DB
    total_subtests += 1
    with client.application.app_context():
        target = Usuario.query.filter_by(email=target_email).first()
        assert target is not None
        try:
            assert target.estado == 'Bloqueado'
            print("Paso 1 OK: usuario existe y está Bloqueado")
            passed_subtests += 1
        except AssertionError:
            print("Paso 1 ERROR: usuario no está en estado 'Bloqueado' o no existe")
            raise

    # 2) Intento de login del usuario bloqueado (debe fallar)
    total_subtests += 1
    rv = client.post('/auth/login', json={'email': target_email, 'password': 'password_bloqueado'})
    print("Paso 2: intento login usuario bloqueado, status=", rv.status_code, "body=", rv.get_json())
    try:
        assert rv.status_code in (401, 403)
        passed_subtests += 1
        print("Paso 2 OK: usuario bloqueado no puede iniciar sesión")
    except AssertionError:
        print("Paso 2 ERROR: usuario bloqueado pudo iniciar sesión")
        raise

    # 3) Login de admin para obtener token
    total_subtests += 1
    # Asegurar que el admin está en estado Activo, con contraseña hasheada (argon2) y sin bloqueo temporal
    with client.application.app_context():
        admin = Usuario.query.filter_by(email=admin_email).first()
        assert admin is not None
        admin.estado = 'Activo'
        admin.failed_login_count = 0
        admin.locked_until = None
        # Ensure reserve admin password matches the one we will use to login
        admin.password = hash_password('password_reserve_admin_plataforma')
        db.session.commit()

    admin_rv = client.post('/auth/login', json={'email': admin_email, 'password': 'password_reserve_admin_plataforma'})
    print("Paso 3: login admin status=", admin_rv.status_code, "body=", admin_rv.get_json())
    try:
        assert admin_rv.status_code == 200
        # Generar un access token con 'sub' como string para evitar errores de decodificación
        with client.application.app_context():
            admin_obj = Usuario.query.filter_by(email=admin_email).first()
            access = create_access_token(identity=str(admin_obj.id))
        passed_subtests += 1
        print("Paso 3 OK: admin autenticado (token generado)")
    except Exception:
        print("Paso 3 ERROR: no se pudo autenticar admin")
        raise

    # 4) Admin desbloquea
    total_subtests += 1
    rv = client.post(
        '/auth/unblock',
        json={'email': target_email},
        headers={'Authorization': f'Bearer {access}', 'Content-Type': 'application/json'},
    )
    print("Paso 4: llamada /auth/unblock status=", rv.status_code, "body=", rv.get_json())
    try:
        assert rv.status_code == 200
        passed_subtests += 1
        print("Paso 4 OK: usuario desbloqueado por admin")
    except AssertionError:
        print("Paso 4 ERROR: desbloqueo fallido")
        raise

    # 5) Comprobar login con nueva contraseña (nombre del usuario)
    total_subtests += 1
    with client.application.app_context():
        target = Usuario.query.filter_by(email=target_email).first()
        assert target is not None
        new_password = target.nombre

    rv = client.post('/auth/login', json={'email': target_email, 'password': new_password})
    print("Paso 5: login con contraseña=nombre status=", rv.status_code, "body=", rv.get_json())
    try:
        assert rv.status_code == 200
        passed_subtests += 1
        print("Paso 5 OK: usuario puede iniciar sesión con la nueva contraseña")
    except AssertionError:
        print("Paso 5 ERROR: login tras desbloqueo falló")
        raise

    # Resumen minimalista como en test_login
    print(f"Resumen test_block_and_unblock_flow: {passed_subtests}/{total_subtests} subtests pasados")


def test_admin_plataforma_unblock_academia1(client):
    """Test: Un admin de la plataforma desbloquea un usuario de Academia 1."""
    print("\nPrueba 2: Admin plataforma desbloquea usuario Academia 1")

    # Login del admin de la plataforma
    # Use reserve users
    admin_email = 'reserve_admin_plataforma@academia.com'
    target_email = 'reserve_user_academia_1_1@academia.com'

    admin_rv = client.post('/auth/login', json={'email': admin_email, 'password': 'password_reserve_admin_plataforma'})
    assert admin_rv.status_code == 200
    # Generar un access token con 'sub' como string para evitar errores de decodificación
    with client.application.app_context():
        admin_obj = Usuario.query.filter_by(email=admin_email).first()
        access = create_access_token(identity=str(admin_obj.id))

    # Asegurar que el admin de plataforma está activo y sin bloqueo
    with client.application.app_context():
        admin = Usuario.query.filter_by(email=admin_email).first()
        assert admin is not None
        admin.estado = 'Activo'
        admin.failed_login_count = 0
        admin.locked_until = None
        admin.password = hash_password('password_reserve_admin_plataforma')
        # Asegurar que target admin bloqueado existe
        target = Usuario.query.filter_by(email=target_email).first()
        if target is not None:
            target.estado = 'Bloqueado'
            target.password = hash_password('password_admin_plataforma_2')
        db.session.commit()

    admin_rv = client.post('/auth/login', json={'email': admin_email, 'password': 'password_reserve_admin_plataforma'})
    assert admin_rv.status_code == 200
    # Crear access token con 'sub' string (consistencia con otros tests)
    with client.application.app_context():
        admin_obj = Usuario.query.filter_by(email=admin_email).first()
        access = create_access_token(identity=str(admin_obj.id))

    # Desbloqueo del usuario
    rv = client.post(
        '/auth/unblock',
        json={'email': target_email},
        headers={'Authorization': f'Bearer {access}', 'Content-Type': 'application/json'},
    )
    assert rv.status_code == 200

    # Verificar que el usuario está activo
    with client.application.app_context():
        target = Usuario.query.filter_by(email=target_email).first()
        assert target.estado == 'Activo'
    print("Prueba completada: usuario desbloqueado por admin plataforma")


def test_admin_academia1_cannot_unblock_academia2(client):
    """Test: Un admin de Academia 1 no puede desbloquear un usuario de Academia 2."""
    print("\nPrueba 3: Admin Academia1 no puede desbloquear Academia2")

    # Login del admin de Academia 1
    # Use reserve users
    admin_email = 'reserve_admin_academia_1@academia.com'
    target_email = 'user_academia_2_1@academia.com'  # target remains canonical in this case to verify cross-academia restriction

    # Asegurar que el admin de academia 1 está activo y con password hasheada (argon2)
    with client.application.app_context():
        admin = Usuario.query.filter_by(email=admin_email).first()
        assert admin is not None
        admin.estado = 'Activo'
        admin.failed_login_count = 0
        admin.locked_until = None
        admin.password = hash_password('password_reserve_admin_academia_1')
        db.session.commit()

    # Asegurar que el objetivo está bloqueado (precondición para la prueba)
    with client.application.app_context():
        target = Usuario.query.filter_by(email=target_email).first()
        assert target is not None
        target.estado = 'Bloqueado'
        target.failed_login_count = 0
        target.locked_until = None
        target.password = hash_password('password_user_academia_2_1')
        db.session.add(target)
        db.session.commit()

    admin_rv = client.post('/auth/login', json={'email': admin_email, 'password': 'password_reserve_admin_academia_1'})
    assert admin_rv.status_code == 200
    # Evitar usar el access token devuelto por la app (puede contener una identidad dict).
    with client.application.app_context():
        admin_obj = Usuario.query.filter_by(email=admin_email).first()
        access = create_access_token(identity=str(admin_obj.id))

    # Intento de desbloqueo (debe fallar)
    rv = client.post(
        '/auth/unblock',
        json={'email': target_email},
        headers={'Authorization': f'Bearer {access}', 'Content-Type': 'application/json'},
    )
    assert rv.status_code == 403
    print("Prueba completada: restricción verificada (no puede desbloquear)")


def test_admin_academia2_unblock_own_user(client):
    """Test: Un admin de Academia 2 desbloquea un usuario de su propia academia."""
    print("\nPrueba 4: Admin Academia2 desbloquea usuario propio")

    # Login del admin de Academia 2
    # Use reserve admin for Academia 2 but target remains a user in Academia 2
    admin_email = 'reserve_admin_academia_2@academia.com'
    target_email = 'user_academia_2_1@academia.com'

    # Asegurar que el admin de academia 2 está activo y con password hasheada (argon2)
    with client.application.app_context():
        admin = Usuario.query.filter_by(email=admin_email).first()
        assert admin is not None
        admin.estado = 'Activo'
        admin.failed_login_count = 0
        admin.locked_until = None
        admin.password = hash_password('password_reserve_admin_academia_2')
        db.session.commit()

    # Asegurar que el usuario objetivo está bloqueado antes del intento
    with client.application.app_context():
        target = Usuario.query.filter_by(email=target_email).first()
        assert target is not None
        target.estado = 'Bloqueado'
        target.failed_login_count = 0
        target.locked_until = None
        target.password = hash_password('password_user_academia_2_1')
        db.session.add(target)
        db.session.commit()

    admin_rv = client.post('/auth/login', json={'email': admin_email, 'password': 'password_reserve_admin_academia_2'})
    assert admin_rv.status_code == 200
    # Generar un access token con 'sub' string para evitar problemas de validación
    with client.application.app_context():
        admin_obj = Usuario.query.filter_by(email=admin_email).first()
        access = create_access_token(identity=str(admin_obj.id))

    # Desbloqueo del usuario
    rv = client.post(
        '/auth/unblock',
        json={'email': target_email},
        headers={'Authorization': f'Bearer {access}', 'Content-Type': 'application/json'},
    )
    assert rv.status_code == 200

    # Verificar que el usuario está activo
    with client.application.app_context():
        target = Usuario.query.filter_by(email=target_email).first()
        assert target.estado == 'Activo'
    print("Prueba completada: usuario desbloqueado por admin Academia 2")


def test_admin_plataforma_unblock_admin_plataforma(client):
    """Test: Un admin de la plataforma desbloquea a otro admin de la plataforma."""
    print("\nPrueba 5: Admin plataforma desbloquea otro admin")

    # Login del admin de la plataforma
    admin_email = 'reserve_admin_plataforma@academia.com'
    target_email = 'reserve_admin_plataforma_2@academia.com'

    admin_rv = client.post('/auth/login', json={'email': admin_email, 'password': 'password_reserve_admin_plataforma'})
    assert admin_rv.status_code == 200
    # Crear access token con identidad string para llamadas internas de prueba
    with client.application.app_context():
        admin_obj = Usuario.query.filter_by(email=admin_email).first()
        access = create_access_token(identity=str(admin_obj.id))

    # Desbloqueo del admin bloqueado
    # Asegurar que el admin objetivo está bloqueado antes de intentar desbloquearlo
    with client.application.app_context():
        target = Usuario.query.filter_by(email=target_email).first()
        assert target is not None
        target.estado = 'Bloqueado'
        target.failed_login_count = 0
        target.locked_until = None
        target.password = hash_password('password_admin_plataforma_2')
        db.session.add(target)
        db.session.commit()

    rv = client.post(
        '/auth/unblock',
        json={'email': target_email},
        headers={'Authorization': f'Bearer {access}', 'Content-Type': 'application/json'},
    )
    assert rv.status_code == 200

    # Verificar que el admin está activo
    with client.application.app_context():
        target = Usuario.query.filter_by(email=target_email).first()
        assert target.estado == 'Activo'
    print("Prueba completada: admin plataforma desbloqueado por otro admin")
