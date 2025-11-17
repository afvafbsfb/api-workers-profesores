"""Rutas Flask para gestión de Anotaciones de Alumnos en Sesiones."""
from flask import Blueprint, jsonify, request, g
from webargs.flaskparser import use_args
from webargs import fields
from datetime import datetime

from src.shared.middleware.auth import require_auth
from src.shared.application.permissions import (
    can_query_anotaciones,
    can_create_anotacion,
    can_view_anotacion,
    can_modify_anotacion,
    can_delete_anotacion
)
from src.shared.docs.operation_id import operation_id
from src.shared.docs.openapi_args import openapi_query_args
from src.shared.pagination import clamp_pagination, build_page_envelope, DEFAULT_PAGE, DEFAULT_SIZE, MAX_PAGE_SIZE
from src.shared.database import db
from src.schemas.anotacion import (
    AnotacionSchema,
    AnotacionCreateSchema,
    AnotacionUpdateSchema
)
import logging

logger = logging.getLogger(__name__)

from sqlalchemy import Table, MetaData, select, and_
metadata = MetaData()

# Lazy loading de tablas
_tables_loaded = False
anotaciones = None
sesiones = None
inscripciones = None
cursos = None
curso_profesores = None
alumnos = None

def _load_tables():
    """Carga las tablas de forma lazy al primer uso."""
    global _tables_loaded, anotaciones, sesiones, inscripciones, cursos, curso_profesores, alumnos
    if not _tables_loaded:
        anotaciones = Table('anotacionesalumnosesion', metadata, autoload_with=db.engine)
        sesiones = Table('sesion', metadata, autoload_with=db.engine)
        inscripciones = Table('inscripcion', metadata, autoload_with=db.engine)
        cursos = Table('curso', metadata, autoload_with=db.engine)
        curso_profesores = Table('curso_profesores', metadata, autoload_with=db.engine)
        alumnos = Table('alumno', metadata, autoload_with=db.engine)
        _tables_loaded = True

anotaciones_bp = Blueprint('anotaciones', __name__)


# ============================================================
# GET / - Listar anotaciones
# ============================================================

anotaciones_list_query_args = {
    'sesion_id': {
        'type': 'integer',
        'description': 'Filtrar por ID de sesión',
        'required': False,
        'example': 123
    },
    'alumno_id': {
        'type': 'integer',
        'description': 'Filtrar por ID de alumno',
        'required': False,
        'example': 5
    },
    'curso_id': {
        'type': 'integer',
        'description': 'Filtrar por ID de curso',
        'required': False,
        'example': 1
    },
    'tipo_anotacion': {
        'type': 'string',
        'description': 'Filtrar por tipo específico de anotación',
        'required': False,
        'enum': ['Ausencia', 'Evaluacion', 'Comportamiento', 'Observacion', 'Otros'],
        'example': 'Evaluacion'
    },
    'excluir_tipo': {
        'type': 'string',
        'description': 'Excluir anotaciones de un tipo específico (ej: excluir_tipo=Ausencia para ver solo anotaciones académicas)',
        'required': False,
        'enum': ['Ausencia', 'Evaluacion', 'Comportamiento', 'Observacion', 'Otros'],
        'example': 'Ausencia'
    },
    'fecha_desde': {
        'type': 'string',
        'format': 'date',
        'description': 'Filtrar anotaciones desde esta fecha (formato YYYY-MM-DD)',
        'required': False,
        'example': '2024-09-01'
    },
    'fecha_hasta': {
        'type': 'string',
        'format': 'date',
        'description': 'Filtrar anotaciones hasta esta fecha (formato YYYY-MM-DD)',
        'required': False,
        'example': '2024-12-31'
    },
    'activas': {
        'type': 'boolean',
        'description': 'Si true, solo anotaciones activas. Si false, solo inactivas. Si se omite, solo activas por defecto',
        'required': False,
        'example': True
    },
    'page': {
        'type': 'integer',
        'description': 'Número de página',
        'required': False,
        'example': 1
    },
    'size': {
        'type': 'integer',
        'description': 'Tamaño de página',
        'required': False,
        'example': 20
    },
    'with_total': {
        'type': 'boolean',
        'description': 'Incluir conteo total de resultados',
        'required': False,
        'example': False
    },
    'order_by': {
        'type': 'string',
        'description': 'Campo por el cual ordenar',
        'required': False,
        'enum': ['id', 'timestamp_alta', 'tipo_anotacion'],
        'example': 'timestamp_alta'
    },
    'order_dir': {
        'type': 'string',
        'description': 'Dirección de ordenamiento',
        'required': False,
        'enum': ['asc', 'desc'],
        'example': 'desc'
    },
    'expand': {
        'type': 'string',
        'description': 'Expandir relaciones (separadas por comas). Opciones: sesion, alumno, inscripcion',
        'required': False,
        'example': 'alumno,sesion'
    }
}

ORDER_WHITELIST = ['id', 'timestamp_alta', 'tipo_anotacion']

@anotaciones_bp.route('/', methods=['GET'])
@require_auth
@operation_id('anotaciones.listar_anotaciones')
@openapi_query_args(anotaciones_list_query_args)
def listar_anotaciones(current_user):
    """Lista anotaciones de alumnos en sesiones según permisos del usuario.
    
    TIPOS DE ANOTACIONES disponibles:
    - Ausencia: Registrada automáticamente al pasar lista (no editable manualmente)
    - Evaluacion: Anotaciones académicas (ej: "Excelente participación", "Necesita refuerzo")
    - Comportamiento: Anotaciones de conducta (ej: "Disruptivo en clase", "Muy colaborador")
    - Observacion: Notas generales del profesor
    - Otros: Categoría genérica para otras observaciones
    
    CASOS DE USO COMUNES:
    
    1. Ver todas las anotaciones de una sesión (panel del profesor):
       GET /anotaciones?sesion_id=123&order_by=timestamp_alta&order_dir=desc
    
    2. Ver anotaciones académicas de un alumno en una sesión (excluyendo ausencias):
       GET /anotaciones?sesion_id=123&alumno_id=5&excluir_tipo=Ausencia
    
    3. Historial completo de un alumno en un rango de fechas:
       GET /anotaciones?alumno_id=5&fecha_desde=2024-09-01&fecha_hasta=2024-12-31&page=1&size=20
    
    4. Solo anotaciones de comportamiento de un curso:
       GET /anotaciones?curso_id=1&tipo_anotacion=Comportamiento
    
    Parámetros de consulta disponibles:
    - sesion_id: Filtrar por sesión específica
    - alumno_id: Filtrar por alumno específico
    - curso_id: Filtrar por curso
    - tipo_anotacion: Filtrar por tipo específico (Ausencia, Evaluacion, Comportamiento, Observacion, Otros)
    - excluir_tipo: Excluir un tipo específico (útil para excluir Ausencia)
    - fecha_desde/fecha_hasta: Rango de fechas
    - activas: true=solo activas, false=solo inactivas, omitido=solo activas
    - page/size: Paginación
    - with_total: Incluir conteo total
    - order_by/order_dir: Ordenamiento (timestamp_alta, tipo_anotacion, id)
    - expand: Expandir relaciones (alumno, sesion, inscripcion)
    
    Respuesta ejemplo:
    {
        "ok": true,
        "result": [
            {
                "id": 1,
                "sesion_id": 123,
                "alumno_id": 5,
                "tipo_anotacion": "Evaluacion",
                "texto": "Excelente participación en clase",
                "timestamp_alta": "2024-10-15T10:30:00"
            }
        ],
        "page": 1,
        "size": 20,
        "total": 150  // solo si with_total=true
    }
    """
    _load_tables()
    
    args = request.args.to_dict()
    page = int(args.get('page', DEFAULT_PAGE))
    size = int(args.get('size', DEFAULT_SIZE))
    page, size = clamp_pagination(page, size)
    
    _load_tables()
    
    args = request.args.to_dict()
    page = int(args.get('page', DEFAULT_PAGE))
    size = int(args.get('size', DEFAULT_SIZE))
    page, size = clamp_pagination(page, size)
    with_total = args.get('with_total', '').lower() == 'true'
    order_by = args.get('order_by', 'timestamp_alta')
    order_dir = args.get('order_dir', 'desc')
    
    if order_by not in ORDER_WHITELIST:
        order_by = 'timestamp_alta'
    if order_dir not in ['asc', 'desc']:
        order_dir = 'desc'
    
    perm_result = can_query_anotaciones(current_user, args)
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    query = select(anotaciones)
    
    # Si es profesor, solo ve anotaciones de sus sesiones
    if 'profesor_academia' in current_user['roles']:
        query = query.select_from(
            anotaciones.join(curso_profesores,
                           and_(
                               anotaciones.c.curso_profesor_id == curso_profesores.c.id,
                               curso_profesores.c.usuario_id == current_user['usuario_id'],
                               curso_profesores.c.fecha_baja.is_(None)
                           ))
        )
    
    # Filtro de academia para admin_academia
    enforced_filters = perm_result.get('enforced_filters', {})
    if 'academia_id' in enforced_filters:
        query = query.select_from(
            anotaciones.join(cursos, anotaciones.c.curso_id == cursos.c.id)
        ).where(cursos.c.academia_id == enforced_filters['academia_id'])
    
    # Filtros opcionales
    if args.get('sesion_id'):
        query = query.where(anotaciones.c.sesion_id == int(args['sesion_id']))
    
    if args.get('alumno_id'):
        query = query.where(anotaciones.c.alumno_id == int(args['alumno_id']))
    
    if args.get('curso_id'):
        query = query.where(anotaciones.c.curso_id == int(args['curso_id']))
    
    # Filtro por tipo específico
    if args.get('tipo_anotacion'):
        query = query.where(anotaciones.c.tipo_anotacion == args['tipo_anotacion'])
    
    # Filtro para EXCLUIR un tipo (ej: excluir_tipo=Ausencia)
    if args.get('excluir_tipo'):
        query = query.where(anotaciones.c.tipo_anotacion != args['excluir_tipo'])
    
    # Filtros de fecha
    if args.get('fecha_desde'):
        from datetime import datetime
        fecha_desde = datetime.strptime(args['fecha_desde'], '%Y-%m-%d').date()
        query = query.where(db.func.date(anotaciones.c.timestamp_alta) >= fecha_desde)
    
    if args.get('fecha_hasta'):
        from datetime import datetime
        fecha_hasta = datetime.strptime(args['fecha_hasta'], '%Y-%m-%d').date()
        query = query.where(db.func.date(anotaciones.c.timestamp_alta) <= fecha_hasta)
    
    # Filtro de activas/inactivas
    if args.get('activas') is not None:
        activas_str = args.get('activas', '').lower()
        if activas_str == 'true':
            query = query.where(anotaciones.c.timestamp_baja.is_(None))
        elif activas_str == 'false':
            query = query.where(anotaciones.c.timestamp_baja.isnot(None))
    else:
        # Por defecto, solo activas
        query = query.where(anotaciones.c.timestamp_baja.is_(None))
    
    # Ordenamiento
    order_column = getattr(anotaciones.c, order_by)
    query = query.order_by(order_column.desc() if order_dir == 'desc' else order_column.asc())
    
    try:
        with db.engine.connect() as conn:
            # Conteo total si se solicita
            total = None
            if with_total:
                count_query = select(db.func.count()).select_from(query.alias())
                total = conn.execute(count_query).scalar()
            
            # Paginación
            offset = (page - 1) * size
            query = query.limit(size).offset(offset)
            
            rows = conn.execute(query).mappings().fetchall()
            schema = AnotacionSchema(many=True)
            result = schema.dump(rows)
            
            response = build_page_envelope(result, page, size, total)
            return jsonify(response), 200
    except Exception as e:
        logger.error(f"Error listando anotaciones: {str(e)}")
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# POST / - Crear anotación
# ============================================================
@anotaciones_bp.route('/', methods=['POST'])
@require_auth
@operation_id('anotaciones.crear_anotacion')
def crear_anotacion(current_user):
    """Crea una nueva anotación para un alumno en una sesión.
    
    IMPORTANTE: Las anotaciones de tipo "Ausencia" se gestionan automáticamente 
    mediante el endpoint POST /sesiones/{sesion_id}/pasar-lista y NO deben 
    crearse manualmente.
    
    TIPOS DE ANOTACIONES permitidos para creación manual:
    - Evaluacion: Anotaciones académicas (rendimiento, participación, etc.)
    - Comportamiento: Observaciones de conducta
    - Observacion: Notas generales del profesor
    - Otros: Categoría genérica
    
    Body JSON ejemplo:
    {
        "sesion_id": 123,
        "alumno_id": 5,
        "tipo_anotacion": "Evaluacion",
        "texto": "Excelente participación en la discusión sobre gramática inglesa"
    }
    
    Validaciones automáticas:
    - La sesión debe existir y estar activa
    - El alumno debe estar inscrito en el curso de la sesión
    - El profesor debe estar asignado al curso (si el creador es profesor)
    - tipo_anotacion debe ser uno de los valores permitidos
    
    Respuesta ejemplo:
    {
        "ok": true,
        "result": {
            "id": 456,
            "sesion_id": 123,
            "alumno_id": 5,
            "tipo_anotacion": "Evaluacion",
            "texto": "Excelente participación...",
            "timestamp_alta": "2024-11-17T10:30:00"
        }
    }
    """
    _load_tables()
    
    try:
        schema = AnotacionCreateSchema()
        payload = schema.load(request.get_json() or {})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    
    perm_result = can_create_anotacion(current_user, payload)
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    # Validaciones complejas de FKs
    with db.engine.connect() as conn:
        # Validar sesion_id
        sesion = conn.execute(
            select(sesiones).where(sesiones.c.id == payload['sesion_id'])
        ).mappings().fetchone()
        
        if not sesion:
            return jsonify({'ok': False, 'error': 'sesion_id no existe'}), 404
        
        # Validar inscripcion_id
        inscripcion = conn.execute(
            select(inscripciones).where(inscripciones.c.id == payload['inscripcion_id'])
        ).mappings().fetchone()
        
        if not inscripcion:
            return jsonify({'ok': False, 'error': 'inscripcion_id no existe'}), 404
        
        # Validar coherencia: inscripcion debe ser del curso y alumno indicados
        if inscripcion['curso_id'] != payload['curso_id']:
            return jsonify({'ok': False, 'error': 'La inscripción no pertenece al curso indicado'}), 409
        
        if inscripcion['alumno_id'] != payload['alumno_id']:
            return jsonify({'ok': False, 'error': 'La inscripción no pertenece al alumno indicado'}), 409
        
        # Validar curso_profesor_id
        cp = conn.execute(
            select(curso_profesores).where(
                and_(
                    curso_profesores.c.id == payload['curso_profesor_id'],
                    curso_profesores.c.fecha_baja.is_(None)
                )
            )
        ).mappings().fetchone()
        
        if not cp:
            return jsonify({'ok': False, 'error': 'curso_profesor_id no válido o inactivo'}), 404
        
        # Si es profesor, validar que sea su asignación
        if 'profesor_academia' in current_user['roles'] and current_user['usuario_id'] != cp['usuario_id']:
            return jsonify({'ok': False, 'error': 'No puede crear anotaciones para otros profesores'}), 403
    
    try:
        insert_stmt = anotaciones.insert().values(
            **payload,
            timestamp_alta=datetime.now()
        )
        
        with db.engine.connect() as conn:
            result = conn.execute(insert_stmt)
            conn.commit()
            anotacion_id = result.inserted_primary_key[0]
            
            anotacion = conn.execute(
                select(anotaciones).where(anotaciones.c.id == anotacion_id)
            ).mappings().fetchone()
            
            schema = AnotacionSchema()
            logger.info(f"Anotación creada: id={anotacion_id}, tipo={payload.get('tipo_anotacion')}, sesion={payload.get('sesion_id')}, alumno={payload.get('alumno_id')}")
            return jsonify({'ok': True, 'result': schema.dump(anotacion)}), 201
    except Exception as e:
        logger.error(f"Error creando anotación: {str(e)}")
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@anotaciones_bp.route('/<int:anotacion_id>', methods=['GET'])
@require_auth
@operation_id('anotaciones.obtener_anotacion')
def obtener_anotacion(anotacion_id, current_user):
    """Obtiene una anotación por ID."""
    _load_tables()
    
    with db.engine.connect() as conn:
        anotacion = conn.execute(
            select(anotaciones).where(anotaciones.c.id == anotacion_id)
        ).mappings().fetchone()
        
        if not anotacion:
            return jsonify({'ok': False, 'error': 'Anotación no encontrada'}), 404
    
    perm_result = can_view_anotacion(current_user, {'anotacion_id': anotacion_id})
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    schema = AnotacionSchema()
    return jsonify({'ok': True, 'result': schema.dump(anotacion)}), 200


@anotaciones_bp.route('/<int:anotacion_id>', methods=['PATCH', 'PUT'])
@require_auth
@operation_id('anotaciones.actualizar_anotacion')
def actualizar_anotacion(anotacion_id, current_user):
    """Actualiza una anotación existente."""
    _load_tables()
    
    with db.engine.connect() as conn:
        anotacion = conn.execute(
            select(anotaciones).where(anotaciones.c.id == anotacion_id)
        ).mappings().fetchone()
        
        if not anotacion:
            return jsonify({'ok': False, 'error': 'Anotación no encontrada'}), 404
    
    try:
        schema = AnotacionUpdateSchema()
        payload = schema.load(request.get_json() or {})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    
    perm_result = can_modify_anotacion(current_user, {'anotacion_id': anotacion_id, **payload})
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    sanitized = perm_result.get('sanitized_payload', payload)
    
    # Si se marca como baja, añadir timestamp
    if 'motivo_baja' in sanitized and sanitized['motivo_baja']:
        if 'timestamp_baja' not in sanitized or not sanitized.get('timestamp_baja'):
            sanitized['timestamp_baja'] = datetime.now()
    
    try:
        update_stmt = anotaciones.update().where(anotaciones.c.id == anotacion_id).values(**sanitized)
        
        with db.engine.connect() as conn:
            conn.execute(update_stmt)
            conn.commit()
            
            anotacion_updated = conn.execute(
                select(anotaciones).where(anotaciones.c.id == anotacion_id)
            ).mappings().fetchone()
            
            schema = AnotacionSchema()
            return jsonify({'ok': True, 'result': schema.dump(anotacion_updated)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@anotaciones_bp.route('/<int:anotacion_id>', methods=['DELETE'])
@require_auth
@operation_id('anotaciones.eliminar_anotacion')
def eliminar_anotacion(anotacion_id, current_user):
    """Elimina (marca como baja) una anotación."""
    _load_tables()
    
    with db.engine.connect() as conn:
        anotacion = conn.execute(
            select(anotaciones).where(anotaciones.c.id == anotacion_id)
        ).mappings().fetchone()
        
        if not anotacion:
            return jsonify({'ok': False, 'error': 'Anotación no encontrada'}), 404
    
    perm_result = can_delete_anotacion(current_user, {'anotacion_id': anotacion_id})
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    try:
        update_stmt = anotaciones.update().where(anotaciones.c.id == anotacion_id).values(
            timestamp_baja=datetime.now(),
            motivo_baja='Eliminación manual'
        )
        
        with db.engine.connect() as conn:
            conn.execute(update_stmt)
            conn.commit()
            
            logger.info(f"Anotación eliminada: id={anotacion_id}")
            return jsonify({'ok': True, 'result': 'Anotación eliminada correctamente'}), 200
    except Exception as e:
        logger.error(f"Error eliminando anotación {anotacion_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500
