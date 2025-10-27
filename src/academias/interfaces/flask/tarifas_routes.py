"""Rutas para gestión de Tarifas."""
from flask import Blueprint, request, jsonify, g
from webargs import fields
from webargs.flaskparser import use_args
from datetime import datetime, timezone
from sqlalchemy import or_, and_

from src.shared.pagination import clamp_pagination, DEFAULT_SIZE, MAX_PAGE_SIZE, DEFAULT_PAGE
from src.shared.docs.openapi_args import openapi_query_args
from src.shared.middleware.auth import require_auth
from src.shared.docs.operation_id import operation_id
from src.shared.application.permissions import (
    can_query_tarifas,
    can_create_tarifa,
    can_view_tarifa,
    can_modify_tarifa,
    can_delete_tarifa
)
from src.academias.infrastructure.models import Tarifa, Academia, Curso
from src.schemas.tarifa import TarifaSchema, TarifaCreateSchema, TarifaUpdateSchema
from src.shared.database import db
from config import Config

tarifas_bp = Blueprint('tarifas', __name__)

# Schemas para serialización
tarifa_schema = TarifaSchema()
tarifas_schema = TarifaSchema(many=True)
tarifa_create_schema = TarifaCreateSchema()
tarifa_update_schema = TarifaUpdateSchema()


# Query args para listar tarifas
tarifas_list_query_args = {
    'academia_id': fields.Int(required=False, allow_none=True),
    'precio_base_min': fields.Float(required=False, allow_none=True),
    'precio_base_max': fields.Float(required=False, allow_none=True),
    'fecha_alta_desde': fields.Date(required=False, allow_none=True),
    'fecha_alta_hasta': fields.Date(required=False, allow_none=True),
    'fecha_baja_null': fields.Bool(required=False, allow_none=True),
    'order_by': fields.Str(required=False, allow_none=True),
    'order_direction': fields.Str(required=False, allow_none=True),
    'page': fields.Int(required=False, load_default=DEFAULT_PAGE),
    'size': fields.Int(required=False, load_default=DEFAULT_SIZE),
    'expand': fields.Str(required=False, allow_none=True, metadata={
        'description': 'Expandir relaciones. Valores: "academia" (añade objeto con id y nombre de la academia)'
    }),
}


@tarifas_bp.route('/', methods=['GET'])
@require_auth
@use_args(tarifas_list_query_args, location='query')
@openapi_query_args(tarifas_list_query_args)
@operation_id('tarifas.listar_tarifas')
def listar_tarifas(args):
    """Listar tarifas con filtros y paginación.
    
    Filtros disponibles:
    - academia_id: ID de la academia
    - precio_base_min, precio_base_max: rango de precio
    - fecha_alta_desde, fecha_alta_hasta: rango de fecha de alta
    - fecha_baja_null: true (activas) o false (dadas de baja)
    - order_by: campo para ordenar (id, academia_id, descripcion, precio_base, fecha_alta, fecha_baja, fecha_ultima_modificacion)
    - order_direction: asc o desc
    - expand: expandir relaciones (valores: "academia")
    """
    user = getattr(g, 'current_user', None)
    
    # Parsear parámetro expand
    expand_param = args.get('expand', '') or ''
    expand = [e.strip() for e in expand_param.split(',') if e.strip()]
    
    # Verificar permisos
    params = {'academia_id': args.get('academia_id')}
    allowed, effective_filters, reason = can_query_tarifas(user, params)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Construir query
    query = Tarifa.query
    
    # Aplicar filtro de academia_id (forzado por permisos o proporcionado)
    if 'academia_id' in effective_filters:
        query = query.filter(Tarifa.academia_id == effective_filters['academia_id'])
    
    # Filtros adicionales
    if args.get('precio_base_min') is not None:
        query = query.filter(Tarifa.precio_base >= args.get('precio_base_min'))
    
    if args.get('precio_base_max') is not None:
        query = query.filter(Tarifa.precio_base <= args.get('precio_base_max'))
    
    if args.get('fecha_alta_desde'):
        query = query.filter(Tarifa.fecha_alta >= datetime.combine(args.get('fecha_alta_desde'), datetime.min.time()))
    
    if args.get('fecha_alta_hasta'):
        query = query.filter(Tarifa.fecha_alta <= datetime.combine(args.get('fecha_alta_hasta'), datetime.max.time()))
    
    if args.get('fecha_baja_null') is not None:
        if args.get('fecha_baja_null'):
            query = query.filter(Tarifa.fecha_baja.is_(None))
        else:
            query = query.filter(Tarifa.fecha_baja.isnot(None))
    
    # Ordenación
    order_by = args.get('order_by', 'id')
    order_direction = args.get('order_direction', 'asc').lower()
    
    # Validar campo de ordenación
    valid_order_fields = ['id', 'academia_id', 'descripcion', 'precio_base', 'fecha_alta', 'fecha_baja', 'fecha_ultima_modificacion']
    if order_by not in valid_order_fields:
        order_by = 'id'
    
    if order_direction not in ['asc', 'desc']:
        order_direction = 'asc'
    
    # Aplicar ordenación
    order_column = getattr(Tarifa, order_by)
    if order_direction == 'desc':
        query = query.order_by(order_column.desc())
    else:
        query = query.order_by(order_column.asc())
    
    # Paginación
    page, size = clamp_pagination(args.get('page'), args.get('size'))
    offset = (max(page, 1) - 1) * max(size, 1)
    
    tarifas = query.offset(offset).limit(size).all()
    
    # Serializar tarifas
    result = []
    for tarifa in tarifas:
        item = tarifa_schema.dump(tarifa)
        
        # Expandir academia si se solicita
        if 'academia' in expand:
            if tarifa.academia_id:
                academia = db.session.get(Academia, tarifa.academia_id)
                if academia:
                    item['academia'] = {
                        'id': academia.id,
                        'nombre': academia.nombre
                    }
                else:
                    # FK apunta a academia inexistente (caso edge)
                    item['academia'] = None
            else:
                # academia_id es NULL
                item['academia'] = None
        
        result.append(item)
    
    return jsonify({"ok": True, "result": result}), 200


@tarifas_bp.route('/', methods=['POST'])
@require_auth
@operation_id('tarifas.crear_tarifa')
def crear_tarifa():
    """Crear una nueva tarifa.
    
    Body JSON:
    - academia_id: ID de la academia (obligatorio para admin_plataforma, opcional para admin_academia)
    - descripcion: Descripción de la tarifa (obligatorio)
    - precio_base: Precio base (obligatorio, > 0)
    """
    user = getattr(g, 'current_user', None)
    
    # Parsear y validar payload
    data = request.get_json() or {}
    errors = tarifa_create_schema.validate(data)
    if errors:
        return jsonify({"ok": False, "error": "validation_error", "details": errors}), 400
    
    # Verificar permisos y obtener payload efectivo
    allowed, effective_payload, reason = can_create_tarifa(user, data)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Validar que la academia existe y está activa (solo para admin_plataforma)
    try:
        user_role = user.rol.nombre.strip().lower() if user and user.rol else None
    except Exception:
        user_role = None
    
    if user_role == 'admin_plataforma':
        academia_id = effective_payload.get('academia_id')
        academia = db.session.get(Academia, academia_id)
        if not academia:
            return jsonify({"ok": False, "error": "not_found", "message": "academia_not_found"}), 404
        if academia.fecha_baja is not None:
            return jsonify({"ok": False, "error": "invalid_state", "message": "academia_inactive"}), 400
    
    # Crear tarifa
    try:
        tarifa = Tarifa(
            academia_id=effective_payload['academia_id'],
            descripcion=effective_payload['descripcion'].strip(),
            precio_base=effective_payload['precio_base']
        )
        db.session.add(tarifa)
        db.session.commit()
        
        result = tarifa_schema.dump(tarifa)
        return jsonify({"ok": True, "result": result}), 201
    except Exception as e:
        db.session.rollback()
        if Config.DEBUG:
            print(f"[ERROR] crear_tarifa: {e}")
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500


@tarifas_bp.route('/<int:tarifa_id>', methods=['GET'])
@require_auth
@operation_id('tarifas.obtener_tarifa')
def obtener_tarifa(tarifa_id):
    """Obtener una tarifa por ID."""
    user = getattr(g, 'current_user', None)
    
    tarifa = db.session.get(Tarifa, tarifa_id)
    if not tarifa:
        return jsonify({"ok": False, "error": "not_found"}), 404
    
    # Verificar permisos
    allowed, _, reason = can_view_tarifa(user, tarifa)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    result = tarifa_schema.dump(tarifa)
    return jsonify({"ok": True, "result": result}), 200


@tarifas_bp.route('/<int:tarifa_id>', methods=['PUT', 'PATCH'])
@require_auth
@operation_id({'put': 'tarifas.actualizar_tarifa_put', 'patch': 'tarifas.actualizar_tarifa_patch'})
def actualizar_tarifa(tarifa_id):
    """Actualizar una tarifa.
    
    Body JSON (campos opcionales):
    - descripcion: Nueva descripción
    - precio_base: Nuevo precio base (> 0)
    """
    user = getattr(g, 'current_user', None)
    
    tarifa = db.session.get(Tarifa, tarifa_id)
    if not tarifa:
        return jsonify({"ok": False, "error": "not_found"}), 404
    
    # Parsear y validar payload
    data = request.get_json() or {}
    errors = tarifa_update_schema.validate(data)
    if errors:
        return jsonify({"ok": False, "error": "validation_error", "details": errors}), 400
    
    # Verificar permisos y obtener campos permitidos
    allowed, sanitized_payload, reason = can_modify_tarifa(user, tarifa, data)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Actualizar campos permitidos
    try:
        if 'descripcion' in sanitized_payload:
            tarifa.descripcion = sanitized_payload['descripcion'].strip()
        if 'precio_base' in sanitized_payload:
            tarifa.precio_base = sanitized_payload['precio_base']
        
        db.session.add(tarifa)
        db.session.commit()
        
        result = tarifa_schema.dump(tarifa)
        return jsonify({"ok": True, "result": result}), 200
    except Exception as e:
        db.session.rollback()
        if Config.DEBUG:
            print(f"[ERROR] actualizar_tarifa: {e}")
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500


@tarifas_bp.route('/<int:tarifa_id>', methods=['DELETE'])
@require_auth
@operation_id('tarifas.eliminar_tarifa')
def eliminar_tarifa(tarifa_id):
    """Eliminar (soft-delete) una tarifa.
    
    Solo se permite si no tiene cursos activos asociados.
    """
    user = getattr(g, 'current_user', None)
    
    tarifa = db.session.get(Tarifa, tarifa_id)
    if not tarifa:
        return jsonify({"ok": False, "error": "not_found"}), 404
    
    # Verificar permisos
    allowed, reason = can_delete_tarifa(user, tarifa)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Validar que no hay cursos activos con esta tarifa
    cursos_activos = Curso.query.filter(
        Curso.tarifa_id == tarifa_id,
        Curso.estado == 'Activo'
    ).count()
    
    if cursos_activos > 0:
        return jsonify({
            "ok": False,
            "error": "has_dependents",
            "message": "No se puede eliminar la tarifa porque tiene cursos activos asociados",
            "details": {"cursos_activos": cursos_activos}
        }), 409
    
    # Soft-delete
    try:
        tarifa.fecha_baja = datetime.now(timezone.utc)
        db.session.add(tarifa)
        db.session.commit()
        
        result = tarifa_schema.dump(tarifa)
        return jsonify({"ok": True, "result": result}), 200
    except Exception as e:
        db.session.rollback()
        if Config.DEBUG:
            print(f"[ERROR] eliminar_tarifa: {e}")
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500
