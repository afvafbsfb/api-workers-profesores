from app import app

from models import db, Empresa, Turno, Tarifa, Inscripcion, Sesion, Asistencia, Pago, Alumno
from datetime import date

def seed_if_empty():
    # Solo poblar si no hay registros
    if db.session.query(Empresa).count() == 0:
        empresa = Empresa(nombre="Academia Ejemplo")
        db.session.add(empresa)
        db.session.commit()
    else:
        empresa = db.session.query(Empresa).first()

    if db.session.query(Turno).count() == 0:
        turnos_data = [
            ("adulto", "lunes", "19:30", "21:30", 120, 15),
            ("adulto", "martes", "19:30", "21:30", 120, 15),
            ("adulto", "miércoles", "11:30", "13:30", 120, 15),
            ("adulto", "miércoles", "19:30", "21:30", 120, 15),
            ("adulto", "jueves", "19:30", "21:30", 120, 15),
            ("niño", "lunes", "16:30", "18:00", 90, 20),
            ("niño", "lunes", "18:00", "19:30", 90, 20),
            ("niño", "martes", "17:30", "19:00", 90, 20),
            ("niño", "miércoles", "17:30", "19:00", 90, 20),
            ("niño", "jueves", "17:30", "19:00", 90, 20),
            ("niño", "viernes", "16:30", "18:00", 90, 20),
            ("niño", "viernes", "18:00", "20:00", 120, 20),
            ("niño", "sábado", "11:30", "13:30", 120, 20),
        ]
        turnos = [
            Turno(
                empresa_id=empresa.id,
                tipo_alumno=t[0],
                dia_semana=t[1],
                hora_inicio=t[2],
                hora_fin=t[3],
                duracion_min=t[4],
                capacidad=t[5],
                activo=True,
            )
            for t in turnos_data
        ]
        db.session.add_all(turnos)
        db.session.commit()

    if db.session.query(Alumno).count() == 0:
        alumnos = [
            Alumno(nombre=f"Alumno {i}", email=f"alumno{i}@example.com")
            for i in range(1, 51)
        ]
        db.session.add_all(alumnos)
        db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        # Crea tablas si no existen y pobla datos si está vacío
        db.create_all()
        seed_if_empty()
        print("Init DB: tablas aseguradas y datos iniciales listos (idempotente)")
