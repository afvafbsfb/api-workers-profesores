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

    # metadata para logs
    ip_raw = request.remote_addr
    def _ip_to_bytes(ip_str):
        if not ip_str:
            return None
        try:
            return socket.inet_pton(socket.AF_INET6, ip_str)
        except Exception:
            try:
                return socket.inet_pton(socket.AF_INET, ip_str)
            except Exception:
                return None

    ip_bytes = _ip_to_bytes(ip_raw)
    user_agent = request.headers.get('User-Agent')
    device_id = request.headers.get('X-Device-Id')
    client = request.headers.get('X-Client')

    if not usuario:
        # No podemos registrar en UserLoginLog porque requiere usuario_id (FK NOT NULL)
        return jsonify({"ok": False, "error": "Usuario no encontrado"}), 401

    now = datetime.now(timezone.utc)

    # Comprobar bloqueo temporal por anti-brute-force
    if usuario.locked_until and usuario.locked_until > now:
        # registrar intento fallido
        try:
            ull = UserLoginLog(usuario_id=usuario.id, success=False, fail_reason='LOCKED', ip=ip_bytes, user_agent=user_agent, device_id=device_id, client=client)
            db.session.add(ull)
            db.session.commit()
        except Exception:
            db.session.rollback()
        return jsonify({"ok": False, "error": "Usuario temporalmente bloqueado"}), 403

    if usuario.estado == "Bloqueado":
        try:
            ull = UserLoginLog(usuario_id=usuario.id, success=False, fail_reason='DISABLED', ip=ip_bytes, user_agent=user_agent, device_id=device_id, client=client)
            db.session.add(ull)
            db.session.commit()
        except Exception:
            db.session.rollback()
        return jsonify({"ok": False, "error": "Usuario bloqueado"}), 403

    # Verificar contraseña
    if not usuario.check_password(password):
        # Incrementar contador de fallos y fijar last_failed_login_at
        try:
            usuario.failed_login_count = (usuario.failed_login_count or 0) + 1
            usuario.last_failed_login_at = now
            # política: bloquear tras 5 fallos durante 15 minutos
            MAX_FAILED = 5
            LOCK_MINUTES = 15
            if usuario.failed_login_count >= MAX_FAILED:
                usuario.locked_until = now + timedelta(minutes=LOCK_MINUTES)
                usuario.estado = 'Bloqueado'
            db.session.add(usuario)
            # registrar intento
            ull = UserLoginLog(usuario_id=usuario.id, success=False, fail_reason='BAD_CREDENTIALS', ip=ip_bytes, user_agent=user_agent, device_id=device_id, client=client)
            db.session.add(ull)
            db.session.commit()
        except Exception:
            db.session.rollback()
        return jsonify({"ok": False, "error": "Contraseña incorrecta"}), 401

    # Login correcto: resetear contador de fallos y campos de bloqueo
    try:
        usuario.failed_login_count = 0
        usuario.last_failed_login_at = None
        usuario.locked_until = None
        usuario.estado = 'Activo'
        db.session.add(usuario)
        db.session.commit()
    except Exception:
        db.session.rollback()

    # registrar login exitoso
    try:
        ull = UserLoginLog(usuario_id=usuario.id, success=True, ip=ip_bytes, user_agent=user_agent, device_id=device_id, client=client)
        db.session.add(ull)
        db.session.commit()
    except Exception:
        db.session.rollback()

    tokens = generar_tokens(usuario_id=usuario.id)
    return jsonify({"ok": True, "tokens": tokens}), 200

# Registrar el blueprint en la aplicación principal
# Esto debe hacerse en el archivo principal de la aplicación (app.py o main.py)
# app.register_blueprint(login_bp)


@login_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_tokens():
    """Renueva access + refresh: valida que el refresh token recibido exista (hash) y no esté revocado.
    Realiza rotación: crea un nuevo RefreshToken y marca el anterior como revoked/replaced_by_id.
    """
    try:
        # La identidad del refresh es el usuario id (según crear tokens en generar_tokens)
        identity = get_jwt_identity()
        usuario_id = identity if isinstance(identity, int) or isinstance(identity, str) else identity.get('usuario_id')

        # Obtener el raw refresh token desde el header Authorization (Bearer ...) si está disponible
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            raw_token = auth_header.split(' ', 1)[1].strip()
        else:
            # Si no viene por header, intentar obtenerlo del body JSON
            raw_token = request.get_json(silent=True) and request.get_json().get('refresh_token')

        if not raw_token:
            return jsonify({"ok": False, "error": "refresh_missing"}), 400

        # Calcular hash y buscar en BD un refresh token válido
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        now = datetime.now(timezone.utc)
        existing = RefreshToken.query.filter_by(token_hash=token_hash).first()
        if not existing:
            return jsonify({"ok": False, "error": "refresh_not_found"}), 401
        if existing.revoked_at is not None:
            return jsonify({"ok": False, "error": "refresh_revoked"}), 401
        if existing.expires_at and existing.expires_at < now:
            return jsonify({"ok": False, "error": "refresh_expired"}), 401

        # Rotación: crear nuevo refresh token y marcar el anterior
        nuevo_refresh = create_refresh_token(identity=usuario_id, expires_delta=REFRESH_EXPIRES)
        nuevo_hash = hashlib.sha256(nuevo_refresh.encode('utf-8')).hexdigest()
        expires_at = now + REFRESH_EXPIRES

        try:
            rt_new = RefreshToken(usuario_id=usuario_id, token_hash=nuevo_hash, expires_at=expires_at, ip=existing.ip, user_agent=existing.user_agent, device_id=existing.device_id)
            db.session.add(rt_new)
            # marcar el antiguo como revocado y linkear
            existing.revoked_at = now
            existing.replaced_by_id = None  # lo rellenamos tras flush
            db.session.add(existing)
            db.session.flush()
            existing.replaced_by_id = rt_new.id
            db.session.add(existing)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({"ok": False, "error": "db_error"}), 500

        # Generar nuevo access token
        usuario = db.session.get(Usuario, usuario_id)
        token_version = usuario.token_version if usuario else 0
        access_token = create_access_token(identity={"usuario_id": usuario_id, "token_version": token_version}, expires_delta=ACCESS_EXPIRES)

        return jsonify({"ok": True, "access_token": access_token, "refresh_token": nuevo_refresh}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": "refresh_error", "message": str(e)}), 500



@login_bp.route('/auth/logout', methods=['POST'])
@jwt_required(refresh=True)
def logout():
    """Revoca el refresh token usado para la petición. Opcionalmente puede revocar todos los tokens del usuario.
    """
    try:
        identity = get_jwt_identity()
        usuario_id = identity if isinstance(identity, int) or isinstance(identity, str) else identity.get('usuario_id')

        # Obtener raw token similar al refresh handler
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            raw_token = auth_header.split(' ', 1)[1].strip()
        else:
            raw_token = request.get_json(silent=True) and request.get_json().get('refresh_token')

        if not raw_token:
            return jsonify({"ok": False, "error": "refresh_missing"}), 400

        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        existing = RefreshToken.query.filter_by(token_hash=token_hash).first()
        now = datetime.now(timezone.utc)
        if existing:
            try:
                existing.revoked_at = now
                db.session.add(existing)
                # registrar logout_at en el último UserLoginLog no terminado (success=True)
                ull = UserLoginLog.query.filter_by(usuario_id=existing.usuario_id, logout_at=None).order_by(UserLoginLog.login_at.desc()).first()
                if ull:
                    ull.logout_at = now
                    db.session.add(ull)
                db.session.commit()
            except Exception:
                db.session.rollback()
                return jsonify({"ok": False, "error": "db_error"}), 500

        return jsonify({"ok": True}), 204
    except Exception as e:
        return jsonify({"ok": False, "error": "logout_error", "message": str(e)}), 500
