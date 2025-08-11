# Stub para evitar error de importación
class PagoMySQLRepository:
    def save(self, pago):
        from models import Pago as PagoModel, db, Inscripcion
        # Buscar la inscripción activa del alumno
        inscripcion = Inscripcion.query.filter_by(alumno_id=pago.alumno_id, fecha_fin=None).first()
        if not inscripcion:
            raise Exception("No existe inscripción activa para el alumno")
        # Crear instancia del modelo Pago para la base de datos
        pago_db = PagoModel(
            inscripcion_id=inscripcion.id,
            fecha_pago=pago.fecha,
            monto=pago.importe,
            metodo=pago.concepto  # Usamos 'concepto' como método de pago
        )
        db.session.add(pago_db)
        db.session.commit()
        # Asignar el id generado en la base de datos al objeto de dominio
        pago.id = pago_db.id
        return pago_db
# vlodeiro/secretaria/infrastructure/repositorio_mysql.py

# Este archivo contendría la implementación de los repositorios
# que interactúan con una base de datos MySQL.
# Aquí se traducirían los objetos de dominio a estructuras de base de datos
# y viceversa.


from models import Turno
from datetime import date

class AlumnoMySQLRepository:
    def get_by_id(self, alumno_id: str):
        print(f"[MySQL] Obteniendo alumno con ID: {alumno_id}")
        from models import Alumno as AlumnoModel
        alumno = AlumnoModel.query.filter_by(id=int(alumno_id)).first()
        if alumno:
            # Devuelve un objeto compatible con el dominio si es necesario
            return alumno
        return None

    def save(self, alumno):
        print(f"[MySQL] Guardando alumno: {alumno.nombre}")
        # Simulación de guardado en DB
        pass

class ClaseMySQLRepository:

    def get_by_id(self, clase_id: str):
        from models import Clase
        clase = Clase.query.filter_by(id=clase_id).first()
        return clase

    def inscribir_alumno(self, clase_id: int, alumno_id: int, tarifa_id: int) -> bool:
        from models import Inscripcion, Clase, db, Tarifa
        clase = Clase.query.filter_by(id=clase_id).first()
        if not clase:
            return False
        # Verificar capacidad
        inscripciones = Inscripcion.query.filter_by(turno_id=clase_id).count()
        if inscripciones >= clase.capacidad:
            return False
        # Validar tarifa explícita
        tarifa = Tarifa.query.filter_by(id=tarifa_id, activo=True).first()
        if not tarifa:
            return False
        # Registrar inscripción
        inscripcion = Inscripcion(alumno_id=alumno_id, turno_id=clase_id, tarifa_id=tarifa.id, fecha_inicio=date.today(), fecha_fin=None)
        db.session.add(inscripcion)
        db.session.commit()
        return True

    def listar_turnos(self, empresa_id=1):
        return Turno.query.filter_by(empresa_id=empresa_id, activo=True).all()

class TurnoMySQLRepository:
    def get_by_id(self, turno_id: str):
        from models import Turno
        turno = Turno.query.filter_by(id=turno_id).first()
        return turno

    def listar_turnos(self, empresa_id=1):
        from models import Turno
        return Turno.query.filter_by(empresa_id=empresa_id, activo=True).all()

    def inscribir_alumno(self, turno_id: int, alumno_id: int, tarifa_id: int) -> bool:
        from models import Inscripcion, Turno, db, Tarifa
        turno = Turno.query.filter_by(id=turno_id).first()
        if not turno:
            return False
        # Verificar capacidad
        inscripciones_activas = Inscripcion.query.filter_by(turno_id=turno_id, fecha_fin=None).count()
        if inscripciones_activas >= turno.capacidad:
            return False
        # Validar tarifa explícita
        tarifa = Tarifa.query.filter_by(id=tarifa_id, activo=True).first()
        if not tarifa:
            return False
        # Registrar inscripción
        inscripcion = Inscripcion(alumno_id=alumno_id, turno_id=turno_id, tarifa_id=tarifa.id, fecha_inicio=date.today(), fecha_fin=None)
        db.session.add(inscripcion)
        db.session.commit()
        return True

    # Listar alumnos inscritos en un turno
    def alumnos_inscritos(self, turno_id: int):
        from models import Inscripcion, Alumno
        return (
            Inscripcion.query.filter_by(turno_id=turno_id, fecha_fin=None)
            .join(Alumno, Inscripcion.alumno_id == Alumno.id)
            .with_entities(Alumno.id, Alumno.nombre, Alumno.email, Inscripcion.id.label('inscripcion_id'))
            .all()
        )

    # Dar de baja (cerrar) una inscripción
    def baja_inscripcion(self, inscripcion_id: int) -> bool:
        from models import Inscripcion, db
        ins = Inscripcion.query.filter_by(id=inscripcion_id, fecha_fin=None).first()
        if not ins:
            return False
        ins.fecha_fin = date.today()
        db.session.commit()
        return True
