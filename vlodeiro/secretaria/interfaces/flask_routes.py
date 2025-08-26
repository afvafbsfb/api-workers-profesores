

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
    tarifa_id = fields.Int(required=True)

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
    tarifa_id = validated['tarifa_id']
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
    # Validar tarifa: existe, activa y pertenece a la misma empresa
    from models import Tarifa
    tarifa = Tarifa.query.filter_by(id=tarifa_id, activo=True).first()
    if not tarifa:
        debug_info['motivo'] = 'tarifa_no_valida'
        return jsonify({'error': 'Tarifa no válida o inactiva'}), 400
    if getattr(tarifa, 'empresa_id', None) != getattr(turno, 'empresa_id', None):
        debug_info['motivo'] = 'tarifa_empresa_mismatch'
        return jsonify({'error': 'La tarifa no pertenece a la misma empresa del turno', 'debug': debug_info}), 400
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
    # Ejecutar inscripción con manejo de errores
    try:
        if inscribir_alumno_use_case.execute(alumno_id, turno_id, tarifa_id):
            return jsonify({'message': 'Alumno inscrito correctamente'}), 200
    except Exception as e:
        # Evitar 500 por errores de integridad/relaciones
        debug_info['motivo'] = 'excepcion_en_inscripcion'
        debug_info['detalle'] = str(e)
        return jsonify({'error': 'No se pudo inscribir al alumno', 'debug': debug_info}), 400
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

# --- ENDPOINTS TARIFAS ---
@secretaria_bp.route('/tarifas', methods=['GET'])
def listar_tarifas():
    try:
        from models import Tarifa
        tarifas = Tarifa.query.all()
        return jsonify([
            {
                "id": t.id,
                "empresa_id": t.empresa_id,
                "descripcion": t.descripcion,
                "duracion_min": t.duracion_min,
                "precio_base": t.precio_base,
                "descuento": t.descuento,
                "activo": t.activo,
            } for t in tarifas
        ])
    except Exception as e:
        import traceback
        if current_app.config.get("ENV") == "production":
            return jsonify({"ok": False, "error": "internal_error"}), 500
        return jsonify({"ok": False, "error": str(e), "trace": traceback.format_exc()}), 500

@secretaria_bp.route('/tarifas', methods=['POST'])
def crear_tarifa():
    try:
        from models import Tarifa, db
        data = request.get_json() or {}
        required = ["empresa_id", "descripcion", "duracion_min", "precio_base"]
        if not all(k in data for k in required):
            return jsonify({"error": "Faltan campos requeridos", "requeridos": required}), 400
        t = Tarifa(
            empresa_id=int(data["empresa_id"]),
            descripcion=data.get("descripcion"),
            duracion_min=int(data["duracion_min"]),
            precio_base=float(data["precio_base"]),
            descuento=float(data.get("descuento", 0)),
            activo=bool(data.get("activo", True)),
        )
        db.session.add(t)
        db.session.commit()
        return jsonify({"message": "Tarifa creada", "id": t.id}), 201
    except Exception as e:
        import traceback
        if current_app.config.get("ENV") == "production":
            return jsonify({"ok": False, "error": "internal_error"}), 500
        return jsonify({"ok": False, "error": str(e), "trace": traceback.format_exc()}), 500

@secretaria_bp.route('/tarifas/<int:tarifa_id>', methods=['PUT'])
def actualizar_tarifa(tarifa_id: int):
    try:
        from models import Tarifa, db
        data = request.get_json() or {}
        t = Tarifa.query.filter_by(id=tarifa_id).first()
        if not t:
            return jsonify({"error": "Tarifa no encontrada"}), 404
        for field in ["empresa_id", "descripcion", "duracion_min", "precio_base", "descuento", "activo"]:
            if field in data:
                setattr(t, field, data[field])
        db.session.commit()
        return jsonify({"message": "Tarifa actualizada"})
    except Exception as e:
        import traceback
        if current_app.config.get("ENV") == "production":
            return jsonify({"ok": False, "error": "internal_error"}), 500
        return jsonify({"ok": False, "error": str(e), "trace": traceback.format_exc()}), 500

@secretaria_bp.route('/tarifas/<int:tarifa_id>', methods=['DELETE'])
def eliminar_tarifa(tarifa_id: int):
    try:
        from models import Tarifa, db
        t = Tarifa.query.filter_by(id=tarifa_id).first()
        if not t:
            return jsonify({"error": "Tarifa no encontrada"}), 404
        db.session.delete(t)
        db.session.commit()
        return jsonify({"message": "Tarifa eliminada"})
    except Exception as e:
        import traceback
        if current_app.config.get("ENV") == "production":
            return jsonify({"ok": False, "error": "internal_error"}), 500
        return jsonify({"ok": False, "error": str(e), "trace": traceback.format_exc()}), 500

# --- ENDPOINTS INSCRIPCIONES ---
@secretaria_bp.route('/turnos/<int:turno_id>/alumnos', methods=['GET'])
def alumnos_en_turno(turno_id: int):
    try:
        rows = turno_repo.alumnos_inscritos(turno_id)
        return jsonify([
            {"alumno_id": r[0], "nombre": r[1], "email": r[2], "inscripcion_id": r[3]} for r in rows
        ])
    except Exception as e:
        import traceback
        if current_app.config.get("ENV") == "production":
            return jsonify({"ok": False, "error": "internal_error"}), 500
        return jsonify({"ok": False, "error": str(e), "trace": traceback.format_exc()}), 500

@secretaria_bp.route('/inscripciones/<int:inscripcion_id>/baja', methods=['POST'])
def baja_inscripcion(inscripcion_id: int):
    try:
        from models import Inscripcion, db
        ins = Inscripcion.query.filter_by(id=inscripcion_id).first()
        if not ins:
            return jsonify({"error": "Inscripción no encontrada"}), 404
        if ins.fecha_fin is not None:
            return jsonify({"error": "Inscripción ya estaba dada de baja"}), 409
        ok = turno_repo.baja_inscripcion(inscripcion_id)
        if not ok:
            # Si el repo falla, pero ya comprobamos arriba, es error interno
            return jsonify({"error": "Error al dar de baja la inscripción"}), 500
        return jsonify({"message": "Inscripción dada de baja"})
    except Exception as e:
        import traceback
        if current_app.config.get("ENV") == "production":
            return jsonify({"ok": False, "error": "internal_error"}), 500
        return jsonify({"ok": False, "error": str(e), "trace": traceback.format_exc()}), 500


# --- NUEVOS ENDPOINTS: ALUMNOS ---

@secretaria_bp.route('/alumnos', methods=['GET'])
def listar_alumnos():
    try:
        from models import Alumno
        # Obtener parámetros de paginación
        try:
            page = int(request.args.get('page', 0))
            size = int(request.args.get('size', 50))
            if page < 0: page = 0
            if size <= 0: size = 50
        except Exception:
            page = 0
            size = 50

        # Consulta paginada
        total = Alumno.query.count()
        alumnos = Alumno.query.order_by(Alumno.id).offset(page * size).limit(size).all()
        alumnos_list = [
            {
                "id": a.id,
                "nombre": a.nombre,
                "email": a.email,
            } for a in alumnos
        ]
        result = {
            "list": alumnos_list,
            "total": total,
            "page": page,
            "size": size,
            "hasMore": (page + 1) * size < total
        }
        return jsonify(result)
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
