from flask import Blueprint, jsonify, request, g
from src.shared.middleware.auth import require_auth
from src.usuarios.infrastructure.models import Usuario

usuarios_bp = Blueprint('usuarios', __name__)

@usuarios_bp.route('/', methods=['GET'])
@require_auth  # Middleware para validar el token y extraer el rol
def listar_usuarios():
    """
    Endpoint para listar usuarios con filtros opcionales.
    - Si el rol es admin_academia o profesor_academia, se fuerza el filtro por academia_id.
    - Si el rol es admin_plataforma, se permite ver todos los usuarios o filtrar por academia opcionalmente.
    """
    user = get_current_user()  # Extraer usuario desde el token
    rol = user['rol']
    academia_id = request.args.get('academia_id')
    nombre = request.args.get('nombre')
    rol_filtro = request.args.get('rol')

    # Construir la consulta
    query = Usuario.query

    if rol in ['admin_academia', 'profesor_academia']:
        # Forzar filtro por academia
        query = query.filter(Usuario.academia_id == user['academia_id'])
    elif rol == 'admin_plataforma':
        # Permitir ver todos o filtrar por academia opcionalmente
        if academia_id:
            query = query.filter(Usuario.academia_id == academia_id)
    else:
        # Rol no autorizado
        return jsonify({'error': 'No autorizado'}), 403

    # Aplicar filtros opcionales
    if nombre:
        query = query.filter(Usuario.nombre.ilike(f"%{nombre}%"))
    if rol_filtro:
        query = query.filter(Usuario.rol == rol_filtro)

    usuarios = query.all()
    return jsonify([usuario.to_dict() for usuario in usuarios])

@usuarios_bp.route('/', methods=['POST'])
def crear_usuario():
    data = request.get_json()
    return jsonify({"message": "Usuario creado", "data": data})

@usuarios_bp.route('/<int:usuario_id>', methods=['GET'])
def obtener_usuario(usuario_id):
    return jsonify({"message": f"Detalles del usuario {usuario_id}"})
@usuarios_bp.route('/<int:usuario_id>', methods=['PUT'])
def actualizar_usuario(usuario_id):
    data = request.get_json()
    return jsonify({"message": f"Usuario {usuario_id} actualizado", "data": data})

@usuarios_bp.route('/<int:usuario_id>', methods=['DELETE'])
def eliminar_usuario(usuario_id):
    return jsonify({"message": f"Usuario {usuario_id} eliminado"})

@usuarios_bp.route('/<int:usuario_id>/credentials', methods=['PUT'])
def actualizar_credenciales(usuario_id):
    data = request.get_json()
    return jsonify({"message": f"Credenciales del usuario {usuario_id} actualizadas", "data": data})

@usuarios_bp.route('/<int:usuario_id>/role', methods=['PUT'])
def actualizar_rol(usuario_id):
    data = request.get_json()
    return jsonify({"message": f"Rol del usuario {usuario_id} actualizado", "data": data})

@usuarios_bp.route('/<int:usuario_id>/status', methods=['PUT'])
def actualizar_estado(usuario_id):
    data = request.get_json()
    return jsonify({"message": f"Estado del usuario {usuario_id} actualizado", "data": data})

@usuarios_bp.route('/recover', methods=['GET'])
def recuperar_credenciales():
    email = request.args.get('email')
    return jsonify({"message": f"Instrucciones enviadas al correo {email}"})


# Endpoint para obtener los datos del usuario autenticado
@usuarios_bp.route('/me', methods=['GET'])
@require_auth
def obtener_mi_perfil():
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({"ok": False, "error": "user_not_authenticated"}), 401

    # Construir la respuesta con los campos útiles para la capa de presentación
    perfil = {
        "id": user.id,
        "nombre": user.nombre,
        "email": user.email,
        "rol": user.rol.nombre if getattr(user, 'rol', None) else None,
        "academia_id": user.academia_id,
        "estado": user.estado,
        "fecha_alta": user.fecha_alta.isoformat() if getattr(user, 'fecha_alta', None) else None,
    }

    return jsonify(perfil)