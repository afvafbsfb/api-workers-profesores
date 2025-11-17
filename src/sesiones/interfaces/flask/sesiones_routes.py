"""Rutas Flask para gestión de Sesiones."""
from flask import Blueprint, jsonify, request, g
from webargs.flaskparser import use_args
from webargs import fields
from marshmallow import Schema
from datetime import datetime

from src.shared.middleware.auth import require_auth
from src.shared.application.permissions import (
    can_query_sesiones,
    can_create_sesion,
    can_view_sesion,
    can_modify_sesion,
    can_pasar_lista
)
from src.shared.docs.operation_id import operation_id
from src.shared.docs.openapi_args import openapi_query_args
from src.shared.pagination import clamp_pagination, build_page_envelope, DEFAULT_PAGE, DEFAULT_SIZE, MAX_PAGE_SIZE
from src.shared.database import db
from src.schemas.sesion import (
    SesionSchema,
    SesionCreateSchema,
    SesionUpdateSchema
)
import logging

logger = logging.getLogger(__name__)

# Importar modelos necesarios
from sqlalchemy import Table, MetaData, select, and_, or_
metadata = MetaData()

# Lazy loading de tablas
_tables_loaded = False
sesiones = None
horarios_curso = None
cursos = None
aulas = None
curso_profesores = None
anotaciones = None
inscripciones = None
alumnos = None

def _load_tables():
    """Carga las tablas de forma lazy al primer uso."""
    global _tables_loaded, sesiones, horarios_curso, cursos, aulas, curso_profesores, anotaciones, inscripciones, alumnos
    if not _tables_loaded:
        sesiones = Table('sesion', metadata, autoload_with=db.engine)
        horarios_curso = Table('horariocurso', metadata, autoload_with=db.engine)
        cursos = Table('curso', metadata, autoload_with=db.engine)
        aulas = Table('aula', metadata, autoload_with=db.engine)
        curso_profesores = Table('curso_profesores', metadata, autoload_with=db.engine)
        anotaciones = Table('anotacionesalumnosesion', metadata, autoload_with=db.engine)
        inscripciones = Table('inscripcion', metadata, autoload_with=db.engine)
        alumnos = Table('alumno', metadata, autoload_with=db.engine)
        _tables_loaded = True

sesiones_bp = Blueprint('sesiones', __name__)


# ============================================================
# GET / - Listar sesiones
# ============================================================

sesiones_list_query_args = {
    'horario_curso_id': {
        'type': 'integer',
        'description': 'Filtrar por ID de horario curso',
        'required': False,
        'example': 1
    },
    'curso_id': {
        'type': 'integer',
        'description': 'Filtrar por ID de curso',
        'required': False,
        'example': 1
    },
    'aula_id': {
        'type': 'integer',
        'description': 'Filtrar por ID de aula',
        'required': False,
        'example': 1
    },
    'profesor_id': {
        'type': 'integer',
        'description': 'Filtrar por ID de profesor (usuario_id)',
        'required': False,
        'example': 5
    },
    'fecha_desde': {
        'type': 'string',
        'format': 'date',
        'description': 'Filtrar sesiones desde esta fecha (formato YYYY-MM-DD)',
        'required': False,
        'example': '2024-09-01'
    },
    'fecha_hasta': {
        'type': 'string',
        'format': 'date',
        'description': 'Filtrar sesiones hasta esta fecha (formato YYYY-MM-DD)',
        'required': False,
        'example': '2024-12-31'
    },
    'con_asistencia': {
        'type': 'boolean',
        'description': 'Si true, solo devuelve sesiones con asistencia registrada',
        'required': False,
        'example': False
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
        'enum': ['id', 'timestamp_alta', 'horario_curso_id'],
        'example': 'timestamp_alta'
    },
    'order_dir': {
        'type': 'string',
        'description': 'Dirección de ordenamiento',
        'required': False,
        'enum': ['asc', 'desc'],
        'example': 'desc'
    }
}

ORDER_WHITELIST = ['id', 'timestamp_alta', 'horario_curso_id']

@sesiones_bp.route('/', methods=['GET'])
@require_auth
@operation_id('sesiones.listar_sesiones')
@openapi_query_args(sesiones_list_query_args)
def listar_sesiones(current_user):
    """Lista sesiones según permisos del usuario.
    
    Parámetros de consulta disponibles:
    - horario_curso_id: Filtrar por horario de curso
    - curso_id: Filtrar por curso
    - aula_id: Filtrar por aula
    - profesor_id: Filtrar por profesor
    - fecha_desde/fecha_hasta: Rango de fechas
    - con_asistencia: Solo sesiones con asistencia registrada
    - page/size: Paginación
    - with_total: Incluir conteo total
    - order_by/order_dir: Ordenamiento
    
    Ejemplo de uso:
    GET /sesiones?curso_id=1&fecha_desde=2024-09-01&fecha_hasta=2024-12-31&page=1&size=20&order_by=timestamp_alta&order_dir=desc
    
    Respuesta:
    {
        "ok": true,
        "result": [...],
        "page": 1,
        "size": 20,
        "total": 150  # solo si with_total=true
    }
    """
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
    
    perm_result = can_query_sesiones(current_user, args)
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    # Query base
    query = select(sesiones)
    
    # Filtros de permisos (join con horario -> curso -> profesores si es necesario)
    enforced_filters = perm_result.get('enforced_filters', {})
    
    # Si es profesor_academia, solo ve sus sesiones
    if 'profesor_academia' in current_user['roles']:
        # Join necesario para filtrar por profesor
        query = query.select_from(
            sesiones
            .join(horarios_curso, sesiones.c.horario_curso_id == horarios_curso.c.id)
            .join(cursos, horarios_curso.c.curso_id == cursos.c.id)
            .join(curso_profesores, 
                  and_(
                      curso_profesores.c.curso_id == cursos.c.id,
                      curso_profesores.c.usuario_id == current_user['usuario_id'],
                      curso_profesores.c.fecha_baja.is_(None)
                  ))
        )
    
    # Aplicar filtros de academia si es admin_academia
    if 'academia_id' in enforced_filters:
        query = query.select_from(
            sesiones
            .join(horarios_curso, sesiones.c.horario_curso_id == horarios_curso.c.id)
            .join(cursos, horarios_curso.c.curso_id == cursos.c.id)
        ).where(cursos.c.academia_id == enforced_filters['academia_id'])
    
    # Filtros opcionales del usuario
    if args.get('horario_curso_id'):
        query = query.where(sesiones.c.horario_curso_id == int(args['horario_curso_id']))
    
    if args.get('curso_id'):
        if 'curso_profesores' not in query.froms:
            query = query.select_from(
                sesiones.join(horarios_curso, sesiones.c.horario_curso_id == horarios_curso.c.id)
            )
        query = query.where(horarios_curso.c.curso_id == int(args['curso_id']))
    
    if args.get('aula_id'):
        query = query.where(sesiones.c.aula_id == int(args['aula_id']))
    
    if args.get('profesor_id'):
        # Filtrar por profesor específico
        if 'curso_profesores' not in query.froms:
            query = query.select_from(
                sesiones
                .join(horarios_curso, sesiones.c.horario_curso_id == horarios_curso.c.id)
                .join(cursos, horarios_curso.c.curso_id == cursos.c.id)
                .join(curso_profesores, 
                      and_(
                          curso_profesores.c.curso_id == cursos.c.id,
                          curso_profesores.c.fecha_baja.is_(None)
                      ))
            )
        query = query.where(curso_profesores.c.usuario_id == int(args['profesor_id']))
    
    # Filtros de fecha (usar timestamp_alta como fecha de la sesión)
    if args.get('fecha_desde'):
        from datetime import datetime
        fecha_desde = datetime.strptime(args['fecha_desde'], '%Y-%m-%d').date()
        query = query.where(db.func.date(sesiones.c.timestamp_alta) >= fecha_desde)
    
    if args.get('fecha_hasta'):
        from datetime import datetime
        fecha_hasta = datetime.strptime(args['fecha_hasta'], '%Y-%m-%d').date()
        query = query.where(db.func.date(sesiones.c.timestamp_alta) <= fecha_hasta)
    
    # Excluir sesiones dadas de baja
    query = query.where(sesiones.c.timestamp_baja.is_(None))
    
    # Ordenar
    order_column = getattr(sesiones.c, order_by)
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
            schema = SesionSchema(many=True)
            result = schema.dump(rows)
            
            response = build_page_envelope(result, page, size, total)
            return jsonify(response), 200
    except Exception as e:
        logger.error(f"Error listando sesiones: {str(e)}")
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# POST / - Crear sesión
# ============================================================
@sesiones_bp.route('/', methods=['POST'])
@require_auth
@operation_id('sesiones.crear_sesion')
def crear_sesion(current_user):
    """Crea una nueva sesión."""
    _load_tables()
    
    try:
        schema = SesionCreateSchema()
        payload = schema.load(request.get_json() or {})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    
    perm_result = can_create_sesion(current_user, payload)
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    # Validar que horario_curso_id existe
    with db.engine.connect() as conn:
        horario = conn.execute(
            select(horarios_curso).where(horarios_curso.c.id == payload['horario_curso_id'])
        ).mappings().fetchone()
        
        if not horario:
            return jsonify({'ok': False, 'error': 'horario_curso_id no existe'}), 404
        
        # Validar que el curso pertenece a la academia del usuario (si es admin_academia)
        if 'admin_academia' in current_user['roles']:
            curso = conn.execute(
                select(cursos).where(cursos.c.id == horario['curso_id'])
            ).mappings().fetchone()
            
            if curso and curso['academia_id'] != current_user.get('academia_id'):
                return jsonify({'ok': False, 'error': 'No puede crear sesiones para cursos de otra academia'}), 403
        
        # Validar que aula_id existe y pertenece a la academia
        if 'admin_academia' in current_user['roles']:
            aula = conn.execute(
                select(aulas).where(aulas.c.id == payload['aula_id'])
            ).mappings().fetchone()
            
            if not aula:
                return jsonify({'ok': False, 'error': 'aula_id no existe'}), 404
            
            if aula['academia_id'] != current_user.get('academia_id'):
                return jsonify({'ok': False, 'error': 'El aula no pertenece a su academia'}), 403
        
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
            return jsonify({'ok': False, 'error': 'No puede crear sesiones para otros profesores'}), 403
    
    # Crear la sesión
    try:
        insert_stmt = sesiones.insert().values(
            horario_curso_id=payload['horario_curso_id'],
            aula_id=payload['aula_id'],
            curso_profesor_id=payload['curso_profesor_id'],
            hora_inicio=payload['hora_inicio'],
            hora_fin=payload['hora_fin'],
            notas_sesion=payload.get('notas_sesion'),
            notas_materia=payload.get('notas_materia'),
            timestamp_alta=datetime.now()
        )
        
        with db.engine.connect() as conn:
            result = conn.execute(insert_stmt)
            conn.commit()
            sesion_id = result.inserted_primary_key[0]
            
            # Obtener la sesión creada
            sesion = conn.execute(
                select(sesiones).where(sesiones.c.id == sesion_id)
            ).mappings().fetchone()
            
            schema = SesionSchema()
            return jsonify({'ok': True, 'result': schema.dump(sesion)}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# GET /<id> - Obtener sesión
# ============================================================
@sesiones_bp.route('/<int:sesion_id>', methods=['GET'])
@require_auth
@operation_id('sesiones.obtener_sesion')
def obtener_sesion(sesion_id, current_user):
    """Obtiene una sesión por ID."""
    _load_tables()
    
    with db.engine.connect() as conn:
        sesion = conn.execute(
            select(sesiones).where(sesiones.c.id == sesion_id)
        ).mappings().fetchone()
        
        if not sesion:
            return jsonify({'ok': False, 'error': 'Sesión no encontrada'}), 404
    
    perm_result = can_view_sesion(current_user, {'sesion_id': sesion_id})
    
    if not perm_result['allowed']:
        # Verificar si es profesor asignado al curso
        if 'profesor_academia' in current_user['roles']:
            with db.engine.connect() as conn:
                cp = conn.execute(
                    select(curso_profesores).where(
                        and_(
                            curso_profesores.c.id == sesion['curso_profesor_id'],
                            curso_profesores.c.usuario_id == current_user['usuario_id'],
                            curso_profesores.c.fecha_baja.is_(None)
                        )
                    )
                ).mappings().fetchone()
                
                if not cp:
                    return jsonify({'ok': False, 'error': 'No autorizado para ver esta sesión'}), 403
        else:
            return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    schema = SesionSchema()
    return jsonify({'ok': True, 'result': schema.dump(sesion)}), 200


# ============================================================
# PATCH/PUT /<id> - Actualizar sesión
# ============================================================
@sesiones_bp.route('/<int:sesion_id>', methods=['PATCH', 'PUT'])
@require_auth
@operation_id('sesiones.actualizar_sesion')
def actualizar_sesion(sesion_id, current_user):
    """Actualiza una sesión existente."""
    _load_tables()
    
    with db.engine.connect() as conn:
        sesion = conn.execute(
            select(sesiones).where(sesiones.c.id == sesion_id)
        ).mappings().fetchone()
        
        if not sesion:
            return jsonify({'ok': False, 'error': 'Sesión no encontrada'}), 404
    
    try:
        schema = SesionUpdateSchema()
        payload = schema.load(request.get_json() or {})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    
    perm_result = can_modify_sesion(current_user, {'sesion_id': sesion_id, **payload})
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    # Aplicar payload sanitizado
    sanitized = perm_result.get('sanitized_payload', payload)
    
    # Validaciones de aula si se cambia
    if 'aula_id' in sanitized:
        with db.engine.connect() as conn:
            aula = conn.execute(
                select(aulas).where(aulas.c.id == sanitized['aula_id'])
            ).mappings().fetchone()
            
            if not aula:
                return jsonify({'ok': False, 'error': 'aula_id no existe'}), 404
            
            if 'admin_academia' in current_user['roles']:
                if aula['academia_id'] != current_user.get('academia_id'):
                    return jsonify({'ok': False, 'error': 'El aula no pertenece a su academia'}), 403
    
    # Si se marca como baja, requerir motivo
    if 'motivo_baja' in sanitized and sanitized['motivo_baja']:
        if 'timestamp_baja' not in sanitized or not sanitized.get('timestamp_baja'):
            sanitized['timestamp_baja'] = datetime.now()
    
    try:
        update_stmt = sesiones.update().where(sesiones.c.id == sesion_id).values(**sanitized)
        
        with db.engine.connect() as conn:
            conn.execute(update_stmt)
            conn.commit()
            
            # Obtener sesión actualizada
            sesion_updated = conn.execute(
                select(sesiones).where(sesiones.c.id == sesion_id)
            ).mappings().fetchone()
            
            schema = SesionSchema()
            return jsonify({'ok': True, 'result': schema.dump(sesion_updated)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# DELETE /<id> - Eliminar sesión (soft delete)
# ============================================================
@sesiones_bp.route('/<int:sesion_id>', methods=['DELETE'])
@require_auth
@operation_id('sesiones.eliminar_sesion')
def eliminar_sesion(sesion_id, current_user):
    """Elimina (marca como baja) una sesión."""
    _load_tables()
    
    with db.engine.connect() as conn:
        sesion = conn.execute(
            select(sesiones).where(sesiones.c.id == sesion_id)
        ).mappings().fetchone()
        
        if not sesion:
            return jsonify({'ok': False, 'error': 'Sesión no encontrada'}), 404
    
    perm_result = can_modify_sesion(current_user, sesion, {})
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    try:
        # Soft delete: marcar timestamp_baja
        update_stmt = sesiones.update().where(sesiones.c.id == sesion_id).values(
            timestamp_baja=datetime.now(),
            motivo_baja='Eliminación manual'
        )
        
        with db.engine.connect() as conn:
            conn.execute(update_stmt)
            conn.commit()
            
            return jsonify({'ok': True, 'result': 'Sesión eliminada correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# POST /<sesion_id>/pasar-lista - Pasar lista batch (ENDPOINT ESPECIAL)
# ============================================================
@sesiones_bp.route('/<int:sesion_id>/pasar-lista', methods=['POST'])
@require_auth
@operation_id('sesiones.pasar_lista')
def pasar_lista(sesion_id, current_user):
    """Registra asistencia de múltiples alumnos en una sesión.
    
    Body esperado:
    {
        "alumnos": [
            {"alumno_id": 1, "ausente": true},
            {"alumno_id": 2, "ausente": false},
            {"alumno_id": 3, "ausente": true}
        ]
    }
    
    Lógica:
    - Si ausente=true: crear/actualizar anotación tipo 'Ausencia'
    - Si ausente=false: eliminar anotación de ausencia si existe (marcar como presente)
    
    Respuesta ejemplo:
    {
        "ok": true,
        "result": {
            "sesion_id": 123,
            "procesados": 3,
            "detalles": [
                "Alumno 1: ausencia registrada",
                "Alumno 2: presente (sin cambios)",
                "Alumno 3: ausencia registrada"
            ]
        }
    }
    """
    _load_tables()
    
    payload = request.get_json() or {}
    
    alumnos = payload.get('alumnos', [])
    
    if not isinstance(alumnos, list):
        return jsonify({'ok': False, 'error': 'alumnos debe ser un array'}), 400
    
    # Validar estructura de cada alumno
    for a in alumnos:
        if not isinstance(a, dict) or 'alumno_id' not in a or 'ausente' not in a:
            return jsonify({'ok': False, 'error': 'Cada alumno debe tener alumno_id y ausente (true/false)'}), 400
    
    # Verificar que la sesión existe
    with db.engine.connect() as conn:
        sesion = conn.execute(
            select(sesiones).where(sesiones.c.id == sesion_id)
        ).mappings().fetchone()
        
        if not sesion:
            return jsonify({'ok': False, 'error': 'Sesión no encontrada'}), 404
    
    # Verificar permisos
    perm_result = can_pasar_lista(current_user, {'sesion_id': sesion_id})
    
    if not perm_result['allowed']:
        # Verificar si es el profesor asignado
        if 'profesor_academia' in current_user['roles']:
            with db.engine.connect() as conn:
                cp = conn.execute(
                    select(curso_profesores).where(
                        and_(
                            curso_profesores.c.id == sesion['curso_profesor_id'],
                            curso_profesores.c.usuario_id == current_user['usuario_id'],
                            curso_profesores.c.fecha_baja.is_(None)
                        )
                    )
                ).mappings().fetchone()
                
                if not cp:
                    return jsonify({'ok': False, 'error': 'No autorizado para pasar lista en esta sesión'}), 403
        else:
            return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    # Obtener curso_id y curso_profesor_id de la sesión
    with db.engine.connect() as conn:
        horario = conn.execute(
            select(horarios_curso).where(horarios_curso.c.id == sesion['horario_curso_id'])
        ).mappings().fetchone()
        
        if not horario:
            return jsonify({'ok': False, 'error': 'Horario de curso no encontrado'}), 500
        
        curso_id = horario['curso_id']
        curso_profesor_id = sesion['curso_profesor_id']
    
    # Procesar cada alumno
    resultados = []
    errores = []
    
    try:
        with db.engine.begin() as conn:
            for item in alumnos:
                alumno_id = item['alumno_id']
                ausente = item['ausente']
                
                # Verificar que el alumno está inscrito en el curso
                inscripcion = conn.execute(
                    select(inscripciones).where(
                        and_(
                            inscripciones.c.alumno_id == alumno_id,
                            inscripciones.c.curso_id == curso_id,
                            inscripciones.c.fecha_fin.is_(None)  # Inscripción activa
                        )
                    )
                ).mappings().fetchone()
                
                if not inscripcion:
                    errores.append(f'Alumno {alumno_id} no está inscrito en el curso')
                    continue
                
                inscripcion_id = inscripcion['id']
                
                # Buscar anotación de ausencia existente
                anotacion_existente = conn.execute(
                    select(anotaciones).where(
                        and_(
                            anotaciones.c.sesion_id == sesion_id,
                            anotaciones.c.alumno_id == alumno_id,
                            anotaciones.c.tipo_anotacion == 'Ausencia',
                            anotaciones.c.timestamp_baja.is_(None)
                        )
                    )
                ).mappings().fetchone()
                
                if ausente:
                    # ALUMNO AUSENTE: crear o reactivar anotación
                    if anotacion_existente:
                        # Ya existe, no hacer nada (o actualizar timestamp si lo deseas)
                        resultados.append(f'Alumno {alumno_id}: ausencia ya registrada')
                    else:
                        # Crear nueva anotación de ausencia
                        insert_stmt = anotaciones.insert().values(
                            sesion_id=sesion_id,
                            inscripcion_id=inscripcion_id,
                            curso_id=curso_id,
                            curso_profesor_id=curso_profesor_id,
                            alumno_id=alumno_id,
                            tipo_anotacion='Ausencia',
                            texto='Ausente',
                            timestamp_alta=datetime.now()
                        )
                        conn.execute(insert_stmt)
                        resultados.append(f'Alumno {alumno_id}: ausencia registrada')
                else:
                    # ALUMNO NO AUSENTE: eliminar anotación si existe
                    if anotacion_existente:
                        # Soft delete de la anotación
                        delete_stmt = anotaciones.update().where(
                            anotaciones.c.id == anotacion_existente['id']
                        ).values(
                            timestamp_baja=datetime.now(),
                            motivo_baja='Alumno presente'
                        )
                        conn.execute(delete_stmt)
                        resultados.append(f'Alumno {alumno_id}: anotación de ausencia eliminada')
                    else:
                        # No había anotación, alumno presente (no hacer nada)
                        resultados.append(f'Alumno {alumno_id}: presente (sin cambios)')
        
        response = {
            'ok': True,
            'result': {
                'sesion_id': sesion_id,
                'procesados': len(alumnos),
                'detalles': resultados
            }
        }
        
        if errores:
            response['result']['errores'] = errores
        
        logger.info(f"Asistencia registrada para sesión {sesion_id}: {len(alumnos)} alumnos procesados")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error al pasar lista en sesión {sesion_id}: {str(e)}")
        return jsonify({'ok': False, 'error': str(e)}), 500
