# API para Empresa
from flask import Blueprint, request, jsonify
from vlodeiro.empresa.infrastructure.empresa_repository import EmpresaRepository
from vlodeiro.empresa.application.crear_empresa import CrearEmpresa

empresa_bp = Blueprint('empresa', __name__)
empresa_repo = EmpresaRepository()
crear_empresa_uc = CrearEmpresa(empresa_repo)

@empresa_bp.route('/empresa', methods=['POST'])
def crear_empresa():
    data = request.get_json() or {}
    nombre = data.get('nombre')
    descripcion = data.get('descripcion')
    usuarios = data.get('usuarios')
    config = data.get('config')
    if not nombre:
        return jsonify({'error': 'El nombre es obligatorio'}), 400
    empresa = crear_empresa_uc.execute(nombre, descripcion, usuarios, config)
    return jsonify({'id': empresa.id, 'nombre': empresa.nombre, 'descripcion': empresa.descripcion}), 201

@empresa_bp.route('/empresa/<empresa_id>', methods=['GET'])
def obtener_empresa(empresa_id):
    empresa = empresa_repo.get_by_id(empresa_id)
    if not empresa:
        return jsonify({'error': 'Empresa no encontrada'}), 404
    return jsonify({'id': empresa.id, 'nombre': empresa.nombre, 'descripcion': empresa.descripcion})

@empresa_bp.route('/empresa', methods=['GET'])
def listar_empresas():
    empresas = empresa_repo.list_all()
    return jsonify([
        {'id': e.id, 'nombre': e.nombre, 'descripcion': e.descripcion}
        for e in empresas
    ])
