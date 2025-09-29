from main import app
from src.shared.security import hash_password

from models import db, Academia, Curso, Aula, Usuario, Rol, HorarioCurso, Alumno, Inscripcion, CursoProfesores, Sesion, Tarifa
from datetime import date, time
import argparse

def seed_if_empty():
    # Poblar datos iniciales para Academia
    if db.session.query(Academia).count() == 0:
        academia = Academia(
            nombre="Academia Central",
            email="contacto@academia.com"  # Agregar un email válido
        )
        db.session.add(academia)
        db.session.commit()
        print(f"[init_db] Academia creada con id={academia.id}")

    # Poblar datos iniciales para Tarifas
    if db.session.query(Tarifa).count() == 0:
        tarifa = Tarifa(
            academia_id=academia.id,
            descripcion="Tarifa General",
            precio_base=50.0
        )
        db.session.add(tarifa)
        db.session.commit()
        print(f"[init_db] Tarifa creada con id={tarifa.id}")

    # Poblar datos iniciales para Cursos
    if db.session.query(Curso).count() == 0:
        curso = Curso(
            academia_id=academia.id,
            nombre="Curso de Verano",
            anio_academico="2025-2026",
            fecha_inicio=date(2025, 6, 1),
            fecha_fin=date(2025, 8, 31),
            acepta_nuevos_alumnos=True,
            capacidad_maxima=30,
            tarifa_id=tarifa.id,
            tipo_alumno="Juvenil",
            estado="Activo"
        )
        db.session.add(curso)
        db.session.commit()
        print(f"[init_db] Curso creado con id={curso.id}")

    # Poblar datos iniciales para Aulas
    if db.session.query(Aula).count() == 0:
        aula = Aula(
            academia_id=academia.id,
            nombre="Aula 101",
            capacidad_maxima=20
        )
        db.session.add(aula)
        db.session.commit()
        print(f"[init_db] Aula creada con id={aula.id}")

    # Poblar datos iniciales para Usuarios
    if db.session.query(Usuario).count() == 0:
        # Usuario Activo
        usuario_activo = Usuario(
            academia_id=academia.id,
            nombre="Usuario Activo",
            email="activo@academia.com",
            password=hash_password("password_activo"),
            rol_id=1,
            estado="Activo"
        )
        db.session.add(usuario_activo)

        # Usuario Bloqueado
        usuario_bloqueado = Usuario(
            academia_id=academia.id,
            nombre="Usuario Bloqueado",
            email="bloqueado@academia.com",
            password=hash_password("password_bloqueado"),
            rol_id=1,
            estado="Bloqueado"
        )
        db.session.add(usuario_bloqueado)

        # Usuario de Baja
        usuario_baja = Usuario(
            academia_id=academia.id,
            nombre="Usuario Baja",
            email="baja@academia.com",
            password=hash_password("password_baja"),
            rol_id=1,
            estado="Baja"
        )
        db.session.add(usuario_baja)

        db.session.commit()
        print("[init_db] Usuarios creados: Activo, Bloqueado, Baja")

    # Poblar datos iniciales para Roles
    if db.session.query(Rol).count() == 0:
        rol = Rol(nombre="Admin_plataforma", descripcion="Administrador del sistema")
        db.session.add(rol)
        db.session.commit()
        print(f"[init_db] Rol creado con id={rol.id}")

    # Poblar datos iniciales para Horarios de Curso
    if db.session.query(HorarioCurso).count() == 0:
        horario = HorarioCurso(
            curso_id=curso.id,
            aula_id=aula.id,
            dia_semana="Lunes",
            hora_inicio=time(9, 0),  # Convertir a objeto time
            hora_fin=time(11, 0)    # Convertir a objeto time
        )
        db.session.add(horario)
        db.session.commit()
        print(f"[init_db] Horario de curso creado con id={horario.id}")

    # Poblar datos iniciales para Alumnos
    if db.session.query(Alumno).count() == 0:
        alumno = Alumno(
            academia_id=academia.id,
            nombre="Juan Pérez",
            email="juan.perez@correo.com",
            dni="12345678A",
            telefono="600123456",
            fecha_nacimiento=date(2005, 5, 15),
            direccion="Calle Falsa 123",
            nombre_tutor="María Pérez",
            relaccion_tutor_alumno="Madre",
            telefono_tutor="600654321",
            email_tutor="maria.perez@correo.com"
        )
        db.session.add(alumno)
        db.session.commit()
        print(f"[init_db] Alumno creado con id={alumno.id}")

    # Poblar datos iniciales para Inscripciones
    if db.session.query(Inscripcion).count() == 0:
        inscripcion = Inscripcion(
            alumno_id=alumno.id,
            curso_id=curso.id,
            tarifa_id=tarifa.id,
            fecha_inicio=date(2025, 6, 1)
        )
        db.session.add(inscripcion)
        db.session.commit()
        print(f"[init_db] Inscripción creada con id={inscripcion.id}")

    # Poblar datos iniciales para Curso_Profesores
    if db.session.query(CursoProfesores).count() == 0:
        curso_profesor = CursoProfesores(
            curso_id=curso.id,
            usuario_id=usuario_activo.id,  # Usar el usuario activo
            fecha_alta=db.func.current_timestamp()
        )
        db.session.add(curso_profesor)
        db.session.commit()
        print(f"[init_db] Curso_Profesor creado con id={curso_profesor.id}")

    # Poblar datos iniciales para Sesiones
    if db.session.query(Sesion).count() == 0:
        sesion = Sesion(
            aula_id=aula.id,
            curso_profesor_id=curso_profesor.id,
            timestamp_alta=db.func.current_timestamp(),
            hora_inicio=time(9, 0),  # Convertir a objeto time
            hora_fin=time(11, 0)    # Convertir a objeto time
        )
        db.session.add(sesion)
        db.session.commit()
        print(f"[init_db] Sesión creada con id={sesion.id}")


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
