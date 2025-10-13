from flask_jwt_extended import create_access_token, create_refresh_token
from datetime import timedelta
from typing import Dict, Optional, List
import json
import os
import hashlib

ACCESS_EXPIRES = timedelta(minutes=15)
REFRESH_EXPIRES = timedelta(days=7)


class JwtProvider:
    """Fachada para generar tokens. Centraliza la decisión sobre la forma
    de identidad (subject) que se incluye en los tokens.

    Actualmente: access token identity = dict {'usuario_id', 'token_version'}
    refresh token identity = str(usuario_id)
    """

    @staticmethod
    def create_access(usuario_id: int,
                      token_version: int,
                      roles: Optional[List[str]] = None,
                      academia_id: Optional[int] = None,
                      profesor_id: Optional[int] = None) -> str:
        """Genera un access token incluyendo claims adicionales opcionales.

        identity: se serializa como JSON para mantener compatibilidad con
        el código existente que espera una cadena en get_jwt_identity().
        additional_claims: usados para roles, academia_id, profesor_id, etc.
        """
        identity = {"usuario_id": usuario_id, "token_version": token_version}
        additional_claims: Dict = {}
        if roles:
            # normalizar a lista de strings
            additional_claims['roles'] = roles if isinstance(roles, list) else [roles]
        if academia_id is not None:
            try:
                additional_claims['academia_id'] = int(academia_id)
            except Exception:
                additional_claims['academia_id'] = academia_id
        if profesor_id is not None:
            try:
                additional_claims['profesor_id'] = int(profesor_id)
            except Exception:
                additional_claims['profesor_id'] = profesor_id

        token = create_access_token(identity=json.dumps(identity), additional_claims=additional_claims or None, expires_delta=ACCESS_EXPIRES)
        # Log a short SHA-256 prefix when DEBUG is enabled so tests and runtime can audit token fingerprints
        try:
            if os.getenv('DEBUG', '0').lower() in ('1', 'true', 'yes'):
                h = hashlib.sha256(token.encode('utf-8')).digest()
                short = ''.join(f"{b:02x}" for b in h[:4])
                print(f"[DEBUG] Generated access token SHA256 prefix: {short}")
        except Exception:
            pass
        return token

    @staticmethod
    def create_access_with_log(usuario_id: int,
                      token_version: int,
                      roles: Optional[List[str]] = None,
                      academia_id: Optional[int] = None,
                      profesor_id: Optional[int] = None) -> str:
        """Compatibility wrapper that logs a short SHA-256 prefix of the generated token when DEBUG is enabled."""
        token = JwtProvider.create_access(usuario_id, token_version, roles=roles, academia_id=academia_id, profesor_id=profesor_id)
        try:
            if os.getenv('DEBUG', '0').lower() in ('1', 'true', 'yes'):
                h = hashlib.sha256(token.encode('utf-8')).digest()
                short = ''.join(f"{b:02x}" for b in h[:4])
                print(f"[DEBUG] Generated access token SHA256 prefix: {short}")
        except Exception:
            pass
        return token

    @staticmethod
    def create_refresh(usuario_id: int) -> str:
        return create_refresh_token(identity=str(usuario_id), expires_delta=REFRESH_EXPIRES)
