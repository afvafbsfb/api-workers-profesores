from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash

db = SQLAlchemy()

# Modelo para Academias
class Academia(db.Model):
    __tablename__ = 'academias'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    direccion = db.Column(db.String(255), nullable=True)
    telefono = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    cursos = db.relationship('Curso', backref='academia', lazy=True)
    aulas = db.relationship('Aula', backref='academia', lazy=True)
    alumnos = db.relationship('Alumno', backref='academia', lazy=True)

# Modelo para Aula
class Aula(db.Model):
    __tablename__ = 'aulas'
    id = db.Column(db.Integer, primary_key=True)
    academia_id = db.Column(db.Integer, db.ForeignKey('academias.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    capacidad_maxima = db.Column(db.Integer, nullable=False)

# Modelo para Cursos
class Curso(db.Model):
    __tablename__ = 'cursos'
    id = db.Column(db.Integer, primary_key=True)
    academia_id = db.Column(db.Integer, db.ForeignKey('academias.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    anio_academico = db.Column(db.String(20), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    acepta_nuevos_alumnos = db.Column(db.Boolean, nullable=False)
    capacidad_maxima = db.Column(db.Integer, nullable=False)
    tarifa_id = db.Column(db.Integer, db.ForeignKey('tarifas.id'), nullable=False)
    tipo_alumno = db.Column(db.Enum('Infantil', 'Juvenil', 'Adultos'), nullable=False)
    estado = db.Column(db.Enum('Activo', 'Inactivo', 'Finalizado'), nullable=False)

# Modelo para HorarioCurso
class HorarioCurso(db.Model):
    __tablename__ = 'horarios_curso'
    id = db.Column(db.Integer, primary_key=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False)
    aula_id = db.Column(db.Integer, db.ForeignKey('aulas.id'), nullable=False)
    dia_semana = db.Column(db.String(20), nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)

# Modelo para Usuarios
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    academia_id = db.Column(db.Integer, db.ForeignKey('academias.id'), nullable=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    estado = db.Column(db.Enum('Activo', 'Bloqueado', 'Baja'), default='Activo', nullable=False)
    fecha_alta = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    fecha_baja = db.Column(db.DateTime, nullable=True)
    fecha_ultima_modificacion = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp(), nullable=False)

    def check_password(self, password):
        """Verifica si la contraseña proporcionada coincide con el hash almacenado."""
        return check_password_hash(self.password, password)

# Modelo para Roles
class Rol(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(255), nullable=True)

# Modelo para Tokens de Sesión
class Token(db.Model):
    __tablename__ = 'tokens'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    token_acceso = db.Column(db.String(500), nullable=False)
    token_refresh = db.Column(db.String(500), nullable=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False)
    fecha_expiracion = db.Column(db.DateTime, nullable=False)

# Modelo para Tarifas
class Tarifa(db.Model):
    __tablename__ = 'tarifas'
    id = db.Column(db.Integer, primary_key=True)
    academia_id = db.Column(db.Integer, db.ForeignKey('academias.id'), nullable=False)
    descripcion = db.Column(db.String(255), nullable=False)
    precio_base = db.Column(db.Float, nullable=False)  # Campo obligatorio
    fecha_alta = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    fecha_baja = db.Column(db.DateTime, nullable=True)
    fecha_ultima_modificacion = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp(), nullable=False)

# Modelo para Inscripciones
class Inscripcion(db.Model):
    __tablename__ = 'inscripciones'
    id = db.Column(db.Integer, primary_key=True)
    alumno_id = db.Column(db.Integer, db.ForeignKey('alumnos.id'), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False)  # Actualizado para coincidir con SQL
    tarifa_id = db.Column(db.Integer, db.ForeignKey('tarifas.id'), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)  # Added based on SQL schema assumption

# Modelo para Alumnos
class Alumno(db.Model):
    __tablename__ = 'alumnos'
    id = db.Column(db.Integer, primary_key=True)
    academia_id = db.Column(db.Integer, db.ForeignKey('academias.id'), nullable=False)
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
    __tablename__ = 'curso_profesores'
    id = db.Column(db.Integer, primary_key=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    fecha_alta = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    fecha_baja = db.Column(db.DateTime, nullable=True)
    fecha_ult_modificacion = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp(), nullable=False)
    motivo_baja = db.Column(db.String(255))

# Modelo para DescuentosTarifa
class DescuentosTarifa(db.Model):
    __tablename__ = 'descuentos_tarifa'
    id = db.Column(db.Integer, primary_key=True)
    tarifa_id = db.Column(db.Integer, db.ForeignKey('tarifas.id'), nullable=False)
    motivo_descuento = db.Column(db.String(1), nullable=False)  # 'F' o 'M'
    tipo_descuento = db.Column(db.String(1), nullable=False)  # 'P' o 'F'
    porcentaje_descuento = db.Column(db.Float, nullable=True)
    importe_descuento = db.Column(db.Float, nullable=True)

# Modelo para familias_alumnos
class FamiliasAlumnos(db.Model):
    __tablename__ = 'familias_alumnos'
    id_familia_alumno = db.Column(db.Integer, primary_key=True)
    id_alumno1 = db.Column(db.Integer, db.ForeignKey('alumnos.id'), nullable=False)
    id_alumno2 = db.Column(db.Integer, db.ForeignKey('alumnos.id'), nullable=False)
    relacion_familiar = db.Column(db.String(100), nullable=False)

# Modelo para AnotacionesAlumnoSesion
class AnotacionesAlumnoSesion(db.Model):
    __tablename__ = 'anotaciones_alumno_sesion'
    id = db.Column(db.Integer, primary_key=True)
    sesion_id = db.Column(db.Integer, db.ForeignKey('sesiones.id'), nullable=False)
    inscripcion_id = db.Column(db.Integer, db.ForeignKey('inscripciones.id'), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False)
    curso_profesor_id = db.Column(db.Integer, db.ForeignKey('curso_profesores.id'), nullable=False)
    alumno_id = db.Column(db.Integer, db.ForeignKey('alumnos.id'), nullable=False)
    tipo_anotacion = db.Column(db.Enum('Ausencia', 'Evaluacion', 'Comportamiento'), nullable=False)
    texto = db.Column(db.String(255), nullable=True)
    timestamp_alta = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    timestamp_baja = db.Column(db.DateTime, nullable=True)
    motivo_baja = db.Column(db.String(255), nullable=True)

# Modelo para Extractos
class Extractos(db.Model):
    __tablename__ = 'extractos'
    id = db.Column(db.Integer, primary_key=True)
    inscripcion_id = db.Column(db.Integer, db.ForeignKey('inscripciones.id'), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False)
    alumno_id = db.Column(db.Integer, db.ForeignKey('alumnos.id'), nullable=False)
    numero_extracto = db.Column(db.Integer, nullable=False)
    saldo_ingreso_cuenta_anterior = db.Column(db.Float, nullable=True)
    estado_liquidacion_extracto = db.Column(db.Enum('1', '2'), nullable=False)
    fecha_alta = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    fecha_ini_periodo = db.Column(db.Date, nullable=False)
    fecha_fin_periodo = db.Column(db.Date, nullable=False)
    total_importe_a_cobrar = db.Column(db.Float, nullable=False)

# Modelo para MovimientosExtracto
class MovimientosExtracto(db.Model):
    __tablename__ = 'movimientos_extracto'
    id = db.Column(db.Integer, primary_key=True)
    inscripcion_id = db.Column(db.Integer, db.ForeignKey('inscripciones.id'), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey('cursos.id'), nullable=False)
    alumno_id = db.Column(db.Integer, db.ForeignKey('alumnos.id'), nullable=False)
    extracto_id = db.Column(db.Integer, db.ForeignKey('extractos.id'), nullable=False)
    fecha_movimiento = db.Column(db.Date, nullable=False)
    tipo_movimiento = db.Column(db.Enum('Ingreso', 'Anulacion_Ingreso'), nullable=False)
    estado_liquidacion_movimiento = db.Column(db.Enum('1', '2'), nullable=False)
    importe = db.Column(db.Float, nullable=False)
    descripcion_movimiento = db.Column(db.String(255))
    metodo_pago = db.Column(db.String(50), nullable=False)
    indicador_movimiento_anulado = db.Column(db.Enum('S', 'N'), default='N', nullable=False)

# Modelo para TrabajadorVirtual
class TrabajadorVirtual(db.Model):
    __tablename__ = 'trabajador_virtual'
    id = db.Column(db.Integer, primary_key=True)
    academia_id = db.Column(db.Integer, db.ForeignKey('academias.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    foto = db.Column(db.String(255), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    apikey = db.Column(db.String(255), nullable=True)
    es_administrativo_virtual = db.Column(db.Boolean, nullable=False)

# Modelo para Sesion
class Sesion(db.Model):
    __tablename__ = 'sesiones'
    id = db.Column(db.Integer, primary_key=True)
    aula_id = db.Column(db.Integer, db.ForeignKey('aulas.id'), nullable=False)
    curso_profesor_id = db.Column(db.Integer, db.ForeignKey('curso_profesores.id'), nullable=False)
    timestamp_alta = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    timestamp_baja = db.Column(db.DateTime, nullable=True)
    motivo_baja = db.Column(db.String(255), nullable=True)
    notas_sesion = db.Column(db.Text, nullable=True)
    notas_materia = db.Column(db.Text, nullable=True)
