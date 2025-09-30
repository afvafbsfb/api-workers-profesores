from config import Config

# Asegurar que las variables de entorno para la DB estén configuradas
Config.set_environment_variables()

from main import app
from src.shared.security import hash_password

from models import (
    db,
    Academia,
    Curso,
    Aula,
    Usuario,
    Rol,
    HorarioCurso,
    Alumno,
    Inscripcion,
    CursoProfesores,
    Sesion,
    Tarifa,
    Token,
    MovimientosExtracto,
    Extractos,
    AnotacionesAlumnoSesion,
    DescuentosTarifa,
    FamiliasAlumnos,
    TrabajadorVirtual,
)
from datetime import date, time
import argparse
from sqlalchemy import text
import sys

app.app_context().push()


def get_or_create(model, defaults=None, **filters):
    """Busca un registro por filtros, lo crea con defaults si no existe.

    Devuelve (instance, created_bool)
    """
    instance = model.query.filter_by(**filters).first()
    if instance:
        return instance, False
    params = dict(filters)
    if defaults:
        params.update(defaults)
    instance = model(**params)
    db.session.add(instance)
    try:
        db.session.commit()
        return instance, True
    except Exception:
        db.session.rollback()
        # Intentar recuperar si otro proceso creó el registro simultáneamente
        instance = model.query.filter_by(**filters).first()
        if instance:
            return instance, False
        raise


def delete_all_rows(force=False):
    """Borra todas las filas (no borra tablas). Intenta un borrado ordenado y cae a
    desactivar FOREIGN_KEY_CHECKS si hay problemas.
    """
    # Orden recomendado: hijos primero
    table_names = [
        'tokens',
        'Movimientos_Extracto',
        'Extractos',
        'AnotacionesAlumnoSesion',
        'Inscripcion',
        'Descuentos_tarifa',
        'HorarioCurso',
        'Sesion',
        'Curso_Profesores',
        'familias_alumnos',
        'Alumno',
        'Usuario',
        'Curso',
        'Tarifa',
        'Aula',
        'TrabajadorVirtual',
        'Rol_Usuario',
        'Academia',
    ]

    print('[init_db] Ejecutando borrado ordenado de filas...')
    try:
        for t in table_names:
            stmt = text(f"DELETE FROM `{t}`;")
            with db.engine.begin() as conn:
                conn.execute(stmt)
        print('[init_db] Borrado ordenado completado.')
        return
    except Exception as e:
        print(f"[init_db] Borrado ordenado falló: {e}. Intentando con FOREIGN_KEY_CHECKS=0 en MySQL...")
        try:
            with db.engine.begin() as conn:
                conn.execute(text("SET FOREIGN_KEY_CHECKS=0;"))
                for t in table_names:
                    conn.execute(text(f"DELETE FROM `{t}`;"))
                conn.execute(text("SET FOREIGN_KEY_CHECKS=1;"))
            print('[init_db] Borrado con FOREIGN_KEY_CHECKS=0 completado.')
            return
        except Exception as e2:
            print(f"[init_db] Borrado con FK deshabilitadas también falló: {e2}")
            if not force:
                print('[init_db] Abortando para evitar daños. Usa --force si realmente quieres forzar.')
                sys.exit(1)
            else:
                print('[init_db] Forzando borrado final (último recurso).')
                with db.engine.begin() as conn:
                    for t in table_names:
                        conn.execute(text(f"DELETE FROM `{t}`;"))


def seed():
    # Obtener configuración de la base de datos
    db_config = Config.get_database_config()
    print(f"[init_db] Usando configuración de base de datos: {db_config}")

    # Academia
    academia, created = get_or_create(Academia, nombre="Academia Central")
    if created:
        print(f"[init_db] Academia creada con id={academia.id}")
    else:
        print("[init_db] Academia ya existe, no se creó.")

    # Tarifa
    tarifa_filters = dict(academia_id=academia.id, descripcion="Tarifa General")
    tarifa_defaults = dict(precio_base=50.0)
    tarifa, created = get_or_create(Tarifa, defaults=tarifa_defaults, **tarifa_filters)
    if created:
        print(f"[init_db] Tarifa creada con id={tarifa.id}")
    else:
        print("[init_db] Tarifa existente, no se creó.")

    # Curso
    curso_filters = dict(academia_id=academia.id, nombre="Curso de Verano")
    curso_defaults = dict(
        anio_academico="2025-2026",
        fecha_inicio=date(2025, 6, 1),
        fecha_fin=date(2025, 8, 31),
        acepta_nuevos_alumnos=True,
        capacidad_maxima=30,
        tarifa_id=tarifa.id,
        tipo_alumno="Juvenil",
        estado="Activo",
    )
    curso, created = get_or_create(Curso, defaults=curso_defaults, **curso_filters)
    if created:
        print(f"[init_db] Curso creado con id={curso.id}")
    else:
        print("[init_db] Curso existente, no se creó.")

    # Aula
    aula_filters = dict(academia_id=academia.id, nombre="Aula 101")
    aula_defaults = dict(capacidad_maxima=20)
    aula, created = get_or_create(Aula, defaults=aula_defaults, **aula_filters)
    if created:
        print(f"[init_db] Aula creada con id={aula.id}")
    else:
        print("[init_db] Aula existente, no se creó.")

    # Rol
    rol, created = get_or_create(Rol, nombre="Admin_plataforma")
    if created:
        print(f"[init_db] Rol creado con id={rol.id}")
    else:
        print(f"[init_db] Rol existente usado id={rol.id}")

    # Usuarios de prueba: crear solo si email no existe
    usuarios_prueba = [
        dict(nombre="Usuario Activo", email="activo@academia.com", password=hash_password("password_activo"), rol_id=rol.id, estado="Activo", academia_id=academia.id),
        dict(nombre="Usuario Bloqueado", email="bloqueado@academia.com", password=hash_password("password_bloqueado"), rol_id=rol.id, estado="Bloqueado", academia_id=academia.id),
        dict(nombre="Usuario Baja", email="baja@academia.com", password=hash_password("password_baja"), rol_id=rol.id, estado="Baja", academia_id=academia.id),
    ]
    for u in usuarios_prueba:
        user_filters = dict(email=u['email'])
        defaults = {k: v for k, v in u.items() if k != 'email'}
        user, created = get_or_create(Usuario, defaults=defaults, **user_filters)
        if created:
            print(f"[init_db] Usuario creado: {user.email} (id={user.id})")
        else:
            print(f"[init_db] Usuario ya existe: {user.email}")

    # HorarioCurso
    horario_filters = dict(curso_id=curso.id, aula_id=aula.id, dia_semana="Lunes")
    horario_defaults = dict(hora_inicio=time(9, 0), hora_fin=time(11, 0))
    horario, created = get_or_create(HorarioCurso, defaults=horario_defaults, **horario_filters)
    if created:
        print(f"[init_db] Horario creado id={horario.id}")

    # Alumno
    alumno_filters = dict(email="juan.perez@correo.com")
    alumno_defaults = dict(
        academia_id=academia.id,
        nombre="Juan Pérez",
        dni="12345678A",
        telefono="600123456",
        fecha_nacimiento=date(2005, 5, 15),
        direccion="Calle Falsa 123",
        nombre_tutor="María Pérez",
        relaccion_tutor_alumno="Madre",
        telefono_tutor="600654321",
        email_tutor="maria.perez@correo.com",
    )
    alumno, created = get_or_create(Alumno, defaults=alumno_defaults, **alumno_filters)
    if created:
        print(f"[init_db] Alumno creado id={alumno.id}")

    # Inscripcion
    insc_filters = dict(alumno_id=alumno.id, curso_id=curso.id)
    insc_defaults = dict(tarifa_id=tarifa.id, fecha_inicio=date(2025, 6, 1))
    insc, created = get_or_create(Inscripcion, defaults=insc_defaults, **insc_filters)
    if created:
        print(f"[init_db] Inscripcion creada id={insc.id}")

    # CursoProfesores
    # Asociar el primer usuario activo conocido
    usuario_activo = Usuario.query.filter_by(estado='Activo').first()
    if usuario_activo:
        cp_filters = dict(curso_id=curso.id, usuario_id=usuario_activo.id)
        cp_defaults = dict(fecha_alta=db.func.current_timestamp())
        cp, created = get_or_create(CursoProfesores, defaults=cp_defaults, **cp_filters)
        if created:
            print(f"[init_db] Curso_Profesor creado id={cp.id}")

    # Sesion
    if 'cp' in locals() and cp:
        ses_filters = dict(aula_id=aula.id, curso_profesor_id=cp.id)
        ses_defaults = dict(timestamp_alta=db.func.current_timestamp(), hora_inicio=time(9, 0), hora_fin=time(11, 0))
        ses, created = get_or_create(Sesion, defaults=ses_defaults, **ses_filters)
        if created:
            print(f"[init_db] Sesion creada id={ses.id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inicializa la base de datos y carga datos de prueba.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="BORRA todas las tablas y las recrea antes de cargar datos (¡destructivo!).",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="ELIMINA (DELETE) todas las filas de las tablas configuradas y luego inserta los datos de prueba.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forzar operaciones destructivas incluso si DB_ENV está en production (usar con cuidado).",
    )
    args = parser.parse_args()

    with app.app_context():
        # Configurar la base de datos según el entorno
        Config.set_environment_variables()

        if args.reset:
            print("[init_db] --reset solicitado: borrando todas las tablas...")
            db.drop_all()
        # Crea tablas si no existen (no es destructivo)
        db.create_all()

        # If --delete specified: delete rows then seed
        if args.delete:
            # Safety checks: no borrar en production a menos que se fuerce
            if Config.DB_ENV == 'production' and not args.force:
                print("[init_db] ERROR: --delete no está permitido en production sin --force. Abortando.")
                sys.exit(1)
            delete_all_rows(force=args.force)
            seed()
            print("[init_db] --delete completado: filas eliminadas y datos de prueba insertados.")
        else:
            # Seed idempotente por registro
            seed()
            if args.reset:
                print("[init_db] Reset completado: tablas recreadas y datos de prueba cargados")
            else:
                print("Init DB: tablas aseguradas y datos iniciales listos (idempotente)")


# End of file
