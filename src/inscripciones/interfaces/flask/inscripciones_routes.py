"""Rutas Flask para gestión de Inscripciones."""
from flask import Blueprint, jsonify, request, g
from webargs.flaskparser import use_args
from webargs import fields
from datetime import datetime, date

from src.shared.middleware.auth import require_auth
from src.shared.application.permissions import (
    can_query_inscripciones,
    can_create_inscripcion,
    can_view_inscripcion,
    can_modify_inscripcion,
    can_delete_inscripcion
)
from src.shared.docs.operation_id import operation_id
from src.shared.docs.openapi_args import openapi_query_args
from src.shared.pagination import clamp_pagination, build_page_envelope, DEFAULT_PAGE, DEFAULT_SIZE, MAX_PAGE_SIZE
from src.shared.database import db
from src.schemas.inscripcion import (
    InscripcionSchema,
    InscripcionCreateSchema,
    InscripcionUpdateSchema
)
import logging

logger = logging.getLogger(__name__)

from sqlalchemy import Table, MetaData, select, and_, func
metadata = MetaData()

# Lazy loading de tablas
_tables_loaded = False
inscripciones = None
alumnos = None
cursos = None
tarifas = None
curso_profesores = None

def _load_tables():
    """Carga las tablas de forma lazy al primer uso."""
    global _tables_loaded, inscripciones, alumnos, cursos, tarifas, curso_profesores
    if not _tables_loaded:
        inscripciones = Table('inscripcion', metadata, autoload_with=db.engine)
        alumnos = Table('alumno', metadata, autoload_with=db.engine)
        cursos = Table('curso', metadata, autoload_with=db.engine)
        tarifas = Table('tarifa', metadata, autoload_with=db.engine)
        curso_profesores = Table('curso_profesores', metadata, autoload_with=db.engine)
        _tables_loaded = True

inscripciones_bp = Blueprint('inscripciones', __name__)

# Definición de parámetros de query para GET /inscripciones
inscripciones_list_query_args = {
    'academia_id': {
        'type': 'integer',
        'description': 'Filtrar por ID de academia (solo admin_plataforma)',
        'required': False
    },
    'alumno_id': {
        'type': 'integer',
        'description': 'Filtrar por ID de alumno específico',
        'required': False
    },
    'curso_id': {
        'type': 'integer',
        'description': 'Filtrar por ID de curso específico',
        'required': False
    },
    'tarifa_id': {
        'type': 'integer',
        'description': 'Filtrar por ID de tarifa',
        'required': False
    },
    'activas': {
        'type': 'boolean',
        'description': 'Filtrar por inscripciones activas (true) o finalizadas (false)',
        'required': False
    },
    'fecha_inicio_desde': {
        'type': 'string',
        'description': 'Filtrar inscripciones desde fecha inicio (formato: YYYY-MM-DD)',
        'required': False
    },
    'fecha_inicio_hasta': {
        'type': 'string',
        'description': 'Filtrar inscripciones hasta fecha inicio (formato: YYYY-MM-DD)',
        'required': False
    },
    'page': {
        'type': 'integer',
        'description': 'Número de página (inicia en 1)',
        'required': False,
        'default': 1,
        'minimum': 1
    },
    'size': {
        'type': 'integer',
        'description': 'Tamaño de página',
        'required': False,
        'default': 20,
        'minimum': 1,
        'maximum': 100
    },
    'with_total': {
        'type': 'boolean',
        'description': 'Incluir conteo total de resultados',
        'required': False
    },
    'order_by': {
        'type': 'string',
        'description': 'Campo para ordenar (id, fecha_inicio, fecha_fin)',
        'required': False
    },
    'order_dir': {
        'type': 'string',
        'description': 'Dirección del ordenamiento (asc, desc)',
        'required': False
    },
    'expand': {
        'type': 'string',
        'description': 'Expandir relaciones (alumno, curso, tarifa)',
        'required': False
    }
}

@inscripciones_bp.route('/', methods=['GET'])
@require_auth
@operation_id('inscripciones.listar_inscripciones')
@openapi_query_args(inscripciones_list_query_args)
@use_args({
    'academia_id': fields.Int(required=False),
    'alumno_id': fields.Int(required=False),
    'curso_id': fields.Int(required=False),
    'tarifa_id': fields.Int(required=False),
    'activas': fields.Bool(required=False),
    'fecha_inicio_desde': fields.Str(required=False),
    'fecha_inicio_hasta': fields.Str(required=False),
    'page': fields.Int(required=False, load_default=1),
    'size': fields.Int(required=False, load_default=20),
    'with_total': fields.Bool(required=False),
    'order_by': fields.Str(required=False),
    'order_dir': fields.Str(required=False),
    'expand': fields.Str(required=False)
}, location='query')
def listar_inscripciones(args, current_user):
    """Lista inscripciones (matrículas) según permisos del usuario.
    
    Permite consultar inscripciones filtradas por:
    - Academia (solo admin_plataforma)
    - Alumno específico
    - Curso específico  
    - Tarifa aplicada
    - Estado (activas/finalizadas)
    - Rango de fechas de inicio
    
    Soporta paginación, ordenamiento y expansión de relaciones.
    
    Casos de uso:
    - Ver todas las matrículas de una academia
    - Consultar inscripciones de un alumno
    - Listar alumnos matriculados en un curso
    - Filtrar por estado activo/finalizado
    """
    _load_tables()
    logger.info(f"listar_inscripciones llamado por user {current_user.get('usuario_id')} con args: {args}")
    
    page, size = clamp_pagination(args.get('page', 1), args.get('size', 20))
    
    perm_result = can_query_inscripciones(current_user, args)
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    query = select(inscripciones)
    
    enforced_filters = perm_result.get('enforced_filters', {})
    
    # Si es profesor, solo ve inscripciones de sus cursos
    if 'profesor_academia' in current_user['roles']:
        query = query.select_from(
            inscripciones
            .join(cursos, inscripciones.c.curso_id == cursos.c.id)
            .join(curso_profesores,
                  and_(
                      curso_profesores.c.curso_id == cursos.c.id,
                      curso_profesores.c.usuario_id == current_user['usuario_id'],
                      curso_profesores.c.fecha_baja.is_(None)
                  ))
        )
    
    # Filtro de academia para admin_academia
    if 'academia_id' in enforced_filters:
        query = query.where(inscripciones.c.academia_id == enforced_filters['academia_id'])
    
    # Filtros opcionales
    if args.get('academia_id'):
        # Solo admin_plataforma puede filtrar por academia_id explícitamente
        if 'admin_plataforma' in current_user.get('roles', []):
            query = query.where(inscripciones.c.academia_id == args['academia_id'])
    
    if args.get('alumno_id'):
        query = query.where(inscripciones.c.alumno_id == args['alumno_id'])
    
    if args.get('curso_id'):
        query = query.where(inscripciones.c.curso_id == args['curso_id'])
    
    if args.get('tarifa_id'):
        query = query.where(inscripciones.c.tarifa_id == args['tarifa_id'])
    
    if args.get('activas') is not None:
        if args['activas']:
            query = query.where(inscripciones.c.fecha_fin.is_(None))
        else:
            query = query.where(inscripciones.c.fecha_fin.isnot(None))
    
    # Filtros de fecha de inicio
    if args.get('fecha_inicio_desde'):
        try:
            fecha_desde = datetime.strptime(args['fecha_inicio_desde'], '%Y-%m-%d').date()
            query = query.where(inscripciones.c.fecha_inicio >= fecha_desde)
        except ValueError:
            return jsonify({'ok': False, 'error': 'Formato de fecha_inicio_desde inválido (use YYYY-MM-DD)'}), 400
    
    if args.get('fecha_inicio_hasta'):
        try:
            fecha_hasta = datetime.strptime(args['fecha_inicio_hasta'], '%Y-%m-%d').date()
            query = query.where(inscripciones.c.fecha_inicio <= fecha_hasta)
        except ValueError:
            return jsonify({'ok': False, 'error': 'Formato de fecha_inicio_hasta inválido (use YYYY-MM-DD)'}), 400
    
    # Ordenamiento
    order_whitelist = ['id', 'fecha_inicio', 'fecha_fin']
    order_by = args.get('order_by', 'fecha_inicio')
    order_dir = args.get('order_dir', 'desc').lower()
    
    if order_by in order_whitelist:
        order_column = getattr(inscripciones.c, order_by)
        if order_dir == 'asc':
            query = query.order_by(order_column.asc())
        else:
            query = query.order_by(order_column.desc())
    else:
        query = query.order_by(inscripciones.c.fecha_inicio.desc())
    
    # Conteo total si se solicita
    total = None
    if args.get('with_total'):
        count_query = select(func.count()).select_from(query.alias())
        with db.engine.connect() as conn:
            total = conn.execute(count_query).scalar()
    
    offset = (page - 1) * size
    query = query.limit(size).offset(offset)
    
    try:
        with db.engine.connect() as conn:
            rows = conn.execute(query).mappings().fetchall()
            schema = InscripcionSchema(many=True)
            result = schema.dump(rows)
            
            # Usar build_page_envelope para respuesta paginada
            envelope = build_page_envelope(
                items=result,
                page=page,
                size=size,
                total=total
            )
            
            return jsonify(envelope), 200
    except Exception as e:
        logger.error(f"Error listando inscripciones: {e}")
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@inscripciones_bp.route('/', methods=['POST'])
@require_auth
@operation_id('inscripciones.crear_inscripcion')
def crear_inscripcion(current_user):
    """Crea una nueva inscripción."""
    _load_tables()
    logger.info(f"crear_inscripcion llamado por user {current_user.get('usuario_id')}")
    try:
        schema = InscripcionCreateSchema()
        payload = schema.load(request.get_json() or {})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    
    perm_result = can_create_inscripcion(current_user, payload)
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    # Validar que alumno y curso existen y pertenecen a la misma academia
    with db.engine.connect() as conn:
        alumno = conn.execute(
            select(alumnos).where(alumnos.c.id == payload['alumno_id'])
        ).mappings().fetchone()
        
        if not alumno:
            return jsonify({'ok': False, 'error': 'alumno_id no existe'}), 404
        
        curso = conn.execute(
            select(cursos).where(cursos.c.id == payload['curso_id'])
        ).mappings().fetchone()
        
        if not curso:
            return jsonify({'ok': False, 'error': 'curso_id no existe'}), 404
        
        if alumno['academia_id'] != curso['academia_id']:
            return jsonify({'ok': False, 'error': 'El alumno y el curso deben pertenecer a la misma academia'}), 409
        
        # Calcular academia_id automáticamente
        academia_id = alumno['academia_id']
        
        # Validar que la tarifa pertenece a la academia del curso
        tarifa = conn.execute(
            select(tarifas).where(tarifas.c.id == payload['tarifa_id'])
        ).mappings().fetchone()
        
        if not tarifa:
            return jsonify({'ok': False, 'error': 'tarifa_id no existe'}), 404
        
        if tarifa['academia_id'] != academia_id:
            return jsonify({'ok': False, 'error': 'La tarifa debe pertenecer a la misma academia del curso'}), 409
        
        # Verificar capacidad del curso
        if curso.get('capacidad_maxima'):
            inscripciones_activas = conn.execute(
                select(func.count(inscripciones.c.id))
                .where(
                    and_(
                        inscripciones.c.curso_id == payload['curso_id'],
                        inscripciones.c.fecha_fin.is_(None)
                    )
                )
            ).scalar()
            
            if inscripciones_activas >= curso['capacidad_maxima']:
                return jsonify({'ok': False, 'error': 'El curso ha alcanzado su capacidad máxima'}), 409
        
        # Verificar que no existe inscripción activa duplicada
        inscripcion_existente = conn.execute(
            select(inscripciones).where(
                and_(
                    inscripciones.c.alumno_id == payload['alumno_id'],
                    inscripciones.c.curso_id == payload['curso_id'],
                    inscripciones.c.fecha_fin.is_(None)
                )
            )
        ).mappings().fetchone()
        
        if inscripcion_existente:
            return jsonify({'ok': False, 'error': 'El alumno ya tiene una inscripción activa en este curso'}), 409
        
        # Agregar academia_id al payload para INSERT
        payload['academia_id'] = academia_id
    
    try:
        insert_stmt = inscripciones.insert().values(**payload)
        
        with db.engine.connect() as conn:
            result = conn.execute(insert_stmt)
            conn.commit()
            inscripcion_id = result.inserted_primary_key[0]
            
            inscripcion = conn.execute(
                select(inscripciones).where(inscripciones.c.id == inscripcion_id)
            ).mappings().fetchone()
            
            schema = InscripcionSchema()
            return jsonify({'ok': True, 'result': schema.dump(inscripcion)}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@inscripciones_bp.route('/<int:inscripcion_id>', methods=['GET'])
@require_auth
@operation_id('inscripciones.obtener_inscripcion')
def obtener_inscripcion(inscripcion_id, current_user):
    """Obtiene una inscripción por ID."""
    _load_tables()
    with db.engine.connect() as conn:
        inscripcion = conn.execute(
            select(inscripciones).where(inscripciones.c.id == inscripcion_id)
        ).mappings().fetchone()
        
        if not inscripcion:
            return jsonify({'ok': False, 'error': 'Inscripción no encontrada'}), 404
    
    perm_result = can_view_inscripcion(current_user, {'inscripcion_id': inscripcion_id})
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    schema = InscripcionSchema()
    return jsonify({'ok': True, 'result': schema.dump(inscripcion)}), 200


@inscripciones_bp.route('/<int:inscripcion_id>', methods=['PATCH', 'PUT'])
@require_auth
@operation_id('inscripciones.actualizar_inscripcion')
def actualizar_inscripcion(inscripcion_id, current_user):
    """Actualiza una inscripción (típicamente para dar de baja)."""
    _load_tables()
    with db.engine.connect() as conn:
        inscripcion = conn.execute(
            select(inscripciones).where(inscripciones.c.id == inscripcion_id)
        ).mappings().fetchone()
        
        if not inscripcion:
            return jsonify({'ok': False, 'error': 'Inscripción no encontrada'}), 404
    
    try:
        schema = InscripcionUpdateSchema()
        payload = schema.load(request.get_json() or {})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    
    perm_result = can_modify_inscripcion(current_user, {'inscripcion_id': inscripcion_id, **payload})
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    sanitized = perm_result.get('sanitized_payload', payload)
    
    # Validar cambio de tarifa si se solicita
    if 'tarifa_id' in sanitized:
        with db.engine.connect() as conn:
            curso = conn.execute(
                select(cursos).where(cursos.c.id == inscripcion['curso_id'])
            ).mappings().fetchone()
            
            tarifa = conn.execute(
                select(tarifas).where(tarifas.c.id == sanitized['tarifa_id'])
            ).mappings().fetchone()
            
            if not tarifa:
                return jsonify({'ok': False, 'error': 'tarifa_id no existe'}), 404
            
            if tarifa['academia_id'] != curso['academia_id']:
                return jsonify({'ok': False, 'error': 'La tarifa debe pertenecer a la misma academia'}), 409
    
    try:
        update_stmt = inscripciones.update().where(inscripciones.c.id == inscripcion_id).values(**sanitized)
        
        with db.engine.connect() as conn:
            conn.execute(update_stmt)
            conn.commit()
            
            inscripcion_updated = conn.execute(
                select(inscripciones).where(inscripciones.c.id == inscripcion_id)
            ).mappings().fetchone()
            
            schema = InscripcionSchema()
            return jsonify({'ok': True, 'result': schema.dump(inscripcion_updated)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@inscripciones_bp.route('/<int:inscripcion_id>', methods=['DELETE'])
@require_auth
@operation_id('inscripciones.eliminar_inscripcion')
def eliminar_inscripcion(inscripcion_id, current_user):
    """Elimina una inscripción (mejor usar PATCH para dar de baja)."""
    _load_tables()
    with db.engine.connect() as conn:
        inscripcion = conn.execute(
            select(inscripciones).where(inscripciones.c.id == inscripcion_id)
        ).mappings().fetchone()
        
        if not inscripcion:
            return jsonify({'ok': False, 'error': 'Inscripción no encontrada'}), 404
    
    perm_result = can_delete_inscripcion(current_user, {'inscripcion_id': inscripcion_id})
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    # Mejor práctica: dar de baja con fecha_fin
    try:
        update_stmt = inscripciones.update().where(inscripciones.c.id == inscripcion_id).values(
            fecha_fin=date.today(),
            motivo_baja='Eliminación manual'
        )
        
        with db.engine.connect() as conn:
            conn.execute(update_stmt)
            conn.commit()
            
            return jsonify({'ok': True, 'result': 'Inscripción dada de baja correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500
