from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Boolean, LargeBinary, BigInteger, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.shared.database import Base

class Usuario(Base):
    __tablename__ = 'Usuario'
    id = Column(Integer, primary_key=True, autoincrement=True)
    academia_id = Column(Integer, ForeignKey('Academia.id'), nullable=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    rol_id = Column(Integer, ForeignKey('Rol_Usuario.id'), nullable=False)
    estado = Column(Enum('Activo', 'Bloqueado', 'Baja'), default='Activo', nullable=False)
    fecha_alta = Column(DateTime, default=func.current_timestamp(), nullable=False)
    fecha_baja = Column(DateTime, nullable=True)
    fecha_ultima_modificacion = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)
    token_version = Column(Integer, default=0, nullable=False)
    failed_login_count = Column(Integer, default=0, nullable=False)
    last_failed_login_at = Column(DateTime, nullable=True)
    locked_until = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_usuario_token_version', 'token_version'),
    )

    rol = relationship('Rol', back_populates='usuarios')
    login_logs = relationship('UserLoginLog', back_populates='usuario')

class Rol(Base):
    __tablename__ = 'Rol_Usuario'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(50), unique=True, nullable=False)
    usuarios = relationship('Usuario', back_populates='rol')

class RefreshToken(Base):
    __tablename__ = 'RefreshToken'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey('Usuario.id'), nullable=False)
    token_hash = Column(String(64), nullable=False)
    issued_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    replaced_by_id = Column(BigInteger, ForeignKey('RefreshToken.id'), nullable=True)
    ip = Column(LargeBinary(16), nullable=True)
    user_agent = Column(String(255), nullable=True)
    device_id = Column(String(100), nullable=True)
    scope = Column(String(200), nullable=True)

    __table_args__ = (
        UniqueConstraint('token_hash', name='uk_refreshtoken_hash'),
        Index('idx_refreshtoken_usuario_exp', 'usuario_id', 'expires_at'),
        Index('idx_refreshtoken_revoked', 'revoked_at'),
    )

    usuario = relationship('Usuario')

class UserLoginLog(Base):
    __tablename__ = 'UserLoginLog'

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey('Usuario.id'), nullable=False)
    login_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)
    logout_at = Column(DateTime, nullable=True)
    success = Column(Boolean, nullable=False)
    fail_reason = Column(String(100), nullable=True)
    ip = Column(LargeBinary(16), nullable=True)
    user_agent = Column(String(255), nullable=True)
    device_id = Column(String(100), nullable=True)
    client = Column(String(50), nullable=True)

    __table_args__ = (
        Index('idx_ull_usuario_login', 'usuario_id', 'login_at'),
        Index('idx_ull_success_login', 'success', 'login_at'),
    )

    usuario = relationship('Usuario', back_populates='login_logs')

class PasswordResetToken(Base):
    __tablename__ = 'PasswordResetToken'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey('Usuario.id'), nullable=False)
    token_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    ip = Column(LargeBinary(16), nullable=True)
    user_agent = Column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint('token_hash', name='uk_pwdreset_hash'),
        Index('idx_pwdreset_usuario_exp', 'usuario_id', 'expires_at'),
    )

    usuario = relationship('Usuario')