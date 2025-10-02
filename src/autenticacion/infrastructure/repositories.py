from models import Usuario, RefreshToken, db
import hashlib
from datetime import datetime, timezone
from typing import Optional


class UserRepository:
    @staticmethod
    def get_by_email(email: str):
        return Usuario.query.filter_by(email=email).first()

    @staticmethod
    def get_by_id(uid: int):
        return db.session.get(Usuario, uid)

    @staticmethod
    def save(user: Usuario):
        db.session.add(user)
        db.session.commit()


class RefreshTokenRepository:
    @staticmethod
    def persist(raw_token: str, usuario_id: int, expires_at: datetime):
        # Validar valores antes de persistir
        if not usuario_id or not raw_token or not expires_at:
            raise ValueError("Valores inválidos para persistir RefreshToken")

        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        rt = RefreshToken(usuario_id=usuario_id, token_hash=token_hash, expires_at=expires_at)
        db.session.add(rt)
        db.session.commit()

    @staticmethod
    def find_by_hash(raw_token: str):
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        return RefreshToken.query.filter_by(token_hash=token_hash).first()
