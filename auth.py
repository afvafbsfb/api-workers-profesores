"""
Compatibility shim: original module was renamed to auth_module.py to avoid
shadowing problems during development. This file re-exports the public
symbols so code importing `auth` keeps working.
"""
from auth_module import (
    login_bp,
    require_jwt,
    generar_tokens,
    renovar_token,
    enforce_jwt_globally,
)

__all__ = [
    'login_bp',
    'require_jwt',
    'generar_tokens',
    'renovar_token',
    'enforce_jwt_globally',
]
import os
from flask import request, jsonify, Blueprint
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, create_access_token, create_refresh_token, jwt_required, get_jwt
from datetime import timedelta
from flask_sqlalchemy import SQLAlchemy
from models import Usuario

# Configuración de tiempos de expiración
ACCESS_EXPIRES = timedelta(minutes=15)
REFRESH_EXPIRES = timedelta(days=7)

# Middleware para validar tokens de acceso
PUBLIC_PATHS = ("/health", "/debug", "/auth/login")

def require_jwt(f):
    """Decorador para requerir token JWT en endpoints concretos."""
    @wraps(f)
    def decorated(*args, **kwargs):
        raw_path = request.path or '/'
        if raw_path in PUBLIC_PATHS:
            return f(*args, **kwargs)  # Permitir acceso a rutas públicas
        try:
            verify_jwt_in_request()
        except Exception as e:
            return jsonify({"ok": False, "error": "unauthorized", "message": str(e)}), 401
        return f(*args, **kwargs)
    return decorated

# Función para generar tokens

def generar_tokens(usuario_id):
    """Genera un token de acceso y un token de refrescado."""
    access_token = create_access_token(identity=usuario_id, expires_delta=ACCESS_EXPIRES)
    refresh_token = create_refresh_token(identity=usuario_id, expires_delta=REFRESH_EXPIRES)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }

# Función para renovar el token de acceso
@jwt_required(refresh=True)
def renovar_token():
    """
    Renueva el token de acceso utilizando un token de refresco válido.
    Requiere que el token de refresco sea enviado en el encabezado Authorization.
    """
    try:
        current_user = get_jwt_identity()
        nuevo_access_token = create_access_token(identity=current_user, expires_delta=ACCESS_EXPIRES)
        return jsonify({"ok": True, "access_token": nuevo_access_token}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": "No se pudo renovar el token", "message": str(e)}), 400

# Middleware global para proteger rutas

def enforce_jwt_globally():
    """Función para usar en before_request y proteger toda la API salvo rutas públicas."""
    raw_path = request.path.rstrip('/') or '/'  # Normalize path by removing trailing slashes
    print(f"[DEBUG][AUTH] Verificando ruta: {raw_path}", flush=True)
    print(f"[DEBUG][AUTH] Rutas públicas configuradas: {PUBLIC_PATHS}", flush=True)

    if raw_path in PUBLIC_PATHS:
        print(f"[DEBUG][AUTH] Ruta pública detectada: {raw_path}", flush=True)
        return None  # Permitir acceso a rutas públicas sin validar el token

    # Validar solo en rutas protegidas
    try:
        print(f"[DEBUG][AUTH] Intentando verificar JWT para ruta protegida: {raw_path}", flush=True)
        verify_jwt_in_request()
    except Exception as e:
        print(f"[DEBUG][AUTH] Error al verificar JWT: {str(e)}", flush=True)
        return jsonify({"ok": False, "error": "unauthorized", "message": str(e)}), 401
    return None

# Crear un blueprint para las rutas de autenticación
login_bp = Blueprint('login_bp', __name__)

# Registrar rutas en el blueprint
@login_bp.route('/auth/login', methods=['POST'])
def login():
    print("[DEBUG][LOGIN] Endpoint /auth/login ejecutado", flush=True)
    """
    Endpoint para manejar el inicio de sesión.
    Requiere un cuerpo JSON con 'email' y 'password'.
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # Buscar el usuario en la base de datos
    usuario = Usuario.query.filter_by(email=email).first()

    if not usuario:
        return jsonify({"ok": False, "error": "Usuario no encontrado"}), 401

    if usuario.estado == "Bloqueado":
        return jsonify({"ok": False, "error": "Usuario bloqueado"}), 403

    if not usuario.check_password(password):
        return jsonify({"ok": False, "error": "Contraseña incorrecta"}), 401

    tokens = generar_tokens(usuario_id=usuario.id)
    return jsonify({"ok": True, "tokens": tokens}), 200

# Registrar el blueprint en la aplicación principal
# Esto debe hacerse en el archivo principal de la aplicación (app.py o main.py)
# app.register_blueprint(login_bp)
