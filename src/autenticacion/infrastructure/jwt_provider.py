from flask_jwt_extended import create_access_token, create_refresh_token
from datetime import timedelta
from typing import Dict

ACCESS_EXPIRES = timedelta(minutes=15)
REFRESH_EXPIRES = timedelta(days=7)


class JwtProvider:
    """Fachada para generar tokens. Centraliza la decisión sobre la forma
    de identidad (subject) que se incluye en los tokens.

    Actualmente: access token identity = dict {'usuario_id', 'token_version'}
    refresh token identity = str(usuario_id)
    """

    @staticmethod
    def create_access(usuario_id: int, token_version: int) -> str:
        identity = {"usuario_id": usuario_id, "token_version": token_version}
        return create_access_token(identity=identity, expires_delta=ACCESS_EXPIRES)

    @staticmethod
    def create_refresh(usuario_id: int) -> str:
        return create_refresh_token(identity=str(usuario_id), expires_delta=REFRESH_EXPIRES)
