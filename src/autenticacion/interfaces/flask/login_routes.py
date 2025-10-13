from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, ValidationError
from src.autenticacion.application.services import AuthService
from src.autenticacion.infrastructure.jwt_provider import JwtProvider
from flask_jwt_extended import jwt_required, get_jwt_identity, create_refresh_token, create_access_token, decode_token
from src.usuarios.infrastructure.models import RefreshToken, Usuario, UserLoginLog, Rol
from src.shared.database import db
from src.shared.security import hash_password
import hashlib
from datetime import datetime, timezone, timedelta
from src.autenticacion.application.dtos import LoginRequestDTO
from src.autenticacion.domain.exceptions import UsuarioBloqueadoException, CredencialesInvalidasException
import json

login_bp = Blueprint('login_bp', __name__)
from src.shared.docs.operation_id import operation_id
from src.shared.docs.openapi_request_body import openapi_request_body


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)


@login_bp.route('/login', methods=['POST'])
@operation_id('login.login')
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
@operation_id('login.refresh_tokens')
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
@operation_id('login.logout')
# Document that this endpoint accepts a JSON body with the refresh_token or a
# refresh token via the Authorization header. The implementation prefers a
# body refresh_token when both are provided (this precedence is enforced by
# the handler logic).
@openapi_request_body('RefreshRequest')
def logout():
    try:
        # Allow passing the refresh token either via Authorization header or in the JSON body.
        # If the Authorization header contains an access token but the body contains a refresh token,
        # prefer the body refresh token so clients can send both.
        auth_header = request.headers.get('Authorization', '')
        header_token = None
        if auth_header.startswith('Bearer '):
            header_token = auth_header.split(' ', 1)[1].strip()
        body_token = request.get_json(silent=True) and request.get_json().get('refresh_token')

        raw_token = None
        decoded = None

        if header_token:
            # Try to decode header token first; if it's a refresh token we'll use it.
            try:
                decoded_header = decode_token(header_token)
                header_type = decoded_header.get('type') or decoded_header.get('token_type')
                if header_type == 'refresh':
                    raw_token = header_token
                    decoded = decoded_header
                else:
                    # Header contains non-refresh (probably access token). Prefer body token if present.
                    if body_token:
                        raw_token = body_token
                    else:
                        return jsonify({"msg": "Only refresh tokens are allowed"}), 422
            except Exception:
                # Header token invalid; fall back to body token if present
                if body_token:
                    raw_token = body_token
                else:
                    return jsonify({"ok": False, "error": "invalid_token", "message": "invalid header token"}), 401
        else:
            raw_token = body_token

        if not raw_token:
            return jsonify({"ok": False, "error": "refresh_missing"}), 400

        # Decode the chosen token if not already decoded
        if decoded is None:
            try:
                decoded = decode_token(raw_token)
            except Exception as e:
                return jsonify({"ok": False, "error": "invalid_token", "message": str(e)}), 401

        # Ensure token is a refresh token
        token_type = decoded.get('type') or decoded.get('token_type')
        if token_type != 'refresh':
            return jsonify({"msg": "Only refresh tokens are allowed"}), 422

        # Extract identity from decoded token
        sub = decoded.get('sub') if 'sub' in decoded else decoded.get('identity')
        usuario_id = None
        try:
            import json as _json
            if isinstance(sub, str):
                # sometimes identity is serialized json string
                try:
                    parsed = _json.loads(sub)
                    if isinstance(parsed, dict):
                        usuario_id = parsed.get('usuario_id') or parsed.get('user_id')
                    else:
                        usuario_id = int(parsed) if str(parsed).isdigit() else parsed
                except Exception:
                    usuario_id = int(sub) if sub.isdigit() else sub
            elif isinstance(sub, dict):
                usuario_id = sub.get('usuario_id') or sub.get('user_id')
            else:
                usuario_id = sub
        except Exception:
            usuario_id = sub

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
@operation_id('login.unblock_user')
def unblock_user():
    try:
        identity = get_jwt_identity()
        # Adjusted to handle JSON string identities
        if isinstance(identity, str):
            try:
                identity = json.loads(identity)  # Convert JSON string to dict
            except json.JSONDecodeError:
                print(f"[DEBUG][UNBLOCK] Failed to decode JWT identity JSON: {identity}")
                return jsonify({"ok": False, "error": "invalid_identity_format"}), 401

        if isinstance(identity, dict):
            caller_id = identity.get('usuario_id')
        elif isinstance(identity, (int, str)):
            caller_id = identity
        else:
            print(f"[DEBUG][UNBLOCK] Invalid JWT identity format: {identity}")
            return jsonify({"ok": False, "error": "invalid_identity"}), 401

        caller = db.session.get(Usuario, int(caller_id))
        if not caller:
            print("[DEBUG][UNBLOCK] Caller not found in database.")
            return jsonify({"ok": False, "error": "caller_not_found"}), 401

        print(f"[DEBUG][UNBLOCK] Caller found: {caller.email}, Rol: {caller.rol_id}")

        # Comprobar rol de administrador (permitir Admin_plataforma y Admin_academia)
        rol = Rol.query.filter_by(id=caller.rol_id).first()
        if not rol or rol.nombre not in ('Admin_plataforma', 'Admin_academia'):
            print(f"[DEBUG][UNBLOCK] Caller role invalid or unauthorized: {rol.nombre if rol else 'None'}")
            return jsonify({"ok": False, "error": "forbidden"}), 403

        data = request.get_json() or {}
        email = data.get('email')
        if not email:
            print("[DEBUG][UNBLOCK] Email not provided in request.")
            return jsonify({"ok": False, "error": "email_required"}), 400

        usuario = Usuario.query.filter_by(email=email).first()
        if not usuario:
            print(f"[DEBUG][UNBLOCK] Target user not found: {email}")
            return jsonify({"ok": False, "error": "user_not_found"}), 404

        print(f"[DEBUG][UNBLOCK] Target user found: {usuario.email}, Estado: {usuario.estado}")

        if usuario.estado != 'Bloqueado':
            print(f"[DEBUG][UNBLOCK] Target user is not blocked: {usuario.estado}")
            return jsonify({"ok": False, "error": "user_not_blocked"}), 400

        # Validar que el usuario autenticado no se desbloquee a sí mismo
        if caller.email == email:
            print("[DEBUG][UNBLOCK] Caller attempted to unblock themselves.")
            return jsonify({"ok": False, "error": "self_unblock_forbidden"}), 403

        # Validar roles y academias
        if rol.nombre == 'Admin_academia':
            if usuario.academia_id != caller.academia_id:
                print(f"[DEBUG][UNBLOCK] Academia mismatch: Caller ({caller.academia_id}), Target ({usuario.academia_id})")
                return jsonify({"ok": False, "error": "forbidden_academia_mismatch"}), 403
        elif rol.nombre == 'Admin_plataforma':
            usuario_rol = Rol.query.filter_by(id=usuario.rol_id).first()
            if usuario_rol and usuario_rol.nombre == 'Admin_plataforma' and usuario.id == caller.id:
                print("[DEBUG][UNBLOCK] Admin_plataforma attempted to unblock another Admin_plataforma.")
                return jsonify({"ok": False, "error": "forbidden"}), 403

        # Log the current state of the target user before updating
        print(f"[DEBUG][UNBLOCK] Target user before update: Email={usuario.email}, Estado={usuario.estado}, Password={usuario.password}")

        # Only update the user's state to 'Activo' without changing the password
        try:
            usuario.estado = 'Activo'
            usuario.failed_login_count = 0
            usuario.last_failed_login_at = None
            usuario.locked_until = None
            usuario.token_version = (usuario.token_version or 0) + 1
            db.session.add(usuario)
            db.session.commit()

            # Log the updated state of the target user
            print(f"[DEBUG][UNBLOCK] Target user after update: Email={usuario.email}, Estado={usuario.estado}, Password={usuario.password}")
        except Exception as e:
            db.session.rollback()
            print(f"[DEBUG][UNBLOCK] Database error while unblocking user: {e}")
            return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500

        return jsonify({"ok": True}), 200
    except Exception as e:
        print(f"[DEBUG][UNBLOCK] Unexpected error: {e}")
        return jsonify({"ok": False, "error": "unblock_error", "message": str(e)}), 500



