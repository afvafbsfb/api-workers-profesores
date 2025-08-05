

# vlodeiro/secretaria/interfaces/flask_routes.py

from flask import Blueprint, request, jsonify, current_app
from marshmallow import Schema, fields, ValidationError
from vlodeiro.secretaria.application.inscribir_alumno import InscribirAlumno
from vlodeiro.secretaria.application.registrar_pago import RegistrarPago
from vlodeiro.secretaria.infrastructure.repositorio_mysql import AlumnoMySQLRepository, ClaseMySQLRepository, PagoMySQLRepository

secretaria_bp = Blueprint('secretaria', __name__)

# Inicialización de repositorios y casos de uso
alumno_repo = AlumnoMySQLRepository()
clase_repo = ClaseMySQLRepository()
pago_repo = PagoMySQLRepository()

inscribir_alumno_use_case = InscribirAlumno(alumno_repo, clase_repo)
registrar_pago_use_case = RegistrarPago(pago_repo)

# Esquema para inscribir
class InscribirSchema(Schema):
    alumno_id = fields.Int(required=True)
    clase_id = fields.Int(required=True)

# Esquema para registrar pago
class RegistrarPagoSchema(Schema):
    alumno_id = fields.Int(required=True)
    monto = fields.Float(required=True)
    concepto = fields.Str(required=True)

@secretaria_bp.route('/inscribir', methods=['POST'])
def inscribir():
    data = request.get_json()
    try:
        validated = InscribirSchema().load(data)
    except ValidationError as ve:
        return jsonify({'error': 'Datos inválidos', 'detalles': ve.messages}), 400
    alumno_id = validated['alumno_id']
    clase_id = validated['clase_id']
    if inscribir_alumno_use_case.execute(alumno_id, clase_id):
        return jsonify({'message': 'Alumno inscrito correctamente'}), 200
    else:
        return jsonify({'error': 'No se pudo inscribir al alumno'}), 400

@secretaria_bp.route('/registrar_pago', methods=['POST'])
def registrar_pago():
    data = request.get_json()
    try:
        validated = RegistrarPagoSchema().load(data)
    except ValidationError as ve:
        return jsonify({'error': 'Datos inválidos', 'detalles': ve.messages}), 400
    alumno_id = validated['alumno_id']
    monto = validated['monto']
    concepto = validated['concepto']
    pago = registrar_pago_use_case.execute(alumno_id, monto, concepto)
    return jsonify({'message': 'Pago registrado correctamente', 'pago_id': pago.id}), 200

# --- NUEVO ENDPOINT /turnos EN BLUEPRINT ---
from vlodeiro.secretaria.infrastructure.repositorio_mysql import ClaseMySQLRepository
@secretaria_bp.route('/turnos', methods=['GET'])
def listar_turnos():
    try:
        repo = ClaseMySQLRepository()
        turnos = repo.listar_turnos()
        print("Turnos encontrados:", turnos)
        return jsonify([
            {
                "id": getattr(t, "id", None),
                "dia": getattr(t, "dia_semana", None),
                "hora": getattr(t, "hora", None) and t.hora.strftime('%H:%M'),
                "tipo": getattr(t, "tipo_alumno", None),
                "duracion": getattr(t, "duracion", None),
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
