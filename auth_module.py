import os
from flask import request, jsonify, Blueprint
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, create_access_token, create_refresh_token, jwt_required, get_jwt
from datetime import timedelta, datetime, timezone
import hashlib
from flask_sqlalchemy import SQLAlchemy
from models import Usuario, RefreshToken, db, UserLoginLog
import socket

# Configuración de tiempos de expiración
ACCESS_EXPIRES = timedelta(minutes=15)
REFRESH_EXPIRES = timedelta(days=7)

# Middleware para validar tokens de acceso
PUBLIC_PATHS = ("/health", "/debug", "/auth/login", "/auth/refresh", "/auth/logout")

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
    # Obtener token_version del usuario para incluirlo en el access token
    # Use session.get(...) instead of Query.get(...) to avoid SQLAlchemy legacy warning
    usuario = db.session.get(Usuario, usuario_id)
    token_version = usuario.token_version if usuario else 0

    # Incluir token_version en la identidad del access token
    access_identity = {"usuario_id": usuario_id, "token_version": token_version}
    access_token = create_access_token(identity=access_identity, expires_delta=ACCESS_EXPIRES)
    refresh_token = create_refresh_token(identity=str(usuario_id), expires_delta=REFRESH_EXPIRES)

    # Persistir hash del refresh token (SHA-256) en la tabla RefreshToken
    try:
        token_hash = hashlib.sha256(refresh_token.encode('utf-8')).hexdigest()
        expires_at = datetime.now(timezone.utc) + REFRESH_EXPIRES
        rt = RefreshToken(usuario_id=usuario_id, token_hash=token_hash, expires_at=expires_at)
        db.session.add(rt)
        db.session.commit()
    except Exception:
        db.session.rollback()

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
        current_user = get_jwt_identity()  # para refresh token identity es el usuario_id
        usuario_id = current_user if isinstance(current_user, int) or isinstance(current_user, str) else current_user.get('usuario_id')
        usuario = db.session.get(Usuario, usuario_id)
        token_version = usuario.token_version if usuario else 0
        nuevo_access_token = create_access_token(identity={"usuario_id": usuario_id, "token_version": token_version}, expires_delta=ACCESS_EXPIRES)
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

# NOTE: The HTTP route handlers for login/refresh/logout were moved to
# the new DDD-style package `src.autenticacion`. This module keeps the
# token utilities and middleware (generar_tokens, enforce_jwt_globally,
# renovar_token, etc.) but no longer declares or registers HTTP routes so
# route registration is centralized in the `interfaces` layer.
