from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, ValidationError
from src.autenticacion.application.services import AuthService
from src.autenticacion.infrastructure.jwt_provider import JwtProvider
from flask_jwt_extended import jwt_required, get_jwt_identity, create_refresh_token, create_access_token
from src.usuarios.infrastructure.models import RefreshToken, Usuario, UserLoginLog, Rol
from src.shared.database import db
from src.shared.security import hash_password
import hashlib
from datetime import datetime, timezone, timedelta
from src.autenticacion.application.dtos import LoginRequestDTO
from src.autenticacion.domain.exceptions import UsuarioBloqueadoException, CredencialesInvalidasException

login_bp = Blueprint('login_bp', __name__)


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)


@login_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json() or {}
        schema = LoginSchema()
        validated = schema.load(data)
        request_dto = LoginRequestDTO(email=validated['email'], password=validated['password'])

        # Delegar la lógica al servicio de aplicación
        response_dto = AuthService.login(request_dto)
        return jsonify({
            "ok": response_dto.ok,
            "tokens": response_dto.tokens,
            "role": response_dto.role,
            "name": response_dto.name
        }), response_dto.status

    except ValidationError as e:
        return jsonify({"ok": False, "error": e.messages}), 400
    except UsuarioBloqueadoException as e:
        return jsonify({"ok": False, "error": str(e)}), 403
    except CredencialesInvalidasException as e:
        return jsonify({"ok": False, "error": str(e)}), 401


@login_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_tokens():
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
            return dt < datetime.now(timezone.utc).replace(tzinfo=None)
        return dt < datetime.now(timezone.utc)

    if existing.expires_at and _is_expired(existing.expires_at):
        return jsonify({"ok": False, "error": "refresh_expired"}), 401

    # Rotación: crear nuevo refresh token y marcar anterior
    try:
        nuevo_refresh = create_refresh_token(identity=str(usuario_id), expires_delta=timedelta(days=7))
        nuevo_hash = hashlib.sha256(nuevo_refresh.encode('utf-8')).hexdigest()
        expires_at = now + timedelta(days=7)

        # Validar valores antes de persistir
        if not usuario_id or not nuevo_hash or not expires_at:
            raise ValueError("Valores inválidos para persistir RefreshToken")

        # Crear nuevo RefreshToken y persistir
        rt_new = RefreshToken(usuario_id=usuario_id, token_hash=nuevo_hash, expires_at=expires_at, ip=existing.ip, user_agent=existing.user_agent, device_id=existing.device_id)
        db.session.add(rt_new)
        # Flush to obtain rt_new.id without committing yet
        db.session.flush()

        # Mark existing as revoked and link to new token atomically
        existing.revoked_at = now
        existing.replaced_by_id = rt_new.id
        db.session.add(existing)

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500

    usuario = db.session.get(Usuario, usuario_id)
    token_version = usuario.token_version if usuario else 0
    roles = [usuario.rol.nombre] if usuario and usuario.rol else []
    academia_id = usuario.academia_id if usuario else None
    access_token = JwtProvider.create_access(usuario_id, token_version, roles=roles, academia_id=academia_id)

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

        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": "logout_error", "message": str(e)}), 500


@login_bp.route('/unblock', methods=['POST'])
@jwt_required()
def unblock_user():
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
            if usuario.academia_id != caller.academia_id:
                return jsonify({"ok": False, "error": "forbidden_academia_mismatch"}), 403
        elif rol.nombre == 'Admin_plataforma':
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
            usuario.token_version = (usuario.token_version or 0) + 1
            db.session.add(usuario)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({"ok": False, "error": "db_error"}), 500

        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": "unblock_error", "message": str(e)}), 500
