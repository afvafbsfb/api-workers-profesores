# Stub para evitar error de importación
class PagoMySQLRepository:
    def save(self, pago):
        from app import models
        PagoModel = models.Pago
        db = models.db
        Inscripcion = models.Inscripcion
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
from datetime import date
# vlodeiro/secretaria/infrastructure/repositorio_mysql.py

from datetime import date

class PagoMySQLRepository:
    def save(self, pago):
        from app import models
        PagoModel = models.Pago
        db = models.db
        Inscripcion = models.Inscripcion
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

class AlumnoMySQLRepository:
    def get_by_id(self, alumno_id: str):
        from app import models
        AlumnoModel = models.Alumno
        print(f"[MySQL] Obteniendo alumno con ID: {alumno_id}")
        alumno = AlumnoModel.query.filter_by(id=int(alumno_id)).first()
        if alumno:
            return alumno
        return None

    def save(self, alumno):
        print(f"[MySQL] Guardando alumno: {alumno.nombre}")
        # Simulación de guardado en DB
        pass

class ClaseMySQLRepository:
    def get_by_id(self, clase_id: str):
        from app import models
        Clase = models.Clase
        clase = Clase.query.filter_by(id=clase_id).first()
        return clase

    def inscribir_alumno(self, clase_id: int, alumno_id: int, tarifa_id: int) -> bool:
        from app import models
        Inscripcion = models.Inscripcion
        Clase = models.Clase
        db = models.db
        Tarifa = models.Tarifa
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
        from app import models
        return models.Turno.query.filter_by(empresa_id=empresa_id, activo=True).all()

class TurnoMySQLRepository:
    def get_by_id(self, turno_id: str):
        from app import models
        turno = models.Turno.query.filter_by(id=turno_id).first()
        return turno

    def listar_turnos(self, empresa_id=1):
        from app import models
        return models.Turno.query.filter_by(empresa_id=empresa_id, activo=True).all()

    def inscribir_alumno(self, turno_id: int, alumno_id: int, tarifa_id: int) -> bool:
        from app import models
        turno = models.Turno.query.filter_by(id=turno_id).first()
        if not turno:
            return False
        # Verificar capacidad
        inscripciones_activas = models.Inscripcion.query.filter_by(turno_id=turno_id, fecha_fin=None).count()
        if inscripciones_activas >= turno.capacidad:
            return False
        # Validar tarifa explícita
        tarifa = models.Tarifa.query.filter_by(id=tarifa_id, activo=True).first()
        if not tarifa:
            return False
        # Registrar inscripción
        inscripcion = models.Inscripcion(alumno_id=alumno_id, turno_id=turno_id, tarifa_id=tarifa.id, fecha_inicio=date.today(), fecha_fin=None)
        models.db.session.add(inscripcion)
        models.db.session.commit()
        return True

    # Listar alumnos inscritos en un turno
    def alumnos_inscritos(self, turno_id: int):
        from app import models
        Inscripcion = models.Inscripcion
        Alumno = models.Alumno
        return (
            Inscripcion.query.filter_by(turno_id=turno_id, fecha_fin=None)
            .join(Alumno, Inscripcion.alumno_id == Alumno.id)
            .with_entities(Alumno.id, Alumno.nombre, Alumno.email, Inscripcion.id.label('inscripcion_id'))
            .all()
        )

    # Dar de baja (cerrar) una inscripción
    def baja_inscripcion(self, inscripcion_id: int) -> bool:
        from app import models
        Inscripcion = models.Inscripcion
        db = models.db
        ins = Inscripcion.query.filter_by(id=inscripcion_id, fecha_fin=None).first()
        if not ins:
            return False
        ins.fecha_fin = date.today()
        db.session.commit()
        return True
