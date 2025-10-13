import os
from flask import request, jsonify, Blueprint, g
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, create_access_token, create_refresh_token, jwt_required, get_jwt
from datetime import timedelta, datetime, timezone
import hashlib
from flask_sqlalchemy import SQLAlchemy
from src.usuarios.infrastructure.models import Usuario, RefreshToken, UserLoginLog
from src.shared.database import db
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
        # Validar valores antes de persistir
        if not usuario_id or not token_hash or not expires_at:
            raise ValueError("Valores inválidos para persistir RefreshToken")
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
    """Función para usar en before_request y proteger toda la API salvo rutas públicas.
    Esta versión incluye diagnostics detallados (no rompe la verificación normal).
    """
    raw_path = request.path.rstrip('/') or '/'  # Normalize path by removing trailing slashes
    print(f"[DEBUG][AUTH] Verificando ruta: {raw_path}", flush=True)
    print(f"[DEBUG][AUTH] Rutas públicas configuradas: {PUBLIC_PATHS}", flush=True)

    if raw_path in PUBLIC_PATHS:
        print(f"[DEBUG][AUTH] Ruta pública detectada: {raw_path}", flush=True)
        return None

    # Diagnostics: inspect header and token parts (best-effort, non-fatal)
    try:
        auth_header = request.headers.get('Authorization', '')
        print(f"[AUTH-DEBUG] Authorization header: {auth_header}", flush=True)
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]
            try:
                parts = token.split('.')
                if len(parts) == 3:
                    header_b64, payload_b64, sig_b64 = parts
                    print(f"[AUTH-DEBUG] token_header_b64={header_b64}", flush=True)
                    print(f"[AUTH-DEBUG] token_payload_b64={payload_b64}", flush=True)
                    print(f"[AUTH-DEBUG] token_signature_b64={sig_b64}", flush=True)
                    try:
                        import base64
                        def b64url_decode(s):
                            rem = len(s) % 4
                            if rem > 0:
                                s = s + ('=' * (4 - rem))
                            return base64.urlsafe_b64decode(s.encode('utf-8'))
                        try:
                            header_json = b64url_decode(header_b64).decode('utf-8')
                            payload_json = b64url_decode(payload_b64).decode('utf-8')
                            print(f"[AUTH-DEBUG] token_header_json={header_json}", flush=True)
                            print(f"[AUTH-DEBUG] token_payload_json={payload_json}", flush=True)
                        except Exception as de:
                            print(f"[AUTH-DEBUG] Failed to base64url-decode token parts: {de}", flush=True)
                    except Exception:
                        pass
                else:
                    print(f"[AUTH-DEBUG] Unexpected token parts count={len(parts)}", flush=True)
            except Exception:
                pass

            try:
                import hashlib, os
                tok_sha = hashlib.sha256(token.encode('utf-8')).hexdigest()
                print(f"[AUTH-DEBUG] token_sha256={tok_sha}", flush=True)
                primary = os.getenv('JWT_SECRET_KEY')
                delegated = os.getenv('JWT_DELEGATION_SECRET')
                try:
                    if primary:
                        print(f"[AUTH-DEBUG] JWT_SECRET_KEY (sha256_prefix)={hashlib.sha256(primary.encode()).hexdigest()[:8]} len={len(primary)}", flush=True)
                    else:
                        print(f"[AUTH-DEBUG] JWT_SECRET_KEY=<null>", flush=True)
                except Exception:
                    print(f"[AUTH-DEBUG] JWT_SECRET_KEY=<err>", flush=True)
                try:
                    if delegated:
                        print(f"[AUTH-DEBUG] JWT_DELEGATION_SECRET (sha256_prefix)={hashlib.sha256(delegated.encode()).hexdigest()[:8]} len={len(delegated)}", flush=True)
                    else:
                        print(f"[AUTH-DEBUG] JWT_DELEGATION_SECRET=<null>", flush=True)
                except Exception:
                    print(f"[AUTH-DEBUG] JWT_DELEGATION_SECRET=<err>", flush=True)

                # Try decode with both secrets (non-fatal) to capture detailed errors
                try:
                    import jwt as pyjwt
                    for sname, s in (('primary', primary), ('delegation', delegated)):
                        if not s:
                            print(f"[AUTH-DEBUG] {sname} secret missing", flush=True)
                            continue
                        try:
                            decoded = pyjwt.decode(token, s, algorithms=['HS256'], options={"verify_aud": False})
                            print(f"[AUTH-DEBUG] Decoded as {sname}: {decoded}", flush=True)
                        except Exception as e:
                            print(f"[AUTH-DEBUG] Failed decode as {sname}: {e}", flush=True)
                except Exception:
                    pass
            except Exception:
                pass
    except Exception:
        # Never let diagnostics break request handling
        pass

    # Before calling the framework verifier, accept delegated tokens signed with a different secret
    try:
        # we already computed token above in diagnostics block; recompute safely
        auth_header = request.headers.get('Authorization', '')
        token = None
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]

        delegated = os.getenv('JWT_DELEGATION_SECRET')
        if token and delegated:
            try:
                import jwt as pyjwt
                decoded_deleg = pyjwt.decode(token, delegated, algorithms=['HS256'], options={"verify_aud": False})
                # Only accept delegated tokens that clearly come from the mediator
                actor = decoded_deleg.get('actor')
                if actor == 'chat-backend':
                    # mark delegated payload for downstream handlers/tests and allow request
                    g.delegated_jwt = decoded_deleg
                    print(f"[DEBUG][AUTH] Accepted delegated token (actor={actor}); allowing request", flush=True)
                    return None
                else:
                    print(f"[DEBUG][AUTH] Delegated token actor mismatch: {actor}", flush=True)
            except Exception as e:
                # not a delegated token or signature invalid; continue to primary verification
                print(f"[DEBUG][AUTH] Delegated decode attempt failed: {e}", flush=True)

    except Exception:
        pass

    # Now perform the normal verification (this is the actual enforcement)
    try:
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
