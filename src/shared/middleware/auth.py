from functools import wraps
from flask import g, jsonify, request, current_app
from src.autenticacion.infrastructure.repositories import UserRepository
from config import Config
import json
import os
import jwt
import logging
import hashlib

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def require_auth(fn):
    """Decorator that requires a valid access token and loads the current user
    into flask.g.current_user. Returns 401 when token is invalid or user not found.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        print("[DEBUG] Middleware 'require_auth' ejecutado", flush=True)
        logger.debug("Middleware 'require_auth' started execution.")
        # Dump relevant env vars for debugging at the beginning of auth middleware
        try:
            dump_keys = ['JWT_SECRET_KEY', 'JWT_DELEGATION_SECRET', 'APP_ENV', 'FLASK_DEBUG', 'DEBUG']
            print("[AUTH-DEBUG] Environment snapshot (masked prefixes):", flush=True)
            for k in dump_keys:
                v = os.getenv(k)
                try:
                    if v is None:
                        print(f"[AUTH-DEBUG] {k}=<null>", flush=True)
                    elif v == "":
                        print(f"[AUTH-DEBUG] {k}=<blank>", flush=True)
                    else:
                        # mask but show prefix
                        show = v if len(v) <= 8 else (v[:8] + '...')
                        print(f"[AUTH-DEBUG] {k}={show} (len={len(v)})", flush=True)
                except Exception:
                    print(f"[AUTH-DEBUG] {k}=<error>", flush=True)
        except Exception:
            pass
        auth_header = request.headers.get('Authorization', '')
        logger.debug(f"Authorization header: {auth_header}")

        if not auth_header.startswith('Bearer '):
            logger.debug("Authorization header missing or invalid format.")
            return jsonify({"ok": False, "error": "missing_or_invalid_auth_header"}), 401

        token = auth_header.split(' ')[1]
        logger.debug(f"Extracted token: {token}")

        try:
            # Log the secret keys for debugging
            original_secret = os.getenv('JWT_SECRET_KEY', 'missing')
            delegated_secret = os.getenv('JWT_DELEGATION_SECRET', 'missing')
            # print hashes and lengths (safe non-reversible info)
            try:
                print(f"[DEBUG] JWT_SECRET_KEY (sha256_prefix)={hashlib.sha256(original_secret.encode()).hexdigest()[:8]} len={len(original_secret)}", flush=True)
            except Exception:
                print("[DEBUG] JWT_SECRET_KEY (sha256_prefix)=<err>", flush=True)
            try:
                print(f"[DEBUG] JWT_DELEGATION_SECRET (sha256_prefix)={hashlib.sha256(delegated_secret.encode()).hexdigest()[:8]} len={len(delegated_secret)}", flush=True)
            except Exception:
                print("[DEBUG] JWT_DELEGATION_SECRET (sha256_prefix)=<err>", flush=True)

            # Diagnostic: print token parts (base64url) and unverified header/payload
            try:
                parts = token.split('.')
                if len(parts) == 3:
                    header_b64, payload_b64, sig_b64 = parts
                    print(f"[DEBUG] token_header_b64={header_b64}", flush=True)
                    print(f"[DEBUG] token_payload_b64={payload_b64}", flush=True)
                    print(f"[DEBUG] token_signature_b64={sig_b64}", flush=True)
                    try:
                        import base64
                        def b64url_decode(s):
                            # Add padding
                            rem = len(s) % 4
                            if rem > 0:
                                s = s + ('=' * (4 - rem))
                            return base64.urlsafe_b64decode(s.encode('utf-8'))
                        header_json = b64url_decode(header_b64).decode('utf-8')
                        payload_json = b64url_decode(payload_b64).decode('utf-8')
                        print(f"[DEBUG] token_header_json={header_json}", flush=True)
                        print(f"[DEBUG] token_payload_json={payload_json}", flush=True)
                    except Exception as de:
                        print(f"[DEBUG] Failed to base64url-decode token parts: {de}", flush=True)
                else:
                    print(f"[DEBUG] Unexpected token parts count={len(parts)}", flush=True)
            except Exception:
                pass

            # full token sha256 hex for correlation
            try:
                tok_sha = hashlib.sha256(token.encode('utf-8')).hexdigest()
                print(f"[DEBUG] token_sha256={tok_sha}", flush=True)
            except Exception:
                pass

            # Attempt to decode as original token
            try:
                decoded_token = jwt.decode(token, original_secret, algorithms=['HS256'])
                print(f"[DEBUG] Decoded as original token: {decoded_token}", flush=True)
            except jwt.InvalidTokenError as e:
                print(f"[DEBUG] Failed to decode as original token: {e}", flush=True)

                # Attempt to decode as delegated token
                try:
                    decoded_token = jwt.decode(token, delegated_secret, algorithms=['HS256'])
                    print(f"[DEBUG] Decoded as delegated token: {decoded_token}", flush=True)
                except jwt.InvalidTokenError as e:
                    # On delegated decode failure, print detailed diagnostics to help correlate with mediator logs
                    try:
                        print(f"[DEBUG] Failed to decode as delegated token: {e}", flush=True)
                        print(f"[DEBUG-DETAILS] Token (first64)={token[:64]}", flush=True)
                        print(f"[DEBUG-DETAILS] JWT_SECRET_KEY (masked)={('<null>' if original_secret is None else (original_secret[:8]+'...'))}", flush=True)
                        print(f"[DEBUG-DETAILS] JWT_DELEGATION_SECRET (masked)={('<null>' if delegated_secret is None else (delegated_secret[:8]+'...'))}", flush=True)
                        import traceback
                        traceback.print_exc()
                    except Exception:
                        pass
                    raise
        except Exception as e:
            print(f"[DEBUG] Token validation failed: {e}", flush=True)
            return jsonify({"ok": False, "error": "invalid_token"}), 401

        # compute short sha for correlation with mediator logs
        try:
            token_sha = hashlib.sha256(token.encode('utf-8')).digest()
            token_sha4 = ''.join(f"{b:02x}" for b in token_sha[:4])
            if Config.DEBUG:
                print(f"[DEBUG] Received token (masked)={token[:8]}..., token_sha4={token_sha4}")
        except Exception:
            token_sha4 = None

        payload = None
        tried = []
        # Order: primary app secret, then delegation secret
        secrets = [os.getenv('JWT_SECRET_KEY'), os.getenv('JWT_DELEGATION_SECRET')]
        for s in secrets:
            if not s:
                tried.append(None)
                continue
            try:
                # Decode without verifying audience; require HS256
                payload = jwt.decode(token, s, algorithms=['HS256'], options={"verify_aud": False})
                if Config.DEBUG:
                    print(f"[DEBUG] Token verificado correctamente con secret (prefix): {s[:4]}...; token_sha4={token_sha4}")
                break
            except Exception as e:
                tried.append(str(e))
                if Config.DEBUG:
                    print(f"[DEBUG] Falló verificación con secret (prefix): {None if not s else s[:4]}..., error: {e}; token_sha4={token_sha4}")
                payload = None
                continue

        if payload is None:
            # Emit extensive diagnostic info when verification fails
            try:
                print(f"[DEBUG] Token inválido. Intentos: {tried}", flush=True)
                # Show which secrets were present and their sha prefixes
                primary = os.getenv('JWT_SECRET_KEY')
                delegated = os.getenv('JWT_DELEGATION_SECRET')
                import hashlib
                if primary:
                    print(f"[DEBUG] Primary secret sha256_prefix={hashlib.sha256(primary.encode()).hexdigest()[:8]} len={len(primary)}", flush=True)
                else:
                    print("[DEBUG] Primary secret=<null>", flush=True)
                if delegated:
                    print(f"[DEBUG] Delegation secret sha256_prefix={hashlib.sha256(delegated.encode()).hexdigest()[:8]} len={len(delegated)}", flush=True)
                else:
                    print("[DEBUG] Delegation secret=<null>", flush=True)
                print(f"[DEBUG] Received token (masked)={token[:8]}... token_len={len(token)}", flush=True)
            except Exception:
                pass
            return jsonify({"ok": False, "error": "invalid_token"}), 401

        if Config.DEBUG:
            print(f"[DEBUG] Payload extraído del token: {payload}; token_sha4={token_sha4}")

        # Determine whether the token was validated with the delegation secret
        # Re-run the verification loop to detect which secret validated it (primary or delegation)
        used_delegation = False
        try:
            primary = os.getenv('JWT_SECRET_KEY')
            delegated = os.getenv('JWT_DELEGATION_SECRET')
            # Find which secret decodes the payload (we already decoded earlier, so check signature validation)
            for sname, s in (('primary', primary), ('delegation', delegated)):
                if not s:
                    continue
                try:
                    jwt.decode(token, s, algorithms=['HS256'], options={"verify_aud": False})
                    if sname == 'delegation':
                        used_delegation = True
                    break
                except Exception:
                    continue
        except Exception:
            # ignore and fallback to payload inspection
            used_delegation = False

        if Config.DEBUG:
            print(f"[DEBUG] used_delegation={used_delegation}; payload keys={list(payload.keys()) if isinstance(payload, dict) else None}")

        try:
            identity = build_identity_from_payload(payload, used_delegation)
            if Config.DEBUG:
                print(f"[DEBUG] Identity built from payload: {identity}")
        except ValueError as e:
            if Config.DEBUG:
                print(f"[DEBUG] Identidad inválida o faltan campos requeridos en el token: {e}")
            return jsonify({"ok": False, "error": "invalid_identity"}), 401

        # Load user from database
        user = UserRepository.get_by_id(identity['usuario_id'])
        if not user:
            print(f"[DEBUG] Usuario no encontrado para ID: {identity['usuario_id']}")
            return jsonify({"ok": False, "error": "user_not_found"}), 401

        # Check token version
        if user.token_version != identity.get('token_version', 0):
            print(f"[DEBUG] Versión del token no coincide para el usuario ID: {user.id}")
            return jsonify({"ok": False, "error": "token_version_mismatch"}), 401

        # Attach user to global context
        g.current_user = user
        if Config.DEBUG:
            print(f"[DEBUG] Usuario autenticado: {user.id}, email: {user.email}")

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


def build_identity_from_payload(payload: dict, is_delegated: bool):
    """Return identity dict {'usuario_id': int, 'token_version': int|None} or raise ValueError"""
    if not isinstance(payload, dict):
        raise ValueError('payload_not_dict')
    sub = payload.get('sub')
    token_version = payload.get('token_version')

    # If sub is a JSON string, prefer it
    if isinstance(sub, str) and sub.strip().startswith('{'):
        try:
            parsed = json.loads(sub)
            usuario_id = parsed.get('usuario_id')
            if usuario_id is None:
                raise ValueError('missing_usuario_id')
            # token_version may be inside subject or at top-level
            tv = parsed.get('token_version', token_version)
            return {'usuario_id': int(usuario_id), 'token_version': (int(tv) if tv is not None else None)}
        except Exception as e:
            # fall through to try numeric parsing
            if Config.DEBUG:
                print(f"[DEBUG] Failed parsing sub JSON: {e}")

    # If delegated, accept numeric subject (legacy tokens)
    if is_delegated and (isinstance(sub, (int,)) or (isinstance(sub, str) and str(sub).isdigit())):
        try:
            uid = int(sub)
            tv = token_version
            # log when token_version missing on delegated token
            if tv is None and Config.DEBUG:
                print(f"[DEBUG] Delegated token for usuario_id={uid} missing token_version; treating as None (consider migrating mediator to include token_version)")
            return {'usuario_id': uid, 'token_version': (int(tv) if tv is not None else None)}
        except Exception:
            raise ValueError('invalid_numeric_sub')

    # Non-delegated path: require sub to be JSON with usuario_id and token_version
    if isinstance(sub, str) and sub.strip().startswith('{'):
        try:
            parsed = json.loads(sub)
            usuario_id = parsed.get('usuario_id')
            token_version = parsed.get('token_version')
            if usuario_id is None or token_version is None:
                raise ValueError('missing_fields')
            return {'usuario_id': int(usuario_id), 'token_version': int(token_version)}
        except Exception:
            raise ValueError('invalid_sub_json')

    raise ValueError('invalid_identity_format')
