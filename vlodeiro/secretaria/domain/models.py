from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Turno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dia_semana = db.Column(db.String(20))
    hora = db.Column(db.Time)
    tipo_alumno = db.Column(db.String(20))
    duracion = db.Column(db.Integer)
    capacidad = db.Column(db.Integer)
    empresa_id = db.Column(db.Integer)
    activo = db.Column(db.Boolean, default=True)