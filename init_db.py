from app import app
from models import db, Empresa, Turno
from datetime import time

with app.app_context():
    db.create_all()
    # Poblar con datos de ejemplo similares a producción
    empresa = Empresa(nombre="Academia Ejemplo")
    db.session.add(empresa)
    db.session.commit()

    turnos = [
        Turno(empresa_id=empresa.id, dia_semana="lunes", hora=time(19,30), tipo_alumno="adulto", duracion=120, capacidad=15, activo=True),
        Turno(empresa_id=empresa.id, dia_semana="martes", hora=time(19,30), tipo_alumno="adulto", duracion=120, capacidad=15, activo=True),
        Turno(empresa_id=empresa.id, dia_semana="miércoles", hora=time(19,30), tipo_alumno="adulto", duracion=120, capacidad=15, activo=True),
    ]
    db.session.add_all(turnos)
    db.session.commit()
    print("Tablas y datos de ejemplo creados correctamente.")
