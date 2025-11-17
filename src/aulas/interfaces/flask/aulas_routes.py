"""Rutas para gestión de Aulas."""
from flask import Blueprint, request, jsonify, g
from webargs import fields
from webargs.flaskparser import use_args
from datetime import datetime, timezone

from src.shared.pagination import clamp_pagination, DEFAULT_SIZE, MAX_PAGE_SIZE, DEFAULT_PAGE
from src.shared.docs.openapi_args import openapi_query_args
from src.shared.middleware.auth import require_auth
from src.shared.docs.operation_id import operation_id
from src.shared.application.permissions import (
    can_query_aulas,
    can_create_aula,
    can_view_aula,
    can_modify_aula,
    can_delete_aula
)
from src.academias.infrastructure.models import Aula, Academia
from src.schemas.aula import AulaSchema, AulaCreateSchema, AulaUpdateSchema
from src.shared.database import db
from config import Config

aulas_bp = Blueprint('aulas', __name__)

# Schemas para serialización
aula_schema = AulaSchema()
aulas_schema = AulaSchema(many=True)
aula_create_schema = AulaCreateSchema()
aula_update_schema = AulaUpdateSchema()


# Query args para listar aulas
aulas_list_query_args = {
    'academia_id': fields.Int(required=False, allow_none=True),
    'nombre': fields.Str(required=False, allow_none=True),
    'nombre_contains': fields.Str(required=False, allow_none=True),
    'capacidad_min': fields.Int(required=False, allow_none=True),
    'capacidad_max': fields.Int(required=False, allow_none=True),
    'order_by': fields.Str(required=False, allow_none=True),
    'order_direction': fields.Str(required=False, allow_none=True),
    'page': fields.Int(required=False, load_default=DEFAULT_PAGE),
    'size': fields.Int(required=False, load_default=DEFAULT_SIZE),
    'expand': fields.Str(required=False, allow_none=True, metadata={
        'description': 'Expandir relaciones. Valores: "academia" (añade objeto con id y nombre de la academia)'
    }),
}


@aulas_bp.route('/', methods=['GET'])
@require_auth
@use_args(aulas_list_query_args, location='query')
@openapi_query_args(aulas_list_query_args)
@operation_id('aulas.listar_aulas')
def listar_aulas(args):
    """Listar aulas con filtros y paginación.
    
    Filtros disponibles:
    - academia_id: ID de la academia
    - nombre: nombre exacto del aula
    - nombre_contains: búsqueda parcial por nombre
    - capacidad_min, capacidad_max: rango de capacidad
    - order_by: campo para ordenar (id, academia_id, nombre, capacidad_maxima)
    - order_direction: asc o desc
    - expand: expandir relaciones (valores: "academia")
    """
    user = getattr(g, 'current_user', None)
    
    # Parsear parámetro expand
    expand_param = args.get('expand', '') or ''
    expand = [e.strip() for e in expand_param.split(',') if e.strip()]
    
    # Verificar permisos
    params = {'academia_id': args.get('academia_id')}
    allowed, effective_filters, reason = can_query_aulas(user, params)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Construir query
    query = Aula.query
    
    # Aplicar filtro de academia_id (forzado por permisos o proporcionado)
    if 'academia_id' in effective_filters:
        query = query.filter(Aula.academia_id == effective_filters['academia_id'])
    
    # Filtros adicionales
    nombre_exact = args.get('nombre')
    nombre_contains = args.get('nombre_contains')
    
    if nombre_exact:
        query = query.filter(Aula.nombre == nombre_exact)
    elif nombre_contains:
        try:
            query = query.filter(Aula.nombre.ilike(f"%{nombre_contains}%"))
        except Exception:
            query = query.filter(Aula.nombre.like(f"%{nombre_contains}%"))
    
    if args.get('capacidad_min') is not None:
        query = query.filter(Aula.capacidad_maxima >= args.get('capacidad_min'))
    
    if args.get('capacidad_max') is not None:
        query = query.filter(Aula.capacidad_maxima <= args.get('capacidad_max'))
    
    # Ordenación
    order_by = args.get('order_by', 'id')
    order_direction = args.get('order_direction', 'asc').lower()
    
    # Validar campo de ordenación
    valid_order_fields = ['id', 'academia_id', 'nombre', 'capacidad_maxima']
    if order_by not in valid_order_fields:
        order_by = 'id'
    
    if order_direction not in ['asc', 'desc']:
        order_direction = 'asc'
    
    # Aplicar ordenación
    order_column = getattr(Aula, order_by)
    if order_direction == 'desc':
        query = query.order_by(order_column.desc())
    else:
        query = query.order_by(order_column.asc())
    
    # Paginación
    page, size = clamp_pagination(args.get('page'), args.get('size'))
    offset = (max(page, 1) - 1) * max(size, 1)
    
    aulas = query.offset(offset).limit(size).all()
    
    # Serializar aulas
    result = []
    for aula in aulas:
        item = aula_schema.dump(aula)
        
        # Expandir academia si se solicita
        if 'academia' in expand:
            if aula.academia_id:
                academia = db.session.get(Academia, aula.academia_id)
                if academia:
                    item['academia'] = {
                        'id': academia.id,
                        'nombre': academia.nombre
                    }
                else:
                    item['academia'] = None
            else:
                item['academia'] = None
        
        result.append(item)
    
    return jsonify({"ok": True, "result": result}), 200


@aulas_bp.route('/', methods=['POST'])
@require_auth
@operation_id('aulas.crear_aula')
def crear_aula():
    """Crear una nueva aula.
    
    Body JSON:
    - academia_id: ID de la academia (obligatorio para admin_plataforma, opcional para admin_academia)
    - nombre: Nombre del aula (obligatorio)
    - capacidad_maxima: Capacidad máxima (obligatorio, > 0)
    """
    user = getattr(g, 'current_user', None)
    
    # Parsear y validar payload
    data = request.get_json() or {}
    errors = aula_create_schema.validate(data)
    if errors:
        return jsonify({"ok": False, "error": "validation_error", "details": errors}), 400
    
    # Verificar permisos y obtener payload efectivo
    allowed, effective_payload, reason = can_create_aula(user, data)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Validar que la academia existe y está activa
    academia_id = effective_payload.get('academia_id')
    academia = db.session.get(Academia, academia_id)
    if not academia:
        return jsonify({"ok": False, "error": "not_found", "message": "academia_not_found"}), 404
    if academia.fecha_baja is not None:
        return jsonify({"ok": False, "error": "invalid_state", "message": "academia_inactive"}), 400
    
    # Crear aula
    try:
        aula = Aula(
            academia_id=effective_payload['academia_id'],
            nombre=effective_payload['nombre'].strip(),
            capacidad_maxima=effective_payload['capacidad_maxima']
        )
        db.session.add(aula)
        db.session.commit()
        
        result = aula_schema.dump(aula)
        return jsonify({"ok": True, "result": result}), 201
    except Exception as e:
        db.session.rollback()
        if Config.DEBUG:
            print(f"[ERROR] crear_aula: {e}")
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500


@aulas_bp.route('/<int:aula_id>', methods=['GET'])
@require_auth
@operation_id('aulas.obtener_aula')
def obtener_aula(aula_id):
    """Obtener un aula por ID."""
    user = getattr(g, 'current_user', None)
    
    aula = db.session.get(Aula, aula_id)
    if not aula:
        return jsonify({"ok": False, "error": "not_found"}), 404
    
    # Verificar permisos
    allowed, _, reason = can_view_aula(user, aula)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    result = aula_schema.dump(aula)
    return jsonify({"ok": True, "result": result}), 200


@aulas_bp.route('/<int:aula_id>', methods=['PUT', 'PATCH'])
@require_auth
@operation_id({'put': 'aulas.actualizar_aula_put', 'patch': 'aulas.actualizar_aula_patch'})
def actualizar_aula(aula_id):
    """Actualizar un aula.
    
    Body JSON (campos opcionales):
    - nombre: Nuevo nombre
    - capacidad_maxima: Nueva capacidad máxima (> 0)
    """
    user = getattr(g, 'current_user', None)
    
    aula = db.session.get(Aula, aula_id)
    if not aula:
        return jsonify({"ok": False, "error": "not_found"}), 404
    
    # Parsear y validar payload
    data = request.get_json() or {}
    errors = aula_update_schema.validate(data)
    if errors:
        return jsonify({"ok": False, "error": "validation_error", "details": errors}), 400
    
    # Verificar permisos y obtener campos permitidos
    allowed, sanitized_payload, reason = can_modify_aula(user, aula, data)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Actualizar campos permitidos
    try:
        if 'nombre' in sanitized_payload:
            aula.nombre = sanitized_payload['nombre'].strip()
        if 'capacidad_maxima' in sanitized_payload:
            aula.capacidad_maxima = sanitized_payload['capacidad_maxima']
        
        db.session.add(aula)
        db.session.commit()
        
        result = aula_schema.dump(aula)
        return jsonify({"ok": True, "result": result}), 200
    except Exception as e:
        db.session.rollback()
        if Config.DEBUG:
            print(f"[ERROR] actualizar_aula: {e}")
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500


@aulas_bp.route('/<int:aula_id>', methods=['DELETE'])
@require_auth
@operation_id('aulas.eliminar_aula')
def eliminar_aula(aula_id):
    """Eliminar (soft-delete) un aula.
    
    Nota: Las aulas no tienen campo fecha_baja en el modelo actual.
    Se implementará como eliminación física solo si no tiene horarios asociados.
    """
    user = getattr(g, 'current_user', None)
    
    aula = db.session.get(Aula, aula_id)
    if not aula:
        return jsonify({"ok": False, "error": "not_found"}), 404
    
    # Verificar permisos
    allowed, reason = can_delete_aula(user, aula)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Validar que no hay horarios asociados
    from src.academias.infrastructure.models import HorarioCurso
    horarios = HorarioCurso.query.filter(HorarioCurso.aula_id == aula_id).count()
    
    if horarios > 0:
        return jsonify({
            "ok": False,
            "error": "has_dependents",
            "message": "No se puede eliminar el aula porque tiene horarios asociados",
            "details": {"horarios": horarios}
        }), 409
    
    # Eliminar físicamente (las aulas no tienen fecha_baja en el modelo)
    try:
        db.session.delete(aula)
        db.session.commit()
        
        return jsonify({"ok": True, "result": {"id": aula_id, "deleted": True}}), 200
    except Exception as e:
        db.session.rollback()
        if Config.DEBUG:
            print(f"[ERROR] eliminar_aula: {e}")
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500
