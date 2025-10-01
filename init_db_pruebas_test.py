from config import Config
from werkzeug.security import generate_password_hash

# Este script sólo gestiona datos de prueba (DML).
# Nunca crea ni borra tablas, índices ni modifica la estructura de la BD.
# Uso previsto: preparar datos de test (INSERT si faltan) y opcionalmente
# borrar filas de las tablas de datos de test con --delete (DELETE sólo).

# Asegurar que las variables de entorno para la DB estén configuradas
# & .\.venv\Scripts\Activate.ps1    --> activar entorno virtual

#$env:DB_ENV='development'     --> configurar entorno de DB (ejemplo)
#& 'C:\Users\Angel FV\Desktop\FORMACION\api-workers-profesores\.venv\Scripts\python.exe' 'C:\Users\Angel FV\Desktop\FORMACION\api-workers-profesores\init_db_pruebas_test.py'

#python init_db_pruebas_test.py    --> # 3) ejecutar el seeder idempotente (no hace CREATE/DROP)
#python init_db_pruebas_test.py --delete   (Ejecutar el script pidiendo además que borre las filas (DELETE ordenado) y luego vuelva a insertar los datos de prueba)
#python init_db_pruebas_test.py --reset    (Alias de --delete: borra filas y vuelve a insertar los datos de prueba. IMPORTANTE: solo borra datos, no hace DROP de tablas ni altera el esquema.)
#python init_db_pruebas_test.py --delete --force (Si alguna vez lanzas --delete contra producción, el script denegará la operación a menos que añadas --force. No lo uses en production salvo que estés absolutamente seguro)

#ejecutar los test de login  (salida -s para mostrar prints)
#python -m pytest tests/usuarios/test_login.py -q -s

# o ejecutar toda la suite
#pytest -q

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

    print('[init_db_pruebas_test] Ejecutando borrado ordenado de filas...')
    try:
        for t in table_names:
            stmt = text(f"DELETE FROM `{t}`;")
            try:
                with db.engine.begin() as conn:
                    conn.execute(stmt)
            except Exception as e:
                # Si la tabla no existe, lo ignoramos y continuamos con las demás.
                msg = str(e)
                if 'doesn\'t exist' in msg or 'does not exist' in msg or '1146' in msg:
                    print(f"[init_db_pruebas_test] Tabla no encontrada, se omite DELETE: {t}")
                    continue
                # Para otros errores, relanzamos
                raise
        print('[init_db_pruebas_test] Borrado ordenado completado.')
        return
    except Exception as e:
        print(f"[init_db_pruebas_test] Borrado ordenado falló: {e}. Intentando con FOREIGN_KEY_CHECKS=0 en MySQL...")
        try:
            with db.engine.begin() as conn:
                conn.execute(text("SET FOREIGN_KEY_CHECKS=0;"))
                for t in table_names:
                    try:
                        conn.execute(text(f"DELETE FROM `{t}`;"))
                    except Exception as e2:
                        msg2 = str(e2)
                        if 'doesn\'t exist' in msg2 or 'does not exist' in msg2 or '1146' in msg2:
                            print(f"[init_db_pruebas_test] (FK off) Tabla no encontrada, se omite DELETE: {t}")
                            continue
                        raise
                conn.execute(text("SET FOREIGN_KEY_CHECKS=1;"))
            print('[init_db_pruebas_test] Borrado con FOREIGN_KEY_CHECKS=0 completado.')
            return
        except Exception as e2:
            print(f"[init_db_pruebas_test] Borrado con FK deshabilitadas también falló: {e2}")
            if not force:
                print('[init_db_pruebas_test] Abortando para evitar daños. Usa --force si realmente quieres forzar.')
                sys.exit(1)
            else:
                print('[init_db_pruebas_test] Forzando borrado final (último recurso).')
                with db.engine.begin() as conn:
                    for t in table_names:
                        try:
                            conn.execute(text(f"DELETE FROM `{t}`;"))
                        except Exception as e3:
                            msg3 = str(e3)
                            if 'doesn\'t exist' in msg3 or 'does not exist' in msg3 or '1146' in msg3:
                                print(f"[init_db_pruebas_test] (force) Tabla no encontrada, omitiendo: {t}")
                                continue
                            # Si aún falla por otra razón, relanzar para que sea visible
                            raise


def seed():
    # Obtener configuración de la base de datos
    db_config = Config.get_database_config()
    print(f"[init_db_pruebas_test] Usando configuración de base de datos: {db_config}")

    # Academia
    academia, created = get_or_create(Academia, nombre="Academia Central")
    if created:
        print(f"[init_db_pruebas_test] Academia creada con id={academia.id}")
    else:
        print("[init_db_pruebas_test] Academia ya existe, no se creó.")

    # Tarifa
    tarifa_filters = dict(academia_id=academia.id, descripcion="Tarifa General")
    tarifa_defaults = dict(precio_base=50.0)
    tarifa, created = get_or_create(Tarifa, defaults=tarifa_defaults, **tarifa_filters)
    if created:
        print(f"[init_db_pruebas_test] Tarifa creada con id={tarifa.id}")
    else:
        print("[init_db_pruebas_test] Tarifa existente, no se creó.")

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
        print(f"[init_db_pruebas_test] Curso creado con id={curso.id}")
    else:
        print("[init_db_pruebas_test] Curso existente, no se creó.")

    # Aula
    aula_filters = dict(academia_id=academia.id, nombre="Aula 101")
    aula_defaults = dict(capacidad_maxima=20)
    aula, created = get_or_create(Aula, defaults=aula_defaults, **aula_filters)
    if created:
        print(f"[init_db_pruebas_test] Aula creada con id={aula.id}")
    else:
        print("[init_db_pruebas_test] Aula existente, no se creó.")

    # Rol
    rol, created = get_or_create(Rol, nombre="Admin_plataforma")
    if created:
        print(f"[init_db_pruebas_test] Rol creado con id={rol.id}")
    else:
        print(f"[init_db_pruebas_test] Rol existente usado id={rol.id}")

    # Crear roles adicionales
    rol_academia, created = get_or_create(Rol, nombre="Admin_academia")
    if created:
        print(f"[init_db_pruebas_test] Rol creado con id={rol_academia.id}")
    else:
        print(f"[init_db_pruebas_test] Rol existente usado id={rol_academia.id}")

    # Rol administrativo
    rol_administrativo, created = get_or_create(Rol, nombre="Administrativo")
    if created:
        print(f"[init_db_pruebas_test] Rol creado con id={rol_administrativo.id}")
    else:
        print(f"[init_db_pruebas_test] Rol existente usado id={rol_administrativo.id}")

    # Usuarios de prueba: crear solo si email no existe
    usuarios_prueba = [
        dict(nombre="Usuario Activo", email="activo@academia.com", password=hash_password("password_activo"), rol_id=rol.id, estado="Activo", academia_id=academia.id),
        dict(nombre="Usuario Bloqueado", email="bloqueado@academia.com", password=hash_password("password_bloqueado"), rol_id=rol.id, estado="Bloqueado", academia_id=academia.id),
        dict(nombre="Usuario Baja", email="baja@academia.com", password=hash_password("password_baja"), rol_id=rol.id, estado="Baja", academia_id=academia.id),
        dict(nombre="Admin Plataforma", email="admin_plataforma@academia.com", password=hash_password("password_admin_plataforma"), rol_id=rol.id, estado="Activo", academia_id=None),
        dict(nombre="Admin Academia", email="admin_academia@academia.com", password=hash_password("password_admin_academia"), rol_id=rol_academia.id, estado="Activo", academia_id=academia.id),
    ]
    for u in usuarios_prueba:
        user_filters = dict(email=u['email'])
        defaults = {k: v for k, v in u.items() if k != 'email'}
        user, created = get_or_create(Usuario, defaults=defaults, **user_filters)
        if created:
            print(f"[init_db_pruebas_test] Usuario creado: {user.email} (id={user.id})")
        else:
            print(f"[init_db_pruebas_test] Usuario ya existe: {user.email}")

    # HorarioCurso
    horario_filters = dict(curso_id=curso.id, aula_id=aula.id, dia_semana="Lunes")
    horario_defaults = dict(hora_inicio=time(9, 0), hora_fin=time(11, 0))
    horario, created = get_or_create(HorarioCurso, defaults=horario_defaults, **horario_filters)
    if created:
        print(f"[init_db_pruebas_test] Horario creado id={horario.id}")

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
        print(f"[init_db_pruebas_test] Alumno creado id={alumno.id}")

    # Inscripcion
    insc_filters = dict(alumno_id=alumno.id, curso_id=curso.id)
    insc_defaults = dict(tarifa_id=tarifa.id, fecha_inicio=date(2025, 6, 1))
    insc, created = get_or_create(Inscripcion, defaults=insc_defaults, **insc_filters)
    if created:
        print(f"[init_db_pruebas_test] Inscripcion creada id={insc.id}")

    # CursoProfesores
    usuario_activo = Usuario.query.filter_by(estado='Activo').first()
    if usuario_activo:
        cp_filters = dict(curso_id=curso.id, usuario_id=usuario_activo.id)
        cp_defaults = dict(fecha_alta=db.func.current_timestamp())
        cp, created = get_or_create(CursoProfesores, defaults=cp_defaults, **cp_filters)
        if created:
            print(f"[init_db_pruebas_test] Curso_Profesor creado id={cp.id}")

    # Sesion
    if 'cp' in locals() and cp:
        ses_filters = dict(aula_id=aula.id, curso_profesor_id=cp.id)
        ses_defaults = dict(timestamp_alta=db.func.current_timestamp(), hora_inicio=time(9, 0), hora_fin=time(11, 0))
        ses, created = get_or_create(Sesion, defaults=ses_defaults, **ses_filters)
        if created:
            print(f"[init_db_pruebas_test] Sesion creada id={ses.id}")

    # Crear academias
    academia_1, created = get_or_create(Academia, nombre='Academia 1')
    if created:
        print("[init_db_pruebas_test] Academia creada: Academia 1")
    else:
        print("[init_db_pruebas_test] Academia ya existe: Academia 1")

    academia_2, created = get_or_create(Academia, nombre='Academia 2')
    if created:
        print("[init_db_pruebas_test] Academia creada: Academia 2")
    else:
        print("[init_db_pruebas_test] Academia ya existe: Academia 2")

    # Crear usuarios administradores de la plataforma
    usuarios_plataforma = [
        dict(email='admin_plataforma_1@academia.com', nombre='Admin Plataforma 1', password=generate_password_hash('password_admin_plataforma_1'), rol_id=rol.id, estado='activo', academia_id=None),
        dict(email='admin_plataforma_2@academia.com', nombre='Admin Plataforma 2', password=generate_password_hash('password_admin_plataforma_2'), rol_id=rol.id, estado='bloqueado', academia_id=None),
    ]

    for u in usuarios_plataforma:
        user_filters = dict(email=u['email'])
        defaults = {k: v for k, v in u.items() if k != 'email'}
        user, created = get_or_create(Usuario, defaults=defaults, **user_filters)
        if created:
            print(f"[init_db_pruebas_test] Usuario creado: {user.email} (id={user.id})")
        else:
            print(f"[init_db_pruebas_test] Usuario ya existe: {user.email}")

    # Crear usuarios de Academia 1
    usuarios_academia_1 = [
        dict(email='admin_academia_1@academia.com', nombre='Admin Academia 1', password=generate_password_hash('password_admin_academia_1'), rol_id=rol_academia.id, estado='activo', academia_id=academia_1.id),
        dict(email='user_academia_1_1@academia.com', nombre='User Academia 1.1', password=generate_password_hash('password_user_academia_1_1'), rol_id=rol_administrativo.id, estado='bloqueado', academia_id=academia_1.id),
        dict(email='user_academia_1_2@academia.com', nombre='User Academia 1.2', password=generate_password_hash('password_user_academia_1_2'), rol_id=rol_administrativo.id, estado='bloqueado', academia_id=academia_1.id),
    ]

    for u in usuarios_academia_1:
        user_filters = dict(email=u['email'])
        defaults = {k: v for k, v in u.items() if k != 'email'}
        user, created = get_or_create(Usuario, defaults=defaults, **user_filters)
        if created:
            print(f"[init_db_pruebas_test] Usuario creado: {user.email} (id={user.id})")
        else:
            print(f"[init_db_pruebas_test] Usuario ya existe: {user.email}")

    # Crear usuarios de Academia 2
    usuarios_academia_2 = [
        dict(email='admin_academia_2@academia.com', nombre='Admin Academia 2', password=generate_password_hash('password_admin_academia_2'), rol_id=rol_academia.id, estado='activo', academia_id=academia_2.id),
        dict(email='user_academia_2_1@academia.com', nombre='User Academia 2.1', password=generate_password_hash('password_user_academia_2_1'), rol_id=rol_administrativo.id, estado='activo', academia_id=academia_2.id),  # Changed to activo
        dict(email='user_academia_2_2@academia.com', nombre='User Academia 2.2', password=generate_password_hash('password_user_academia_2_2'), rol_id=rol_administrativo.id, estado='activo', academia_id=academia_2.id),  # Changed to activo
    ]

    for u in usuarios_academia_2:
        user_filters = dict(email=u['email'])
        defaults = {k: v for k, v in u.items() if k != 'email'}
        user, created = get_or_create(Usuario, defaults=defaults, **user_filters)
        if created:
            print(f"[init_db_pruebas_test] Usuario creado: {user.email} (id={user.id})")
        else:
            print(f"[init_db_pruebas_test] Usuario ya existe: {user.email}")

    # Mostrar resumen al final del seeding con roles primero
    def mostrar_resumen():
        print("\n[Resumen de datos creados]")

        # Listar todos los roles
        print("\nRoles:")
        roles = Rol.query.all()
        for rol in roles:
            print(f"  Rol ID: {rol.id}, Nombre: {rol.nombre}")

        # Listar usuarios administradores de la plataforma
        print("\nUsuarios Administradores de la Plataforma:")
        usuarios_plataforma = Usuario.query.filter_by(academia_id=None).all()
        for usuario in usuarios_plataforma:
            rol_usuario = db.session.get(Rol, usuario.rol_id)
            rol_descripcion = rol_usuario.nombre if rol_usuario else "Sin rol"
            print(f"  Usuario ID: {usuario.id}, Nombre: {usuario.nombre}, Estado: {usuario.estado}, Rol: {rol_descripcion}")

        # Listar academias y sus usuarios
        academias = Academia.query.all()
        for academia in academias:
            print(f"\nAcademia ID: {academia.id}, Nombre: {academia.nombre}")

            # Listar usuarios de la academia con descripción del rol
            usuarios = Usuario.query.filter_by(academia_id=academia.id).all()
            print("  Usuarios:")
            for usuario in usuarios:
                rol_usuario = db.session.get(Rol, usuario.rol_id)
                rol_descripcion = rol_usuario.nombre if rol_usuario else "Sin rol"
                print(f"    Usuario ID: {usuario.id}, Nombre: {usuario.nombre}, Estado: {usuario.estado}, Rol: {rol_descripcion}")

    # Llamar a la función de resumen después del seeding
    mostrar_resumen()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga datos de prueba (solo DML). No modifica la estructura de la BD.")
    parser.add_argument(
        "--delete",
        action="store_true",
        help="ELIMINA (DELETE) todas las filas de las tablas configuradas y luego inserta los datos de prueba.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="ALIAS: igual que --delete. Borra filas y vuelve a insertar datos de prueba. NO borra tablas ni modifica esquema.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forzar operaciones destructivas (DELETE) incluso si DB_ENV está en production (usar con cuidado).",
    )
    args = parser.parse_args()

    with app.app_context():
        # Configurar la base de datos según el entorno
        Config.set_environment_variables()

        if args.delete or args.reset:
            # Safety checks: no borrar en production a menos que se fuerce
            if Config.DB_ENV == 'production' and not args.force:
                print("[init_db_pruebas_test] ERROR: --delete no está permitido en production sin --force. Abortando.")
                sys.exit(1)
            delete_all_rows(force=args.force)
            seed()
            print("[init_db_pruebas_test] --delete completado: filas eliminadas y datos de prueba insertados.")
        else:
            # Seed idempotente por registro (solo DML)
            seed()
            print("Init DB pruebas: datos de prueba asegurados (solo DML)")
