from typing import Tuple, Dict
from src.autenticacion.infrastructure.repositories import UserRepository, RefreshTokenRepository
from models import UserLoginLog, db, RefreshToken
from src.autenticacion.infrastructure.hasher import Hasher
from src.autenticacion.infrastructure.jwt_provider import JwtProvider
from datetime import datetime, timezone, timedelta
import hashlib
from config import Config


class AuthService:
    """Servicio de aplicación que agrupa las operaciones de autenticación.

    Por ahora implementa login de forma similar a la lógica existente en
    src/usuarios/login_routes.py, pero delegando persistencia y hashing a
    los adaptadores.
    """

    @staticmethod
    def login(email: str, password: str) -> Tuple[bool, Dict]:
        if Config.DEBUG:
            print(f"[DEBUG] Intentando autenticar usuario: {email}")
        user = UserRepository.get_by_email(email)
        if not user:
            if Config.DEBUG:
                print(f"[DEBUG] Usuario no encontrado: {email}")
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
            # Registrar intento fallido BAD_CREDENTIALS y aplicar política de bloqueo
            try:
                # 1) Crear log de fallo y confirmar inmediatamente
                ull = UserLoginLog(usuario_id=user.id, success=False, fail_reason='BAD_CREDENTIALS')
                db.session.add(ull)
                db.session.commit()
                # print(f"[AuthService] Logged BAD_CREDENTIALS for user_id={user.id}", flush=True)
            except Exception:
                db.session.rollback()

            # 2) Incrementar contador del usuario en una transacción separada
            try:
                # recargar usuario para tener un estado fresco
                user_db = db.session.get(type(user), user.id)
                user_db.failed_login_count = (user_db.failed_login_count or 0) + 1
                # print(f"[DEBUG] Incremented failed_login_count for user_id={user_db.id} to {user_db.failed_login_count}")
                user_db.last_failed_login_at = now
                MAX_FAILED = 5
                LOCK_MINUTES = 15
                if user_db.failed_login_count >= MAX_FAILED:
                    user_db.locked_until = now + timedelta(minutes=LOCK_MINUTES)
                    user_db.estado = 'Bloqueado'
                    # registrar evento LOCKED cuando se alcanza el umbral
                    ull2 = UserLoginLog(usuario_id=user_db.id, success=False, fail_reason='LOCKED')
                    db.session.add(ull2)
                db.session.add(user_db)
                db.session.commit()
                # print(f"[AuthService] Incremented failed_login_count for user_id={user_db.id} -> {user_db.failed_login_count}", flush=True)
            except Exception:
                db.session.rollback()

            return False, {"error": "credenciales inválidas"}

        # login correcto: reset campos temporales, no cambiar estado
        try:
            user.failed_login_count = 0
            # print(f"[DEBUG] Reset failed_login_count for user_id={user.id}")
            user.last_failed_login_at = None
            user.locked_until = None
            db.session.add(user)
            db.session.commit()
        except Exception:
            db.session.rollback()

        if Config.DEBUG:
            print(f"[DEBUG] Usuario autenticado: {user.id}, Rol: {user.rol.nombre}")

        # generar tokens
        token_version = user.token_version if user else 0
        access = JwtProvider.create_access(user.id, token_version)
        refresh = JwtProvider.create_refresh(user.id)
        if Config.DEBUG:
            print(f"[DEBUG] Tokens generados para usuario {user.id}: Access Token y Refresh Token")

        # persistir hash refresh token en la misma sesión para garantizar disponibilidad inmediata
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            token_hash = hashlib.sha256(refresh.encode('utf-8')).hexdigest()
            # Depuración adicional para SQLite
            # print(f"[DEBUG] Intentando persistir RefreshToken para user_id={user.id}", flush=True)
            # print(f"[DEBUG] Valores: token_hash={token_hash}, expires_at={expires_at}", flush=True)
            # Validar valores antes de persistir
            if not user.id or not token_hash or not expires_at:
                raise ValueError("Valores inválidos para persistir RefreshToken")

            # Persistir hash del refresh token en la misma sesión
            rt = RefreshToken(usuario_id=user.id, token_hash=token_hash, expires_at=expires_at)
            db.session.add(rt)
            db.session.commit()
            # print(f"[AuthService] Persisted refresh token hash for user_id={user.id}: {token_hash}", flush=True)
        except Exception as e:
            # print(f"[DEBUG] Error al persistir RefreshToken: {e}", flush=True)
            db.session.rollback()

        # Obtener rol y nombre del usuario
        role = user.rol.nombre if user.rol else None
        name = user.nombre

        return True, {
            "tokens": {"access_token": access, "refresh_token": refresh},
            "role": role,
            "name": name,
            "usuario": user
        }