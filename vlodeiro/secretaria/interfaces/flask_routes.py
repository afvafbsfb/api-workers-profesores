

# vlodeiro/secretaria/interfaces/flask_routes.py

from flask import Blueprint, request, jsonify, current_app
from marshmallow import Schema, fields, ValidationError
from vlodeiro.secretaria.application.inscribir_alumno import InscribirAlumno
from vlodeiro.secretaria.application.registrar_pago import RegistrarPago
from vlodeiro.secretaria.infrastructure.repositorio_mysql import AlumnoMySQLRepository, TurnoMySQLRepository, PagoMySQLRepository

secretaria_bp = Blueprint('secretaria', __name__)

# Inicialización de repositorios y casos de uso
alumno_repo = AlumnoMySQLRepository()
turno_repo = TurnoMySQLRepository()
pago_repo = PagoMySQLRepository()

inscribir_alumno_use_case = InscribirAlumno(alumno_repo, turno_repo)
registrar_pago_use_case = RegistrarPago(pago_repo)

# Endpoint para consultar turnos y plazas libres
@secretaria_bp.route('/turnos_libres', methods=['GET'])
def turnos_libres():
    from models import Turno, Inscripcion
    turnos = Turno.query.all()
    resultado = []
    for turno in turnos:
        inscritos = Inscripcion.query.filter_by(turno_id=turno.id).count()
        libres = max(turno.capacidad - inscritos, 0)
        resultado.append({
            "id": turno.id,
            "dia": turno.dia_semana,
            "hora_inicio": turno.hora_inicio,
            "hora_fin": turno.hora_fin,
            "tipo": turno.tipo_alumno,
            "capacidad": turno.capacidad,
            "inscritos": inscritos,
            "plazas_libres": libres
        })
    return jsonify(resultado)

# Esquema para inscribir
class InscribirSchema(Schema):
    alumno_id = fields.Int(required=True)
    turno_id = fields.Int(required=True)

# Esquema para registrar pago
class RegistrarPagoSchema(Schema):
    alumno_id = fields.Int(required=True)
    importe = fields.Float(required=True)
    concepto = fields.Str(required=True)

@secretaria_bp.route('/inscribir', methods=['POST'])
def inscribir():
    data = request.get_json()
    try:
        validated = InscribirSchema().load(data)
    except ValidationError as ve:
        return jsonify({'error': 'Datos inválidos', 'detalles': ve.messages}), 400
    alumno_id = validated['alumno_id']
    turno_id = validated['turno_id']
    # Depuración avanzada
    debug_info = {}
    alumno = alumno_repo.get_by_id(str(alumno_id))
    if not alumno:
        debug_info['motivo'] = 'alumno_no_encontrado'
        return jsonify({'error': 'No se pudo inscribir al alumno', 'debug': debug_info}), 400
    turno = turno_repo.get_by_id(str(turno_id))
    if not turno:
        debug_info['motivo'] = 'turno_no_encontrado'
        return jsonify({'error': 'No se pudo inscribir al alumno', 'debug': debug_info}), 400
    # Verificar capacidad
    from models import Inscripcion
    inscripciones = Inscripcion.query.filter_by(turno_id=turno_id).count()
    debug_info['inscripciones'] = inscripciones
    debug_info['capacidad'] = getattr(turno, 'capacidad', None)
    if inscripciones >= getattr(turno, 'capacidad', 0):
        debug_info['motivo'] = 'turno_lleno'
        return jsonify({'error': 'No se pudo inscribir al alumno', 'debug': debug_info}), 400
    # Verificar inscripción previa
    ya_inscrito = Inscripcion.query.filter_by(alumno_id=alumno_id, turno_id=turno_id).first()
    if ya_inscrito:
        debug_info['motivo'] = 'alumno_ya_inscrito'
        return jsonify({'error': 'No se pudo inscribir al alumno', 'debug': debug_info}), 400
    # Ejecutar inscripción
    if inscribir_alumno_use_case.execute(alumno_id, turno_id):
        return jsonify({'message': 'Alumno inscrito correctamente'}), 200
    debug_info['motivo'] = 'fallo_desconocido'
    return jsonify({'error': 'No se pudo inscribir al alumno', 'debug': debug_info}), 400

@secretaria_bp.route('/registrar_pago', methods=['POST'])
def registrar_pago():
    data = request.get_json()
    try:
        validated = RegistrarPagoSchema().load(data)
    except ValidationError as ve:
        return jsonify({'error': 'Datos inválidos', 'detalles': ve.messages}), 400
    alumno_id = validated['alumno_id']
    importe = validated['importe']
    concepto = validated['concepto']
    pago = registrar_pago_use_case.execute(alumno_id, importe, concepto)
    return jsonify({'message': 'Pago registrado correctamente', 'pago_id': pago.id}), 200

# --- NUEVO ENDPOINT /turnos EN BLUEPRINT ---
from vlodeiro.secretaria.infrastructure.repositorio_mysql import TurnoMySQLRepository
@secretaria_bp.route('/turnos', methods=['GET'])
def listar_turnos():
    try:
        repo = TurnoMySQLRepository()
        turnos = repo.listar_turnos()
        print("Turnos encontrados:", turnos)
        return jsonify([
            {
                "id": getattr(t, "id", None),
                "dia": getattr(t, "dia_semana", None),
                "hora_inicio": getattr(t, "hora_inicio", None),
                "hora_fin": getattr(t, "hora_fin", None),
                "tipo": getattr(t, "tipo_alumno", None),
                "duracion_min": getattr(t, "duracion_min", None),
                "capacidad": getattr(t, "capacidad", None)
            } for t in turnos
        ])
    except Exception as e:
        import traceback
        print("ERROR EN TURNOS:", e)
        print(traceback.format_exc())
        # Sanitiza error en producción
        if current_app.config.get("ENV") == "production":
            return jsonify({"ok": False, "error": "internal_error"}), 500
        return jsonify({"ok": False, "error": str(e), "trace": traceback.format_exc()}), 500


# --- NUEVOS ENDPOINTS: ALUMNOS ---
@secretaria_bp.route('/alumnos', methods=['GET'])
def listar_alumnos():
    try:
        from models import Alumno
        alumnos = Alumno.query.all()
        return jsonify([
            {
                "id": a.id,
                "nombre": a.nombre,
                "email": a.email,
            } for a in alumnos
        ])
    except Exception as e:
        import traceback
        if current_app.config.get("ENV") == "production":
            return jsonify({"ok": False, "error": "internal_error"}), 500
        return jsonify({"ok": False, "error": str(e), "trace": traceback.format_exc()}), 500


@secretaria_bp.route('/alumnos/<int:alumno_id>', methods=['GET'])
def obtener_alumno(alumno_id: int):
    try:
        from models import Alumno
        a = Alumno.query.filter_by(id=alumno_id).first()
        if not a:
            return jsonify({"error": "Alumno no encontrado"}), 404
        return jsonify({"id": a.id, "nombre": a.nombre, "email": a.email})
    except Exception as e:
        import traceback
        if current_app.config.get("ENV") == "production":
            return jsonify({"ok": False, "error": "internal_error"}), 500
        return jsonify({"ok": False, "error": str(e), "trace": traceback.format_exc()}), 500


@secretaria_bp.route('/alumnos/buscar', methods=['GET'])
def buscar_alumnos_por_nombre():
    try:
        nombre = request.args.get('nombre')
        if not nombre:
            return jsonify({"error": "Parámetro 'nombre' requerido"}), 400
        from models import Alumno
        from sqlalchemy import func
        patrones = f"%{nombre}%"
        alumnos = Alumno.query.filter(func.lower(Alumno.nombre).like(func.lower(patrones))).all()
        return jsonify([
            {"id": a.id, "nombre": a.nombre, "email": a.email} for a in alumnos
        ])
    except Exception as e:
        import traceback
        if current_app.config.get("ENV") == "production":
            return jsonify({"ok": False, "error": "internal_error"}), 500
        return jsonify({"ok": False, "error": str(e), "trace": traceback.format_exc()}), 500
