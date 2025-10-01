from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from werkzeug.security import check_password_hash
from src.shared.security import verify_password

# Use a naming convention so Alembic generates stable, predictable constraint/index names
naming_convention = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=naming_convention)
db = SQLAlchemy(metadata=metadata)

# Modelo para Academias
class Academia(db.Model):
    __tablename__ = 'Academia'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    # Nota: la tabla canonical `Academia` (create_database.sql) contiene solo id y nombre.
    # Campos como direccion/telefono/email no existen en la versión canónica y fueron retirados
    # para que el ORM no intente seleccionar/insertar columnas inexistentes.
    cursos = db.relationship('Curso', backref='academia', lazy=True)
    aulas = db.relationship('Aula', backref='academia', lazy=True)
    alumnos = db.relationship('Alumno', backref='academia', lazy=True)

# Modelo para Aula
class Aula(db.Model):
    __tablename__ = 'Aula'
    id = db.Column(db.Integer, primary_key=True)
    academia_id = db.Column(db.Integer, db.ForeignKey('Academia.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    capacidad_maxima = db.Column(db.Integer, nullable=False)

# Modelo para Cursos
class Curso(db.Model):
    __tablename__ = 'Curso'
    id = db.Column(db.Integer, primary_key=True)
    academia_id = db.Column(db.Integer, db.ForeignKey('Academia.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    anio_academico = db.Column(db.String(20), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    acepta_nuevos_alumnos = db.Column(db.Boolean, nullable=False)
    capacidad_maxima = db.Column(db.Integer, nullable=False)
    tarifa_id = db.Column(db.Integer, db.ForeignKey('Tarifa.id'), nullable=False)
    tipo_alumno = db.Column(db.Enum('Infantil', 'Juvenil', 'Adultos'), nullable=False)
    estado = db.Column(db.Enum('Activo', 'Inactivo', 'Finalizado'), nullable=False)

# Modelo para HorarioCurso
class HorarioCurso(db.Model):
    __tablename__ = 'HorarioCurso'
    id = db.Column(db.Integer, primary_key=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('Curso.id'), nullable=False)
    aula_id = db.Column(db.Integer, db.ForeignKey('Aula.id'), nullable=False)
    dia_semana = db.Column(db.String(20), nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)

# Modelo para Usuarios
class Usuario(db.Model):
    __tablename__ = 'Usuario'
    id = db.Column(db.Integer, primary_key=True)
    academia_id = db.Column(db.Integer, db.ForeignKey('Academia.id'), nullable=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey('Rol_Usuario.id'), nullable=False)
    estado = db.Column(db.Enum('Activo', 'Bloqueado', 'Baja'), default='Activo', nullable=False)
    fecha_alta = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    fecha_baja = db.Column(db.DateTime, nullable=True)
    fecha_ultima_modificacion = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp(), nullable=False)
    # Control de versión de tokens (invalida access tokens antiguos cuando se incrementa)
    token_version = db.Column(db.Integer, default=0, nullable=False)
    # Anti-brute-force / bloqueo de cuenta
    failed_login_count = db.Column(db.Integer, default=0, nullable=False)
    last_failed_login_at = db.Column(db.DateTime, nullable=True)
    locked_until = db.Column(db.DateTime, nullable=True)

    def check_password(self, password):
        """Verifica si la contraseña proporcionada coincide con el hash almacenado."""
        # Usar la implementación de verificación del proyecto (argon2)
        # verify_password(password_plain, hashed_password)
        return verify_password(password, self.password)

# Modelo para Roles
class Rol(db.Model):
    __tablename__ = 'Rol_Usuario'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)


# Modelo para Tokens de Sesión
class Token(db.Model):
    __tablename__ = 'tokens'
    id = db.Column(db.Integer, primary_key=True)
    # Referenciar la tabla canonical `Usuario` (capitalizada) para evitar NoReferencedTableError
    usuario_id = db.Column(db.Integer, db.ForeignKey('Usuario.id'), nullable=False)
    token_acceso = db.Column(db.String(500), nullable=False)
    token_refresh = db.Column(db.String(500), nullable=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False)
    fecha_expiracion = db.Column(db.DateTime, nullable=False)


# Tabla para persistir refresh tokens (hash del token, rotación y revocación)
class RefreshToken(db.Model):
    __tablename__ = 'RefreshToken'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('Usuario.id'), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False)  # SHA-256
    issued_at = db.Column(db.DateTime, server_default=db.func.current_timestamp(), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    replaced_by_id = db.Column(db.BigInteger, db.ForeignKey('RefreshToken.id'), nullable=True)
    ip = db.Column(db.LargeBinary(16), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    device_id = db.Column(db.String(100), nullable=True)
    scope = db.Column(db.String(200), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('token_hash', name='uk_refreshtoken_hash'),
        db.Index('idx_refreshtoken_usuario_exp', 'usuario_id', 'expires_at'),
        db.Index('idx_refreshtoken_revoked', 'revoked_at'),
    )


# Historial de intentos de login
class UserLoginLog(db.Model):
    __tablename__ = 'UserLoginLog'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('Usuario.id'), nullable=False)
    login_at = db.Column(db.DateTime, server_default=db.func.current_timestamp(), nullable=False)
    logout_at = db.Column(db.DateTime, nullable=True)
    success = db.Column(db.Boolean, nullable=False)
    fail_reason = db.Column(db.String(100), nullable=True)
    ip = db.Column(db.LargeBinary(16), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    device_id = db.Column(db.String(100), nullable=True)
    client = db.Column(db.String(50), nullable=True)

    __table_args__ = (
        db.Index('idx_ull_usuario_login', 'usuario_id', 'login_at'),
        db.Index('idx_ull_success_login', 'success', 'login_at'),
    )

# Modelo para Tarifas
class Tarifa(db.Model):
    __tablename__ = 'Tarifa'
    id = db.Column(db.Integer, primary_key=True)
    academia_id = db.Column(db.Integer, db.ForeignKey('Academia.id'), nullable=False)
    descripcion = db.Column(db.String(255), nullable=False)
    precio_base = db.Column(db.Float, nullable=False)  # Campo obligatorio
    fecha_alta = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    fecha_baja = db.Column(db.DateTime, nullable=True)
    fecha_ultima_modificacion = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp(), nullable=False)

# Modelo para Inscripciones
class Inscripcion(db.Model):
    __tablename__ = 'Inscripcion'
    id = db.Column(db.Integer, primary_key=True)
    alumno_id = db.Column(db.Integer, db.ForeignKey('Alumno.id'), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey('Curso.id'), nullable=False)
    tarifa_id = db.Column(db.Integer, db.ForeignKey('Tarifa.id'), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)  # Added based on SQL schema assumption

# Modelo para Alumnos
class Alumno(db.Model):
    __tablename__ = 'Alumno'
    id = db.Column(db.Integer, primary_key=True)
    academia_id = db.Column(db.Integer, db.ForeignKey('Academia.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    dni = db.Column(db.String(20), nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    fecha_nacimiento = db.Column(db.Date, nullable=False)
    direccion = db.Column(db.String(255), nullable=False)
    nombre_tutor = db.Column(db.String(100))
    relaccion_tutor_alumno = db.Column(db.String(100))
    telefono_tutor = db.Column(db.String(20))
    email_tutor = db.Column(db.String(120))

# Modelo para Curso_Profesores
class CursoProfesores(db.Model):
    __tablename__ = 'Curso_Profesores'
    id = db.Column(db.Integer, primary_key=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('Curso.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('Usuario.id'), nullable=False)
    fecha_alta = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    fecha_baja = db.Column(db.DateTime, nullable=True)
    fecha_ult_modificacion = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp(), nullable=False)
    motivo_baja = db.Column(db.String(255))

# Modelo para DescuentosTarifa
class DescuentosTarifa(db.Model):
    __tablename__ = 'Descuentos_tarifa'
    id = db.Column(db.Integer, primary_key=True)
    tarifa_id = db.Column(db.Integer, db.ForeignKey('Tarifa.id'), nullable=False)
    motivo_descuento = db.Column(db.String(1), nullable=False)  # 'F' o 'M'
    tipo_descuento = db.Column(db.String(1), nullable=False)  # 'P' o 'F'
    porcentaje_descuento = db.Column(db.Float, nullable=True)
    importe_descuento = db.Column(db.Float, nullable=True)

# Modelo para familias_alumnos
class FamiliasAlumnos(db.Model):
    __tablename__ = 'familias_alumnos'
    id_familia_alumno = db.Column(db.Integer, primary_key=True)
    id_alumno1 = db.Column(db.Integer, db.ForeignKey('Alumno.id'), nullable=False)
    id_alumno2 = db.Column(db.Integer, db.ForeignKey('Alumno.id'), nullable=False)
    relacion_familiar = db.Column(db.String(100), nullable=False)

# Modelo para AnotacionesAlumnoSesion
class AnotacionesAlumnoSesion(db.Model):
    __tablename__ = 'AnotacionesAlumnoSesion'
    id = db.Column(db.Integer, primary_key=True)
    sesion_id = db.Column(db.Integer, db.ForeignKey('Sesion.id'), nullable=False)
    inscripcion_id = db.Column(db.Integer, db.ForeignKey('Inscripcion.id'), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey('Curso.id'), nullable=False)
    curso_profesor_id = db.Column(db.Integer, db.ForeignKey('Curso_Profesores.id'), nullable=False)
    alumno_id = db.Column(db.Integer, db.ForeignKey('Alumno.id'), nullable=False)
    tipo_anotacion = db.Column(db.Enum('Ausencia', 'Evaluacion', 'Comportamiento'), nullable=False)
    texto = db.Column(db.String(255), nullable=True)
    timestamp_alta = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    timestamp_baja = db.Column(db.DateTime, nullable=True)
    motivo_baja = db.Column(db.String(255), nullable=True)

# Modelo para Extractos
class Extractos(db.Model):
    __tablename__ = 'Extractos'
    id = db.Column(db.Integer, primary_key=True)
    inscripcion_id = db.Column(db.Integer, db.ForeignKey('Inscripcion.id'), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey('Curso.id'), nullable=False)
    alumno_id = db.Column(db.Integer, db.ForeignKey('Alumno.id'), nullable=False)
    numero_extracto = db.Column(db.Integer, nullable=False)
    saldo_ingreso_cuenta_anterior = db.Column(db.Float, nullable=True)
    estado_liquidacion_extracto = db.Column(db.Enum('1', '2'), nullable=False)
    fecha_alta = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    fecha_ini_periodo = db.Column(db.Date, nullable=False)
    fecha_fin_periodo = db.Column(db.Date, nullable=False)
    total_importe_a_cobrar = db.Column(db.Float, nullable=False)

# Modelo para MovimientosExtracto
class MovimientosExtracto(db.Model):
    __tablename__ = 'Movimientos_Extracto'
    id = db.Column(db.Integer, primary_key=True)
    inscripcion_id = db.Column(db.Integer, db.ForeignKey('Inscripcion.id'), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey('Curso.id'), nullable=False)
    alumno_id = db.Column(db.Integer, db.ForeignKey('Alumno.id'), nullable=False)
    extracto_id = db.Column(db.Integer, db.ForeignKey('Extractos.id'), nullable=False)
    fecha_movimiento = db.Column(db.Date, nullable=False)
    tipo_movimiento = db.Column(db.Enum('Ingreso', 'Anulacion_Ingreso'), nullable=False)
    estado_liquidacion_movimiento = db.Column(db.Enum('1', '2'), nullable=False)
    importe = db.Column(db.Float, nullable=False)
    descripcion_movimiento = db.Column(db.String(255))
    metodo_pago = db.Column(db.String(50), nullable=False)
    indicador_movimiento_anulado = db.Column(db.Enum('S', 'N'), default='N', nullable=False)

# Modelo para TrabajadorVirtual
class TrabajadorVirtual(db.Model):
    __tablename__ = 'TrabajadorVirtual'
    id = db.Column(db.Integer, primary_key=True)
    academia_id = db.Column(db.Integer, db.ForeignKey('Academia.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    foto = db.Column(db.String(255), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    apikey = db.Column(db.String(255), nullable=True)
    es_administrativo_virtual = db.Column(db.Boolean, nullable=False)

# Modelo para Sesion
class Sesion(db.Model):
    __tablename__ = 'Sesion'
    id = db.Column(db.Integer, primary_key=True)
    aula_id = db.Column(db.Integer, db.ForeignKey('Aula.id'), nullable=False)
    curso_profesor_id = db.Column(db.Integer, db.ForeignKey('Curso_Profesores.id'), nullable=False)
    timestamp_alta = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    timestamp_baja = db.Column(db.DateTime, nullable=True)
    motivo_baja = db.Column(db.String(255), nullable=True)
    notas_sesion = db.Column(db.Text, nullable=True)
    notas_materia = db.Column(db.Text, nullable=True)
