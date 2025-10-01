from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, ValidationError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models import Usuario  # Modelo de usuario
from src.shared.security import verify_password
from auth_module import generar_tokens
from flask_jwt_extended import jwt_required, get_jwt_identity, create_refresh_token, create_access_token
from models import RefreshToken, Usuario, db, UserLoginLog, Rol
from src.shared.security import hash_password
import hashlib
from datetime import datetime, timezone, timedelta

# Crear Blueprint para las rutas de login
login_bp = Blueprint('login_bp', __name__)

# Configurar Rate-Limiting
limiter = Limiter(get_remote_address, default_limits=["5 per minute"])

# Esquema para validar la entrada
class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)

# Ruta para el login
@login_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")  # Limitar a 5 intentos por minuto
def login():
    try:
        # Validar entrada
        data = request.get_json()
        schema = LoginSchema()
        validated_data = schema.load(data)

        # Buscar usuario
        user = Usuario.query.filter_by(email=validated_data['email']).first()
        if not user:
            # No revelar si el usuario existe: devolver 401 genérico
            return jsonify({"ok": False, "error": "credenciales inválidas"}), 401

        # Verificar estado del usuario
        now = datetime.now(timezone.utc)
        # Comprobar bloqueo temporal por anti-brute-force
        def _is_locked(dt, now_dt):
            if dt is None:
                return False
            # dt may be naive or aware; normalize comparison
            if dt.tzinfo is None:
                return dt > now_dt.replace(tzinfo=None)
            return dt > now_dt

        if user.locked_until and _is_locked(user.locked_until, now):
            try:
                ull = UserLoginLog(usuario_id=user.id, success=False, fail_reason='LOCKED', ip=None, user_agent=request.headers.get('User-Agent'), device_id=request.headers.get('X-Device-Id'), client=request.headers.get('X-Client'))
                db.session.add(ull)
                db.session.commit()
            except Exception:
                db.session.rollback()
            return jsonify({"ok": False, "error": "Usuario temporalmente bloqueado"}), 403

        if user.estado != 'Activo':
            try:
                ull = UserLoginLog(usuario_id=user.id, success=False, fail_reason='DISABLED', ip=None, user_agent=request.headers.get('User-Agent'), device_id=request.headers.get('X-Device-Id'), client=request.headers.get('X-Client'))
                db.session.add(ull)
                db.session.commit()
            except Exception:
                db.session.rollback()
            return jsonify({"ok": False, "error": f"Usuario no está activo (estado: {user.estado})"}), 403

        # Verificar contraseña
        if not verify_password(validated_data['password'], user.password):
            # Incrementar contador de fallos y fijar last_failed_login_at
            try:
                user.failed_login_count = (user.failed_login_count or 0) + 1
                user.last_failed_login_at = now
                MAX_FAILED = 5
                LOCK_MINUTES = 15
                if user.failed_login_count >= MAX_FAILED:
                    user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
                    # Marcar estado como Bloqueado cuando se alcanza el umbral
                    user.estado = 'Bloqueado'
                db.session.add(user)
                ull = UserLoginLog(usuario_id=user.id, success=False, fail_reason='BAD_CREDENTIALS', ip=None, user_agent=request.headers.get('User-Agent'), device_id=request.headers.get('X-Device-Id'), client=request.headers.get('X-Client'))
                db.session.add(ull)
                db.session.commit()
            except Exception:
                db.session.rollback()
            return jsonify({"ok": False, "error": "credenciales inválidas"}), 401

        # Login correcto: resetear contador de fallos y campos de bloqueo
        try:
            # Resetear contadores y campos temporales, pero NO cambiar `estado`.
            # El desbloqueo debe realizarse explícitamente vía /auth/unblock.
            user.failed_login_count = 0
            user.last_failed_login_at = None
            user.locked_until = None
            db.session.add(user)
            db.session.commit()
        except Exception:
            db.session.rollback()

        # registrar login exitoso
        try:
            ull = UserLoginLog(usuario_id=user.id, success=True, ip=None, user_agent=request.headers.get('User-Agent'), device_id=request.headers.get('X-Device-Id'), client=request.headers.get('X-Client'))
            db.session.add(ull)
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Generar tokens (access + refresh)
        tokens = generar_tokens(usuario_id=user.id)

        return jsonify({"ok": True, "tokens": tokens}), 200

    except ValidationError as e:
        return jsonify({"error": e.messages}), 400



@login_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_tokens():
    """Renueva access + refresh: valida y rota el refresh token persistido.
    - Extrae la identidad del refresh token (puede ser string)
    - Obtiene el token raw desde Authorization o body
    - Verifica existencia, revocación y expiración
    - Crea nuevo refresh token y marca el anterior como revocado
    """

    identity = get_jwt_identity()
    if isinstance(identity, str) and identity.isdigit():
        usuario_id = int(identity)
    elif isinstance(identity, int):
        usuario_id = identity
    elif isinstance(identity, dict):
        usuario_id = identity.get('usuario_id')
    else:
        usuario_id = identity

    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        raw_token = auth_header.split(' ', 1)[1].strip()
    else:
        raw_token = request.get_json(silent=True) and request.get_json().get('refresh_token')

    if not raw_token:
        return jsonify({"ok": False, "error": "refresh_missing"}), 400

    token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    now = datetime.now(timezone.utc)
    existing = RefreshToken.query.filter_by(token_hash=token_hash).first()
    if not existing:
        return jsonify({"ok": False, "error": "refresh_not_found"}), 401
    if existing.revoked_at is not None:
        return jsonify({"ok": False, "error": "refresh_revoked"}), 401

    def _is_expired(dt):
        if dt is None:
            return False
        if dt.tzinfo is None:
            # Evitar datetime.utcnow() (deprecated), comparar con now UTC naive
            return dt < datetime.now(timezone.utc).replace(tzinfo=None)
        return dt < datetime.now(timezone.utc)

    if existing.expires_at and _is_expired(existing.expires_at):
        return jsonify({"ok": False, "error": "refresh_expired"}), 401

    # Rotación: crear nuevo refresh token y marcar anterior
    try:
        nuevo_refresh = create_refresh_token(identity=str(usuario_id), expires_delta=timedelta(days=7))
        nuevo_hash = hashlib.sha256(nuevo_refresh.encode('utf-8')).hexdigest()
        expires_at = now + timedelta(days=7)

        rt_new = RefreshToken(usuario_id=usuario_id, token_hash=nuevo_hash, expires_at=expires_at, ip=existing.ip, user_agent=existing.user_agent, device_id=existing.device_id)
        db.session.add(rt_new)

        existing.revoked_at = now
        existing.replaced_by_id = None
        db.session.add(existing)
        db.session.flush()
        existing.replaced_by_id = rt_new.id
        db.session.add(existing)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500

    usuario = db.session.get(Usuario, usuario_id)
    token_version = usuario.token_version if usuario else 0
    access_token = create_access_token(identity={"usuario_id": usuario_id, "token_version": token_version}, expires_delta=timedelta(minutes=15))

    return jsonify({"ok": True, "access_token": access_token, "refresh_token": nuevo_refresh}), 200


@login_bp.route('/logout', methods=['POST'])
@jwt_required(refresh=True)
def logout():
    try:
        identity = get_jwt_identity()
        usuario_id = identity if isinstance(identity, int) or isinstance(identity, str) else identity.get('usuario_id')

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

@login_bp.route('/unblock', methods=['POST'])
@jwt_required()
def unblock_user():
    """Desbloquear un usuario. Solo administradores pueden hacerlo.
    Al desbloquear se resetean los contadores y se establece la contraseña
    del usuario como su propio `nombre` (hasheada).
    Cuerpo JSON: { "email": "usuario@academia.com" }
    """
    try:
        identity = get_jwt_identity()
        caller_id = identity if isinstance(identity, int) or isinstance(identity, str) else identity.get('usuario_id')
        caller = db.session.get(Usuario, int(caller_id))
        if not caller:
            return jsonify({"ok": False, "error": "caller_not_found"}), 401

        # Comprobar rol de administrador (permitir Admin_plataforma y Admin_academia)
        rol = Rol.query.filter_by(id=caller.rol_id).first()
        if not rol or rol.nombre not in ('Admin_plataforma', 'Admin_academia'):
            return jsonify({"ok": False, "error": "forbidden"}), 403

        data = request.get_json() or {}
        email = data.get('email')
        if not email:
            return jsonify({"ok": False, "error": "email_required"}), 400

        usuario = Usuario.query.filter_by(email=email).first()
        if not usuario:
            return jsonify({"ok": False, "error": "user_not_found"}), 404

        if usuario.estado != 'Bloqueado':
            return jsonify({"ok": False, "error": "user_not_blocked"}), 400

        # Validar que el usuario autenticado no se desbloquee a sí mismo
        if caller.email == email:
            return jsonify({"ok": False, "error": "self_unblock_forbidden"}), 403

        # Validar roles y academias
        if rol.nombre == 'Admin_academia':
            # Validar desbloqueo por Admin_academia: solo su propia academia
            # Un Admin_academia solo puede desbloquear usuarios de su misma academia
            if usuario.academia_id != caller.academia_id:
                return jsonify({"ok": False, "error": "forbidden_academia_mismatch"}), 403
        elif rol.nombre == 'Admin_plataforma':
            # Un admin de la plataforma no puede desbloquearse a sí mismo si el objetivo es Admin_plataforma
            usuario_rol = Rol.query.filter_by(id=usuario.rol_id).first()
            if usuario_rol and usuario_rol.nombre == 'Admin_plataforma' and usuario.id == caller.id:
                return jsonify({"ok": False, "error": "forbidden"}), 403

        # Cambiar password a nombre del usuario (hasheada) y desbloquear
        try:
            new_plain = usuario.nombre
            usuario.password = hash_password(new_plain)
            usuario.estado = 'Activo'
            usuario.failed_login_count = 0
            usuario.last_failed_login_at = None
            usuario.locked_until = None
            # invalidar tokens: incrementar token_version
            usuario.token_version = (usuario.token_version or 0) + 1
            db.session.add(usuario)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({"ok": False, "error": "db_error"}), 500

        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": "unblock_error", "message": str(e)}), 500