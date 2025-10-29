"""Rutas para gestión de roles de usuario."""
from flask import Blueprint, jsonify, g
from webargs import fields
from src.shared.docs.openapi_args import openapi_query_args
from src.shared.middleware.auth import require_auth
from src.usuarios.infrastructure.models import Rol
from src.shared.application.permissions import can_query_roles
from src.shared.database import db
from src.shared.docs.operation_id import operation_id
from src.schemas.usuario import RolSchema
import logging

logger = logging.getLogger(__name__)

roles_bp = Blueprint('roles', __name__)

# Query args para listar roles
roles_list_query_args = {
    'nombre': fields.Str(required=False, allow_none=True, metadata={
        'description': 'Filtro exacto por nombre del rol (ej: "Admin_plataforma")'
    }),
    'nombre_contains': fields.Str(required=False, allow_none=True, metadata={
        'description': 'Filtro por nombre que contenga el texto (case-insensitive)'
    }),
    'id': fields.Int(required=False, allow_none=True, metadata={
        'description': 'Filtro por ID específico de rol'
    }),
}


@roles_bp.route('/', methods=['GET'])
@require_auth
@operation_id('roles.listar_roles')
@openapi_query_args(roles_list_query_args)
def listar_roles():
    """
    Endpoint para listar roles disponibles en el sistema.
    
    Retorna todos los roles o filtra por nombre/id.
    Todos los usuarios autenticados pueden consultar roles.
    
    Returns:
        JSON con lista de roles: [{"id": 7, "nombre": "Admin_plataforma"}, ...]
    """
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'ok': False, 'error': 'user_not_authenticated'}), 401

    # Obtener parámetros de filtro
    from flask import request
    nombre = request.args.get('nombre')
    nombre_contains = request.args.get('nombre_contains')
    rol_id = request.args.get('id')

    # Construir filtros
    params = {}
    if nombre:
        params['nombre'] = nombre
    if nombre_contains:
        params['nombre_contains'] = nombre_contains
    if rol_id:
        params['id'] = rol_id

    # Verificar permisos
    allowed, enforced_filters, reason = can_query_roles(user, params)
    if not allowed:
        return jsonify({'ok': False, 'error': 'forbidden', 'reason': reason or 'insufficient_permissions'}), 403

    # Aplicar filtros forzados (si los hay)
    params.update(enforced_filters)

    # Query base
    query = db.session.query(Rol)

    # Aplicar filtros
    if params.get('id'):
        query = query.filter(Rol.id == params['id'])
    
    if params.get('nombre'):
        query = query.filter(Rol.nombre == params['nombre'])
    
    if params.get('nombre_contains'):
        query = query.filter(Rol.nombre.ilike(f"%{params['nombre_contains']}%"))

    # Ordenar por id (los IDs suelen reflejar jerarquía)
    query = query.order_by(Rol.id)

    # Ejecutar query
    try:
        roles = query.all()
    except Exception as e:
        logger.error(f"Error querying roles: {e}")
        return jsonify({'ok': False, 'error': 'database_error'}), 500

    # Serializar
    schema = RolSchema(many=True)
    roles_data = schema.dump(roles)

    logger.info(f"User {user.id} (rol={user.rol.nombre if user.rol else 'unknown'}) listed {len(roles_data)} roles")

    return jsonify({
        'ok': True,
        'data': roles_data,
        'count': len(roles_data)
    }), 200
