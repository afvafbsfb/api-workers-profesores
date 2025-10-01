from typing import Tuple, Dict
from src.autenticacion.infrastructure.repositories import UserRepository, RefreshTokenRepository
from models import UserLoginLog, db
from src.autenticacion.infrastructure.hasher import Hasher
from src.autenticacion.infrastructure.jwt_provider import JwtProvider
from datetime import datetime, timezone, timedelta
import hashlib


class AuthService:
    """Servicio de aplicación que agrupa las operaciones de autenticación.

    Por ahora implementa login de forma similar a la lógica existente en
    src/usuarios/login_routes.py, pero delegando persistencia y hashing a
    los adaptadores.
    """

    @staticmethod
    def login(email: str, password: str) -> Tuple[bool, Dict]:
        user = UserRepository.get_by_email(email)
        if not user:
            return False, {"error": "credenciales inválidas"}

        now = datetime.now(timezone.utc)

        # comprobar bloqueo temporal: puede venir almacenado como naive -> normalizar a UTC
        locked_until = user.locked_until
        if locked_until is not None:
            # si es naive, asumir UTC
            if locked_until.tzinfo is None or locked_until.tzinfo.utcoffset(locked_until) is None:
                # convertir a aware UTC
                locked_until = locked_until.replace(tzinfo=timezone.utc)

        if locked_until and locked_until > now:
            # registrar intento de login fallido por bloqueo
            try:
                ull = UserLoginLog(usuario_id=user.id, success=False, fail_reason='LOCKED')
                db.session.add(ull)
                db.session.commit()
            except Exception:
                db.session.rollback()
            return False, {"error": "Usuario temporalmente bloqueado"}

        if user.estado != 'Activo':
            return False, {"error": f"Usuario no está activo (estado: {user.estado})"}

        # verificar password
        if not Hasher.verify(password, user.password):
            # Registrar intento fallido BAD_CREDENTIALS
            try:
                ull = UserLoginLog(usuario_id=user.id, success=False, fail_reason='BAD_CREDENTIALS')
                db.session.add(ull)
                db.session.flush()
            except Exception:
                db.session.rollback()
            # mantener la política de bloqueo del modelo existente
            try:
                user.failed_login_count = (user.failed_login_count or 0) + 1
                user.last_failed_login_at = now
                MAX_FAILED = 5
                LOCK_MINUTES = 15
                if user.failed_login_count >= MAX_FAILED:
                    user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
                    user.estado = 'Bloqueado'
                    # registrar evento LOCKED cuando se alcanza el umbral
                    try:
                        ull2 = UserLoginLog(usuario_id=user.id, success=False, fail_reason='LOCKED')
                        db.session.add(ull2)
                    except Exception:
                        db.session.rollback()
                UserRepository.save(user)
            except Exception:
                pass
            return False, {"error": "credenciales inválidas"}

        # login correcto: reset campos temporales, no cambiar estado
        try:
            user.failed_login_count = 0
            user.last_failed_login_at = None
            user.locked_until = None
            UserRepository.save(user)
        except Exception:
            pass

        # generar tokens
        token_version = user.token_version if user else 0
        access = JwtProvider.create_access(user.id, token_version)
        refresh = JwtProvider.create_refresh(user.id)

        # persistir hash refresh token en repositorio
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            RefreshTokenRepository.persist(refresh, user.id, expires_at)
        except Exception:
            pass

        return True, {"tokens": {"access_token": access, "refresh_token": refresh}}