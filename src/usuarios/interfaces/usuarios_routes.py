from flask import Blueprint, jsonify, request

usuarios_bp = Blueprint('usuarios', __name__)

@usuarios_bp.route('/usuarios', methods=['GET'])
def listar_usuarios():
    return jsonify({"message": "Lista de usuarios"})

@usuarios_bp.route('/usuarios', methods=['POST'])
def crear_usuario():
    data = request.get_json()
    return jsonify({"message": "Usuario creado", "data": data})

@usuarios_bp.route('/usuarios/<int:usuario_id>', methods=['GET'])
def obtener_usuario(usuario_id):
    return jsonify({"message": f"Detalles del usuario {usuario_id}"})
@usuarios_bp.route('/usuarios/<int:usuario_id>', methods=['PUT'])
def actualizar_usuario(usuario_id):
    data = request.get_json()
    return jsonify({"message": f"Usuario {usuario_id} actualizado", "data": data})

@usuarios_bp.route('/usuarios/<int:usuario_id>', methods=['DELETE'])
def eliminar_usuario(usuario_id):
    return jsonify({"message": f"Usuario {usuario_id} eliminado"})

@usuarios_bp.route('/usuarios/<int:usuario_id>/credentials', methods=['PUT'])
def actualizar_credenciales(usuario_id):
    data = request.get_json()
    return jsonify({"message": f"Credenciales del usuario {usuario_id} actualizadas", "data": data})

@usuarios_bp.route('/usuarios/<int:usuario_id>/role', methods=['PUT'])
def actualizar_rol(usuario_id):
    data = request.get_json()
    return jsonify({"message": f"Rol del usuario {usuario_id} actualizado", "data": data})

@usuarios_bp.route('/usuarios/<int:usuario_id>/status', methods=['PUT'])
def actualizar_estado(usuario_id):
    data = request.get_json()
    return jsonify({"message": f"Estado del usuario {usuario_id} actualizado", "data": data})

@usuarios_bp.route('/usuarios/recover', methods=['GET'])
def recuperar_credenciales():
    email = request.args.get('email')
    return jsonify({"message": f"Instrucciones enviadas al correo {email}"})