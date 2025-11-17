"""Rutas para gestión de Cursos."""
from flask import Blueprint, request, jsonify, g
from webargs import fields
from webargs.flaskparser import use_args
from datetime import datetime, timezone

from src.shared.pagination import clamp_pagination, DEFAULT_SIZE, MAX_PAGE_SIZE, DEFAULT_PAGE
from src.shared.docs.openapi_args import openapi_query_args
from src.shared.middleware.auth import require_auth
from src.shared.docs.operation_id import operation_id
from src.shared.application.permissions import (
    can_query_cursos,
    can_create_curso,
    can_view_curso,
    can_modify_curso,
    can_delete_curso
)
from src.academias.infrastructure.models import Curso, Academia, Tarifa
from src.profesores.infrastructure.models import CursoProfesores
from src.schemas.curso import CursoSchema, CursoCreateSchema, CursoUpdateSchema
from src.shared.database import db
from config import Config

cursos_bp = Blueprint('cursos', __name__)

# Schemas para serialización
curso_schema = CursoSchema()
cursos_schema = CursoSchema(many=True)
curso_create_schema = CursoCreateSchema()
curso_update_schema = CursoUpdateSchema()


# Query args para listar cursos
cursos_list_query_args = {
    'academia_id': fields.Int(required=False, allow_none=True),
    'nombre': fields.Str(required=False, allow_none=True),
    'nombre_contains': fields.Str(required=False, allow_none=True),
    'anio_academico': fields.Str(required=False, allow_none=True),
    'tipo_alumno': fields.Str(required=False, allow_none=True),
    'estado': fields.Str(required=False, allow_none=True),
    'acepta_nuevos_alumnos': fields.Bool(required=False, allow_none=True),
    'tarifa_id': fields.Int(required=False, allow_none=True),
    'order_by': fields.Str(required=False, allow_none=True),
    'order_direction': fields.Str(required=False, allow_none=True),
    'page': fields.Int(required=False, load_default=DEFAULT_PAGE),
    'size': fields.Int(required=False, load_default=DEFAULT_SIZE),
    'expand': fields.Str(required=False, allow_none=True, metadata={
        'description': 'Expandir relaciones. Valores: "academia", "tarifa" (separados por coma)'
    }),
}


@cursos_bp.route('/', methods=['GET'])
@require_auth
@use_args(cursos_list_query_args, location='query')
@openapi_query_args(cursos_list_query_args)
@operation_id('cursos.listar_cursos')
def listar_cursos(args):
    """Listar cursos con filtros y paginación.
    
    Filtros disponibles:
    - academia_id: ID de la academia
    - nombre: nombre exacto del curso
    - nombre_contains: búsqueda parcial por nombre
    - anio_academico: año académico (ej: 2024-2025)
    - tipo_alumno: Infantil, Juvenil, Adultos
    - estado: Activo, Inactivo, Finalizado
    - acepta_nuevos_alumnos: true/false
    - tarifa_id: ID de la tarifa asociada
    - order_by: campo para ordenar (id, nombre, anio_academico, fecha_inicio, fecha_fin, estado)
    - order_direction: asc o desc
    - expand: expandir relaciones (valores: "academia", "tarifa")
    """
    user = getattr(g, 'current_user', None)
    
    # Parsear parámetro expand
    expand_param = args.get('expand', '') or ''
    expand = [e.strip() for e in expand_param.split(',') if e.strip()]
    
    # Verificar permisos
    params = {'academia_id': args.get('academia_id')}
    allowed, effective_filters, reason = can_query_cursos(user, params)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Construir query base
    query = Curso.query
    
    # Aplicar filtro de academia_id (forzado por permisos o proporcionado)
    if 'academia_id' in effective_filters:
        query = query.filter(Curso.academia_id == effective_filters['academia_id'])
    
    # Filtro especial para profesores: solo cursos asignados
    if 'profesor_id' in effective_filters:
        profesor_id = effective_filters['profesor_id']
        # Join con CursoProfesores para filtrar cursos asignados al profesor
        query = query.join(CursoProfesores, Curso.id == CursoProfesores.curso_id)
        query = query.filter(
            CursoProfesores.usuario_id == profesor_id,
            CursoProfesores.fecha_baja.is_(None)  # Solo relaciones activas
        )
    
    # Filtros adicionales
    nombre_exact = args.get('nombre')
    nombre_contains = args.get('nombre_contains')
    
    if nombre_exact:
        query = query.filter(Curso.nombre == nombre_exact)
    elif nombre_contains:
        try:
            query = query.filter(Curso.nombre.ilike(f"%{nombre_contains}%"))
        except Exception:
            query = query.filter(Curso.nombre.like(f"%{nombre_contains}%"))
    
    if args.get('anio_academico'):
        query = query.filter(Curso.anio_academico == args.get('anio_academico'))
    
    if args.get('tipo_alumno'):
        query = query.filter(Curso.tipo_alumno == args.get('tipo_alumno'))
    
    if args.get('estado'):
        query = query.filter(Curso.estado == args.get('estado'))
    
    if args.get('acepta_nuevos_alumnos') is not None:
        query = query.filter(Curso.acepta_nuevos_alumnos == args.get('acepta_nuevos_alumnos'))
    
    if args.get('tarifa_id'):
        query = query.filter(Curso.tarifa_id == args.get('tarifa_id'))
    
    # Ordenación
    order_by = args.get('order_by', 'id')
    order_direction = args.get('order_direction', 'asc').lower()
    
    # Validar campo de ordenación
    valid_order_fields = ['id', 'nombre', 'anio_academico', 'fecha_inicio', 'fecha_fin', 'estado', 'academia_id']
    if order_by not in valid_order_fields:
        order_by = 'id'
    
    if order_direction not in ['asc', 'desc']:
        order_direction = 'asc'
    
    # Aplicar ordenación
    order_column = getattr(Curso, order_by)
    if order_direction == 'desc':
        query = query.order_by(order_column.desc())
    else:
        query = query.order_by(order_column.asc())
    
    # Paginación
    page, size = clamp_pagination(args.get('page'), args.get('size'))
    offset = (max(page, 1) - 1) * max(size, 1)
    
    cursos = query.offset(offset).limit(size).all()
    
    # Serializar cursos
    result = []
    for curso in cursos:
        item = curso_schema.dump(curso)
        
        # Expandir academia si se solicita
        if 'academia' in expand and curso.academia_id:
            academia = db.session.get(Academia, curso.academia_id)
            if academia:
                item['academia'] = {
                    'id': academia.id,
                    'nombre': academia.nombre
                }
        
        # Expandir tarifa si se solicita
        if 'tarifa' in expand and curso.tarifa_id:
            tarifa = db.session.get(Tarifa, curso.tarifa_id)
            if tarifa:
                item['tarifa'] = {
                    'id': tarifa.id,
                    'descripcion': tarifa.descripcion,
                    'precio_base': tarifa.precio_base
                }
        
        result.append(item)
    
    return jsonify({"ok": True, "result": result}), 200


@cursos_bp.route('/', methods=['POST'])
@require_auth
@operation_id('cursos.crear_curso')
def crear_curso():
    """Crear un nuevo curso.
    
    Body JSON:
    - academia_id: ID de la academia (obligatorio para admin_plataforma, opcional para admin_academia)
    - nombre: Nombre del curso (obligatorio)
    - anio_academico: Año académico en formato YYYY-YYYY (obligatorio)
    - fecha_inicio: Fecha de inicio (obligatorio)
    - fecha_fin: Fecha de finalización (obligatorio, debe ser posterior a fecha_inicio)
    - capacidad_maxima: Capacidad máxima (obligatorio, > 0)
    - tarifa_id: ID de la tarifa (obligatorio)
    - tipo_alumno: Infantil, Juvenil o Adultos (obligatorio)
    - estado: Activo, Inactivo o Finalizado (obligatorio)
    - acepta_nuevos_alumnos: true/false (opcional, por defecto true)
    """
    user = getattr(g, 'current_user', None)
    
    # Parsear y validar payload
    data = request.get_json() or {}
    errors = curso_create_schema.validate(data)
    if errors:
        return jsonify({"ok": False, "error": "validation_error", "details": errors}), 400
    
    # Verificar permisos y obtener payload efectivo
    allowed, effective_payload, reason = can_create_curso(user, data)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Validar que la academia existe y está activa
    academia_id = effective_payload.get('academia_id')
    academia = db.session.get(Academia, academia_id)
    if not academia:
        return jsonify({"ok": False, "error": "not_found", "message": "academia_not_found"}), 404
    if academia.fecha_baja is not None:
        return jsonify({"ok": False, "error": "invalid_state", "message": "academia_inactive"}), 400
    
    # Validar que la tarifa existe, está activa y pertenece a la misma academia
    tarifa_id = effective_payload.get('tarifa_id')
    tarifa = db.session.get(Tarifa, tarifa_id)
    if not tarifa:
        return jsonify({"ok": False, "error": "not_found", "message": "tarifa_not_found"}), 404
    if tarifa.fecha_baja is not None:
        return jsonify({"ok": False, "error": "invalid_state", "message": "tarifa_inactive"}), 400
    if tarifa.academia_id != academia_id:
        return jsonify({"ok": False, "error": "invalid_state", "message": "tarifa_academia_mismatch"}), 400
    
    # Crear curso
    try:
        curso = Curso(
            academia_id=effective_payload['academia_id'],
            nombre=effective_payload['nombre'].strip(),
            anio_academico=effective_payload['anio_academico'],
            fecha_inicio=effective_payload['fecha_inicio'],
            fecha_fin=effective_payload['fecha_fin'],
            acepta_nuevos_alumnos=effective_payload.get('acepta_nuevos_alumnos', True),
            capacidad_maxima=effective_payload['capacidad_maxima'],
            tarifa_id=effective_payload['tarifa_id'],
            tipo_alumno=effective_payload['tipo_alumno'],
            estado=effective_payload['estado']
        )
        db.session.add(curso)
        db.session.commit()
        
        result = curso_schema.dump(curso)
        return jsonify({"ok": True, "result": result}), 201
    except Exception as e:
        db.session.rollback()
        if Config.DEBUG:
            print(f"[ERROR] crear_curso: {e}")
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500


@cursos_bp.route('/<int:curso_id>', methods=['GET'])
@require_auth
@operation_id('cursos.obtener_curso')
def obtener_curso(curso_id):
    """Obtener un curso por ID."""
    user = getattr(g, 'current_user', None)
    
    curso = db.session.get(Curso, curso_id)
    if not curso:
        return jsonify({"ok": False, "error": "not_found"}), 404
    
    # Verificar permisos
    allowed, _, reason = can_view_curso(user, curso)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Para profesores, verificar que están asignados al curso
    try:
        user_role = user.rol.nombre.strip().lower() if user and user.rol else None
    except Exception:
        user_role = None
    
    if user_role == 'profesor_academia':
        asignacion = CursoProfesores.query.filter(
            CursoProfesores.curso_id == curso_id,
            CursoProfesores.usuario_id == user.id,
            CursoProfesores.fecha_baja.is_(None)
        ).first()
        if not asignacion:
            return jsonify({"ok": False, "error": "forbidden", "reason": "not_assigned_to_course"}), 403
    
    result = curso_schema.dump(curso)
    return jsonify({"ok": True, "result": result}), 200


@cursos_bp.route('/<int:curso_id>', methods=['PUT', 'PATCH'])
@require_auth
@operation_id({'put': 'cursos.actualizar_curso_put', 'patch': 'cursos.actualizar_curso_patch'})
def actualizar_curso(curso_id):
    """Actualizar un curso.
    
    Body JSON (campos opcionales):
    - nombre: Nuevo nombre
    - anio_academico: Nuevo año académico
    - fecha_inicio: Nueva fecha de inicio
    - fecha_fin: Nueva fecha de finalización
    - acepta_nuevos_alumnos: true/false
    - capacidad_maxima: Nueva capacidad máxima (> 0)
    - tarifa_id: Nuevo ID de tarifa
    - tipo_alumno: Nuevo tipo de alumno
    - estado: Nuevo estado
    """
    user = getattr(g, 'current_user', None)
    
    curso = db.session.get(Curso, curso_id)
    if not curso:
        return jsonify({"ok": False, "error": "not_found"}), 404
    
    # Parsear y validar payload
    data = request.get_json() or {}
    errors = curso_update_schema.validate(data)
    if errors:
        return jsonify({"ok": False, "error": "validation_error", "details": errors}), 400
    
    # Verificar permisos y obtener campos permitidos
    allowed, sanitized_payload, reason = can_modify_curso(user, curso, data)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Si se cambia la tarifa, validar que existe, está activa y pertenece a la misma academia
    if 'tarifa_id' in sanitized_payload:
        tarifa = db.session.get(Tarifa, sanitized_payload['tarifa_id'])
        if not tarifa:
            return jsonify({"ok": False, "error": "not_found", "message": "tarifa_not_found"}), 404
        if tarifa.fecha_baja is not None:
            return jsonify({"ok": False, "error": "invalid_state", "message": "tarifa_inactive"}), 400
        if tarifa.academia_id != curso.academia_id:
            return jsonify({"ok": False, "error": "invalid_state", "message": "tarifa_academia_mismatch"}), 400
    
    # Actualizar campos permitidos
    try:
        for field in ['nombre', 'anio_academico', 'fecha_inicio', 'fecha_fin', 
                      'acepta_nuevos_alumnos', 'capacidad_maxima', 'tarifa_id', 
                      'tipo_alumno', 'estado']:
            if field in sanitized_payload:
                if field == 'nombre':
                    setattr(curso, field, sanitized_payload[field].strip())
                else:
                    setattr(curso, field, sanitized_payload[field])
        
        db.session.add(curso)
        db.session.commit()
        
        result = curso_schema.dump(curso)
        return jsonify({"ok": True, "result": result}), 200
    except Exception as e:
        db.session.rollback()
        if Config.DEBUG:
            print(f"[ERROR] actualizar_curso: {e}")
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500


@cursos_bp.route('/<int:curso_id>', methods=['DELETE'])
@require_auth
@operation_id('cursos.eliminar_curso')
def eliminar_curso(curso_id):
    """Eliminar (soft-delete) un curso.
    
    Nota: Los cursos no tienen campo fecha_baja en el modelo actual.
    Se cambiará el estado a 'Finalizado' como eliminación lógica.
    Solo se permite si no tiene inscripciones activas.
    """
    user = getattr(g, 'current_user', None)
    
    curso = db.session.get(Curso, curso_id)
    if not curso:
        return jsonify({"ok": False, "error": "not_found"}), 404
    
    # Verificar permisos
    allowed, reason = can_delete_curso(user, curso)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Validar que no hay inscripciones activas (fecha_fin = NULL)
    from src.alumnos.infrastructure.models import Inscripcion
    inscripciones_activas = Inscripcion.query.filter(
        Inscripcion.curso_id == curso_id,
        Inscripcion.fecha_fin.is_(None)
    ).count()
    
    if inscripciones_activas > 0:
        return jsonify({
            "ok": False,
            "error": "has_dependents",
            "message": "No se puede eliminar el curso porque tiene inscripciones activas",
            "details": {"inscripciones_activas": inscripciones_activas}
        }), 409
    
    # "Soft-delete": cambiar estado a Finalizado
    try:
        curso.estado = 'Finalizado'
        curso.acepta_nuevos_alumnos = False
        db.session.add(curso)
        db.session.commit()
        
        result = curso_schema.dump(curso)
        return jsonify({"ok": True, "result": result}), 200
    except Exception as e:
        db.session.rollback()
        if Config.DEBUG:
            print(f"[ERROR] eliminar_curso: {e}")
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500
