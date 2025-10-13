from flask import Blueprint, jsonify, request, g
from webargs import fields
from src.shared.pagination import clamp_pagination, DEFAULT_SIZE, MAX_PAGE_SIZE, DEFAULT_PAGE
from src.shared.docs.openapi_args import openapi_query_args
from src.shared.middleware.auth import require_auth
from src.usuarios.infrastructure.models import Usuario
from src.shared.application.permissions import can_query_users, can_create_user, can_modify_user, can_delete_user
from src.shared.database import db
from src.shared.docs.operation_id import operation_id

usuarios_bp = Blueprint('usuarios', __name__)
usuarios_list_query_args = {
    'academia_id': fields.Int(required=False, allow_none=True),
    'rol': fields.Str(required=False, allow_none=True),
    'nombre': fields.Str(required=False, allow_none=True),
    'id': fields.Int(required=False, allow_none=True),
    'page': fields.Int(required=False, allow_none=True),
    'size': fields.Int(required=False, allow_none=True),
}


@usuarios_bp.route('/', methods=['GET'])
@require_auth  # Middleware para validar el token y extraer el rol
@operation_id('usuarios.listar_usuarios')
@openapi_query_args(usuarios_list_query_args)
def listar_usuarios():
    """
    Endpoint para listar usuarios con filtros opcionales.
    - Si el rol es admin_academia o profesor_academia, se fuerza el filtro por academia_id.
    - Si el rol es admin_plataforma, se permite ver todos los usuarios o filtrar por academia opcionalmente.
    """
    # Usuario autenticado cargado por el middleware
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'ok': False, 'error': 'user_not_authenticated'}), 401

    # Recopilar parámetros tal como llegarían desde la petición
    params = {
        'academia_id': request.args.get('academia_id'),
        'rol': request.args.get('rol'),
        'nombre': request.args.get('nombre'),
        'id': request.args.get('id') or request.args.get('usuario_id'),
        'page': request.args.get('page'),
        'size': request.args.get('size'),
    }

    allowed, effective_filters, reason = can_query_users(user, params)
    if not allowed:
        return jsonify({'ok': False, 'error': 'forbidden', 'reason': reason}), 403

    # Construir la consulta base y aplicar filtros efectivos
    query = Usuario.query
    if 'academia_id' in effective_filters:
        query = query.filter(Usuario.academia_id == effective_filters['academia_id'])

    # Aplicar filtros opcionales aportados por el caller (si no contradicen effective_filters)
    if params.get('id'):
        try:
            uid = int(params.get('id'))
            query = query.filter(Usuario.id == uid)
        except ValueError:
            return jsonify({'ok': False, 'error': 'invalid_id'}), 400

    if params.get('nombre'):
        query = query.filter(Usuario.nombre.ilike(f"%{params.get('nombre')}%"))

    if params.get('rol'):
        query = query.join(Usuario.rol).filter(Usuario.rol.has(nombre=params.get('rol')))

    # Pagination: parse page/size, apply offset/limit
    # Parse page/size and clamp to configured maxima/defaults. We prefer to be
    # tolerant and clamp rather than rejecting requests with large sizes.
    try:
        parsed_page = int(params.get('page')) if params.get('page') is not None else None
    except Exception:
        parsed_page = None
    try:
        parsed_size = int(params.get('size')) if params.get('size') is not None else None
    except Exception:
        parsed_size = None

    page, size = clamp_pagination(parsed_page, parsed_size)
    offset = (page - 1) * size
    usuarios = query.offset(offset).limit(size).all()

    def serialize(u: Usuario):
        return {
            'id': u.id,
            'nombre': u.nombre,
            'email': u.email,
            'rol': u.rol.nombre if getattr(u, 'rol', None) else None,
            'academia_id': u.academia_id,
            'estado': u.estado,
            'fecha_alta': u.fecha_alta.isoformat() if getattr(u, 'fecha_alta', None) else None,
        }

    return jsonify([serialize(u) for u in usuarios])


@usuarios_bp.route('/', methods=['POST'])
@require_auth
@operation_id('usuarios.crear_usuario')
def crear_usuario():
    user = getattr(g, 'current_user', None)
    data = request.get_json() or {}
    allowed, effective, reason = can_create_user(user, data)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403

    # Minimal creation logic: expect nombre, email, password, rol_id
    nombre = effective.get('nombre')
    email = effective.get('email')
    password = effective.get('password')
    rol_id = effective.get('rol_id')
    academia_id = effective.get('academia_id')

    if not nombre or not email or not password or not rol_id:
        return jsonify({"ok": False, "error": "missing_fields"}), 400

    # Check email uniqueness
    if Usuario.query.filter_by(email=email).first():
        return jsonify({"ok": False, "error": "conflict", "message": "email_exists"}), 409

    try:
        u = Usuario(nombre=nombre, email=email, password=password, rol_id=int(rol_id), academia_id=academia_id)
        db.session.add(u)
        db.session.commit()
        return jsonify({"ok": True, "result": {"id": u.id, "email": u.email}}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500

@usuarios_bp.route('/<int:usuario_id>', methods=['GET'])
@operation_id('usuarios.obtener_usuario')
def obtener_usuario(usuario_id):
    return jsonify({"message": f"Detalles del usuario {usuario_id}"})
@usuarios_bp.route('/<int:usuario_id>', methods=['PUT', 'PATCH'])
@require_auth
@operation_id({'put': 'usuarios.actualizar_usuario_put', 'patch': 'usuarios.actualizar_usuario_patch'})
def actualizar_usuario(usuario_id):
    user = getattr(g, 'current_user', None)
    target = db.session.get(Usuario, usuario_id)
    if not target:
        return jsonify({"ok": False, "error": "not_found"}), 404

    payload = request.get_json() or {}
    allowed, sanitized, reason = can_modify_user(user, target, payload)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403

    # Apply sanitized fields
    try:
        for k, v in sanitized.items():
            setattr(target, k, v)
        db.session.add(target)
        db.session.commit()
        return jsonify({"ok": True, "result": {"id": target.id}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500

@usuarios_bp.route('/<int:usuario_id>', methods=['DELETE'])
@require_auth
@operation_id('usuarios.eliminar_usuario')
def eliminar_usuario(usuario_id):
    user = getattr(g, 'current_user', None)
    target = db.session.get(Usuario, usuario_id)
    if not target:
        return jsonify({"ok": False, "error": "not_found"}), 404

    allowed, reason = can_delete_user(user, target)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403

    # Soft-delete: set fecha_baja and estado='Baja'
    try:
        from datetime import datetime, timezone
        target.fecha_baja = datetime.now(timezone.utc)
        target.estado = 'Baja'
        db.session.add(target)
        db.session.commit()
        return jsonify({"ok": True, "result": {"id": target.id}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500

@usuarios_bp.route('/<int:usuario_id>/credentials', methods=['PUT'])
@operation_id('usuarios.actualizar_credenciales')
def actualizar_credenciales(usuario_id):
    data = request.get_json()
    return jsonify({"message": f"Credenciales del usuario {usuario_id} actualizadas", "data": data})

@usuarios_bp.route('/<int:usuario_id>/role', methods=['PUT'])
@operation_id('usuarios.actualizar_rol')
def actualizar_rol(usuario_id):
    data = request.get_json()
    return jsonify({"message": f"Rol del usuario {usuario_id} actualizado", "data": data})

@usuarios_bp.route('/<int:usuario_id>/status', methods=['PUT'])
@operation_id('usuarios.actualizar_estado')
def actualizar_estado(usuario_id):
    data = request.get_json()
    return jsonify({"message": f"Estado del usuario {usuario_id} actualizado", "data": data})

@usuarios_bp.route('/recover', methods=['GET'])
@operation_id('usuarios.recuperar_credenciales')
def recuperar_credenciales():
    email = request.args.get('email')
    return jsonify({"message": f"Instrucciones enviadas al correo {email}"})


# Endpoint para obtener los datos del usuario autenticado
@usuarios_bp.route('/me', methods=['GET'])
@require_auth
@operation_id('usuarios.obtener_mi_perfil')
def obtener_mi_perfil():
    print("[DEBUG] Controlador obtener_mi_perfil alcanzado", flush=True)
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