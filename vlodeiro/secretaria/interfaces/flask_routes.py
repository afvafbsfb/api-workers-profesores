
# vlodeiro/secretaria/interfaces/flask_routes.py

from flask import Blueprint, request, jsonify
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

@secretaria_bp.route('/inscribir', methods=['POST'])
def inscribir():
    data = request.get_json()
    alumno_id = data.get('alumno_id')
    clase_id = data.get('clase_id')

    if not alumno_id or not clase_id:
        return jsonify({'error': 'Faltan datos de alumno o clase'}), 400

    if inscribir_alumno_use_case.execute(alumno_id, clase_id):
        return jsonify({'message': 'Alumno inscrito correctamente'}), 200
    else:
        return jsonify({'error': 'No se pudo inscribir al alumno'}), 400

@secretaria_bp.route('/registrar_pago', methods=['POST'])
def registrar_pago():
    data = request.get_json()
    alumno_id = data.get('alumno_id')
    monto = data.get('monto')
    concepto = data.get('concepto')

    if not alumno_id or not monto or not concepto:
        return jsonify({'error': 'Faltan datos del pago'}), 400

    pago = registrar_pago_use_case.execute(alumno_id, monto, concepto)
    return jsonify({'message': 'Pago registrado correctamente', 'pago_id': pago.id}), 200
