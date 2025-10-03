from functools import wraps
from flask import g, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.autenticacion.infrastructure.repositories import UserRepository
from config import Config
import json


def require_auth(fn):
    """Decorator that requires a valid access token and loads the current user
    into flask.g.current_user. Returns 401 when token is invalid or user not found.
    """

    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if Config.DEBUG:
            print(f"[DEBUG] Validando token JWT")
        identity = get_jwt_identity()
        if Config.DEBUG:
            print(f"[DEBUG] Identidad extraída del token: {identity}")

        # Deserializar identidad si es una cadena JSON
        if isinstance(identity, str):
            try:
                identity = json.loads(identity)
                if Config.DEBUG:
                    print(f"[DEBUG] Identidad deserializada: {identity}")
            except json.JSONDecodeError:
                return jsonify({"ok": False, "error": "invalid_token_identity_format"}), 401

        # identity is expected to be a dict {'usuario_id': <id>, 'token_version': <v>}.
        usuario_id = None
        if isinstance(identity, dict):
            usuario_id = identity.get('usuario_id')
        elif isinstance(identity, int):
            usuario_id = identity
        elif isinstance(identity, str) and identity.isdigit():
            usuario_id = int(identity)

        if not usuario_id:
            return jsonify({"ok": False, "error": "invalid_token_identity"}), 401

        user = UserRepository.get_by_id(int(usuario_id))
        if not user:
            if Config.DEBUG:
                print(f"[DEBUG] Usuario no encontrado para ID: {usuario_id}")
            return jsonify({"ok": False, "error": "user_not_found"}), 401

        if Config.DEBUG:
            print(f"[DEBUG] Usuario cargado: {user.id}, Rol: {user.rol.nombre if user.rol else 'Sin rol'}")

        # Optional: validate token_version to support token invalidation on rotation
        try:
            token_version_in_token = None
            if isinstance(identity, dict):
                token_version_in_token = identity.get('token_version')
            # If token_version exists in the token, compare; otherwise allow (backwards compatible)
            if token_version_in_token is not None:
                # Ensure both are ints for safe comparison
                try:
                    tv_token = int(token_version_in_token)
                except Exception:
                    return jsonify({"ok": False, "error": "invalid_token_version_format"}), 401

                user_token_version = int(getattr(user, 'token_version', 0) or 0)
                if tv_token != user_token_version:
                    if Config.DEBUG:
                        print("[DEBUG] Versión del token no válida")
                    return jsonify({"ok": False, "error": "invalid_token_version"}), 401
        except Exception as e:
            if Config.DEBUG:
                print(f"[DEBUG] Error al validar la versión del token: {e}")
            # Fail safe: if something goes wrong validating token_version, treat as invalid
            return jsonify({"ok": False, "error": "invalid_token"}), 401

        # Attach to flask.g for handlers
        g.current_user = user
        if Config.DEBUG:
            print(f"[DEBUG] Usuario asignado a g.current_user: {g.current_user}")
        return fn(*args, **kwargs)

    # Mark the wrapper so other tools (like OpenAPI generator) can detect
    # that this view requires authentication.
    try:
        wrapper._requires_auth = True
    except Exception:
        pass

    return wrapper


def require_role(role_name: str):
    """Decorator factory to require a specific role name on the authenticated user.

    Usage:
        @require_role('Admin_plataforma')
        def endpoint(...):
            ...
    """

    def decorator(fn):
        @wraps(fn)
        @require_auth
        def wrapper(*args, **kwargs):
            user = getattr(g, 'current_user', None)
            user_role = None
            try:
                user_role = user.rol.nombre if user and user.rol else None
            except Exception as e:
                if Config.DEBUG:
                    print(f"[DEBUG] Error al obtener el rol del usuario: {e}")
                user_role = None

            if Config.DEBUG:
                print(f"[DEBUG] Usuario autenticado: {user}")
                print(f"[DEBUG] Rol del usuario: {user_role}, Rol requerido: {role_name}")

            if user_role != role_name:
                if Config.DEBUG:
                    print(f"[DEBUG] Devolviendo 403 Forbidden desde require_role")
                return jsonify({"ok": False, "error": "forbidden"}), 403

            return fn(*args, **kwargs)
        # Mark this wrapper as requiring auth as well (helpful if introspected)
        try:
            wrapper._requires_auth = True
        except Exception:
            pass

        return wrapper

    return decorator
