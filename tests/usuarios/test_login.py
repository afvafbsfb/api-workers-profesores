import os
import pytest
from flask.testing import FlaskClient
from app import create_app
from models import db
from models import Usuario  # Importar el modelo Usuario
from werkzeug.security import generate_password_hash  # Usar para hash_password
from typing import Generator

@pytest.fixture
def client() -> Generator[FlaskClient, None, None]:
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()

def test_login_usuario_activo(client):
    with client.application.app_context():
        # Crear el usuario activo en la base de datos
        usuario_activo = Usuario(
            nombre="Usuario Activo",
            email="activo@academia.com",
            password=generate_password_hash("password_activo"),  # Generar hash de la contraseña
            rol_id=1,
            estado="Activo"
        )
        db.session.add(usuario_activo)
        db.session.commit()

    # Realizar la solicitud al endpoint de login
    response = client.post('/auth/login', json={
        'email': 'activo@academia.com',
        'password': 'password_activo'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert 'tokens' in data
    assert 'access_token' in data['tokens']
    assert 'refresh_token' in data['tokens']

def test_login_usuario_no_existente(client):
    response = client.post('/auth/login', json={
        'email': 'noexiste@academia.com',
        'password': 'password_incorrecta'
    })
    assert response.status_code == 401

def test_login_usuario_bloqueado(client):
    with client.application.app_context():
        usuario_bloqueado = Usuario(
            nombre="Usuario Bloqueado",
            email="bloqueado@academia.com",
            password=generate_password_hash("password_bloqueado"),
            rol_id=1,
            estado="Bloqueado"
        )
        db.session.add(usuario_bloqueado)
        db.session.commit()

    response = client.post('/auth/login', json={
        'email': 'bloqueado@academia.com',
        'password': 'password_bloqueado'
    })
    assert response.status_code == 403

def test_routes(client):
    # Agregar registro para verificar el contexto de la aplicación
    print("[DEBUG] Verificando contexto de la aplicación en las pruebas.", flush=True)
    with client.application.app_context():
        print("[DEBUG] Contexto de la aplicación activo.", flush=True)
        routes = [rule.rule for rule in client.application.url_map.iter_rules()]
    print("Rutas disponibles:", routes)
    assert '/auth/login' in routes

def test_list_routes(client):
    with client.application.app_context():
        routes = [rule.rule for rule in client.application.url_map.iter_rules()]
    print("Rutas disponibles:", routes)
    assert '/auth/login' in routes

def test_blueprint_registration(client):
    with client.application.app_context():
        blueprints = client.application.blueprints.keys()
    print("Blueprints registrados:", blueprints)
    assert 'login_bp' in blueprints