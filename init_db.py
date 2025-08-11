from app import app

from models import db, Empresa, Turno, Tarifa, Inscripcion, Sesion, Asistencia, Pago, Alumno
from datetime import date
import argparse

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

    # Asegurar una tarifa por defecto para evitar errores de FK en inscripciones
    if db.session.query(Tarifa).count() == 0:
        default_tarifa = Tarifa(
            empresa_id=empresa.id,
            descripcion="General 120min",
            duracion_min=120,
            precio_base=40.0,
            descuento=0,
            activo=True,
        )
        db.session.add(default_tarifa)
        db.session.commit()
        print(f"[init_db] Tarifa por defecto creada con id={default_tarifa.id}")
    else:
        print("[init_db] Ya existen tarifas; no se crean nuevas")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inicializa la base de datos y carga datos de prueba.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="BORRA todas las tablas y las recrea antes de cargar datos (¡destructivo!).",
    )
    args = parser.parse_args()

    with app.app_context():
        if args.reset:
            print("[init_db] --reset solicitado: borrando todas las tablas...")
            db.drop_all()
        # Crea tablas si no existen y pobla datos si está vacío
        db.create_all()
        seed_if_empty()
        if args.reset:
            print("[init_db] Reset completado: tablas recreadas y datos de prueba cargados")
        else:
            print("Init DB: tablas aseguradas y datos iniciales listos (idempotente)")
