from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class Empresa(db.Model):
    __tablename__ = 'empresas'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)

class Turno(db.Model):
    __tablename__ = 'turnos'
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    dia_semana = db.Column(db.Enum('lunes','martes','miércoles','jueves','viernes','sábado'), nullable=False)
    hora = db.Column(db.Time, nullable=False)
    tipo_alumno = db.Column(db.Enum('niño','adulto'), nullable=False)
    duracion = db.Column(db.Integer, nullable=False)
    capacidad = db.Column(db.Integer, nullable=False)
    activo = db.Column(db.Boolean, default=True)

class Tarifa(db.Model):
    __tablename__ = 'tarifas'
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    duracion = db.Column(db.Integer, nullable=False)
    precio_base = db.Column(db.Numeric(8,2), nullable=False)
    descripcion = db.Column(db.Text)
    descuento = db.Column(db.Numeric(5,2), default=0)
    activo = db.Column(db.Boolean, default=True)
