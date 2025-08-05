from app import app

from models import db, Empresa, Turno, Tarifa, Inscripcion, Sesion, Asistencia, Pago, Alumno
from datetime import date

if __name__ == "__main__":
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Tablas creadas correctamente.")

        # Poblar empresa
        empresa = Empresa(nombre="Academia Ejemplo")
        db.session.add(empresa)
        db.session.commit()

        # Poblar 13 turnos
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
        turnos = []
        for t in turnos_data:
            turnos.append(Turno(empresa_id=empresa.id, tipo_alumno=t[0], dia_semana=t[1], hora_inicio=t[2], hora_fin=t[3], duracion_min=t[4], capacidad=t[5], activo=True))
        db.session.add_all(turnos)
        db.session.commit()

        # Poblar 50 alumnos
        alumnos = []
        for i in range(1, 51):
            alumnos.append(Alumno(nombre=f"Alumno {i}", email=f"alumno{i}@example.com"))
        db.session.add_all(alumnos)
        db.session.commit()
