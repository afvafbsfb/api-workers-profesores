"""Rutas para gestión de Horarios de Cursos."""
from flask import Blueprint, request, jsonify, g
from webargs import fields
from webargs.flaskparser import use_args
from datetime import datetime, timezone

from src.shared.pagination import clamp_pagination, DEFAULT_SIZE, MAX_PAGE_SIZE, DEFAULT_PAGE
from src.shared.docs.openapi_args import openapi_query_args
from src.shared.middleware.auth import require_auth
from src.shared.docs.operation_id import operation_id
from src.shared.application.permissions import (
    can_query_horarios,
    can_create_horario,
    can_view_horario,
    can_modify_horario,
    can_delete_horario
)
from src.academias.infrastructure.models import HorarioCurso, Curso, Aula
from src.profesores.infrastructure.models import CursoProfesores
from src.schemas.horario_curso import HorarioCursoSchema, HorarioCursoCreateSchema, HorarioCursoUpdateSchema
from src.shared.database import db
from config import Config

horarios_bp = Blueprint('horarios', __name__)

# Schemas para serialización
horario_schema = HorarioCursoSchema()
horarios_schema = HorarioCursoSchema(many=True)
horario_create_schema = HorarioCursoCreateSchema()
horario_update_schema = HorarioCursoUpdateSchema()


# Query args para listar horarios
horarios_list_query_args = {
    'curso_id': fields.Int(required=False, allow_none=True),
    'aula_id': fields.Int(required=False, allow_none=True),
    'dia_semana': fields.Str(required=False, allow_none=True),
    'order_by': fields.Str(required=False, allow_none=True),
    'order_direction': fields.Str(required=False, allow_none=True),
    'page': fields.Int(required=False, load_default=DEFAULT_PAGE),
    'size': fields.Int(required=False, load_default=DEFAULT_SIZE),
    'expand': fields.Str(required=False, allow_none=True, metadata={
        'description': 'Expandir relaciones. Valores: "curso", "aula" (separados por coma)'
    }),
}


@horarios_bp.route('/', methods=['GET'])
@require_auth
@use_args(horarios_list_query_args, location='query')
@openapi_query_args(horarios_list_query_args)
@operation_id('horarios.listar_horarios')
def listar_horarios(args):
    """Listar horarios con filtros y paginación.
    
    Filtros disponibles:
    - curso_id: ID del curso
    - aula_id: ID del aula
    - dia_semana: Día de la semana (Lunes, Martes, etc.)
    - order_by: campo para ordenar (id, curso_id, aula_id, dia_semana, hora_inicio)
    - order_direction: asc o desc
    - expand: expandir relaciones (valores: "curso", "aula")
    """
    user = getattr(g, 'current_user', None)
    
    # Parsear parámetro expand
    expand_param = args.get('expand', '') or ''
    expand = [e.strip() for e in expand_param.split(',') if e.strip()]
    
    # Verificar permisos
    params = {}
    allowed, effective_filters, reason = can_query_horarios(user, params)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Construir query base
    query = HorarioCurso.query
    
    # Para admin_academia: filtrar por cursos de su academia
    if 'academia_id' in effective_filters:
        query = query.join(Curso, HorarioCurso.curso_id == Curso.id)
        query = query.filter(Curso.academia_id == effective_filters['academia_id'])
    
    # Para profesores: filtrar por cursos asignados
    if 'profesor_id' in effective_filters:
        profesor_id = effective_filters['profesor_id']
        query = query.join(Curso, HorarioCurso.curso_id == Curso.id)
        query = query.join(CursoProfesores, Curso.id == CursoProfesores.curso_id)
        query = query.filter(
            CursoProfesores.usuario_id == profesor_id,
            CursoProfesores.fecha_baja.is_(None)
        )
    
    # Filtros adicionales
    if args.get('curso_id'):
        query = query.filter(HorarioCurso.curso_id == args.get('curso_id'))
    
    if args.get('aula_id'):
        query = query.filter(HorarioCurso.aula_id == args.get('aula_id'))
    
    if args.get('dia_semana'):
        query = query.filter(HorarioCurso.dia_semana == args.get('dia_semana'))
    
    # Ordenación
    order_by = args.get('order_by', 'id')
    order_direction = args.get('order_direction', 'asc').lower()
    
    # Validar campo de ordenación
    valid_order_fields = ['id', 'curso_id', 'aula_id', 'dia_semana', 'hora_inicio']
    if order_by not in valid_order_fields:
        order_by = 'id'
    
    if order_direction not in ['asc', 'desc']:
        order_direction = 'asc'
    
    # Aplicar ordenación
    order_column = getattr(HorarioCurso, order_by)
    if order_direction == 'desc':
        query = query.order_by(order_column.desc())
    else:
        query = query.order_by(order_column.asc())
    
    # Paginación
    page, size = clamp_pagination(args.get('page'), args.get('size'))
    offset = (max(page, 1) - 1) * max(size, 1)
    
    horarios = query.offset(offset).limit(size).all()
    
    # Serializar horarios
    result = []
    for horario in horarios:
        item = horario_schema.dump(horario)
        
        # Expandir curso si se solicita
        if 'curso' in expand and horario.curso_id:
            curso = db.session.get(Curso, horario.curso_id)
            if curso:
                item['curso'] = {
                    'id': curso.id,
                    'nombre': curso.nombre,
                    'anio_academico': curso.anio_academico
                }
        
        # Expandir aula si se solicita
        if 'aula' in expand and horario.aula_id:
            aula = db.session.get(Aula, horario.aula_id)
            if aula:
                item['aula'] = {
                    'id': aula.id,
                    'nombre': aula.nombre,
                    'capacidad_maxima': aula.capacidad_maxima
                }
        
        result.append(item)
    
    return jsonify({"ok": True, "result": result}), 200


@horarios_bp.route('/', methods=['POST'])
@require_auth
@operation_id('horarios.crear_horario')
def crear_horario():
    """Crear un nuevo horario.
    
    Body JSON:
    - curso_id: ID del curso (obligatorio)
    - aula_id: ID del aula (obligatorio)
    - dia_semana: Día de la semana (obligatorio: Lunes, Martes, Miércoles, Jueves, Viernes, Sábado, Domingo)
    - hora_inicio: Hora de inicio en formato HH:MM:SS (obligatorio)
    - hora_fin: Hora de finalización en formato HH:MM:SS (obligatorio, debe ser posterior a hora_inicio)
    """
    user = getattr(g, 'current_user', None)
    
    # Parsear y validar payload
    data = request.get_json() or {}
    errors = horario_create_schema.validate(data)
    if errors:
        return jsonify({"ok": False, "error": "validation_error", "details": errors}), 400
    
    # Verificar permisos y obtener payload efectivo
    allowed, effective_payload, reason = can_create_horario(user, data)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Validar que el curso existe y está activo
    curso_id = effective_payload.get('curso_id')
    curso = db.session.get(Curso, curso_id)
    if not curso:
        return jsonify({"ok": False, "error": "not_found", "message": "curso_not_found"}), 404
    if curso.estado == 'Finalizado':
        return jsonify({"ok": False, "error": "invalid_state", "message": "curso_finalizado"}), 400
    
    # Para admin_academia, validar que el curso pertenece a su academia
    try:
        user_role = user.rol.nombre.strip().lower() if user and user.rol else None
    except Exception:
        user_role = None
    
    if user_role == 'admin_academia':
        if curso.academia_id != user.academia_id:
            return jsonify({"ok": False, "error": "forbidden", "reason": "curso_not_in_academia"}), 403
    
    # Validar que el aula existe y pertenece a la misma academia
    aula_id = effective_payload.get('aula_id')
    aula = db.session.get(Aula, aula_id)
    if not aula:
        return jsonify({"ok": False, "error": "not_found", "message": "aula_not_found"}), 404
    if aula.academia_id != curso.academia_id:
        return jsonify({"ok": False, "error": "invalid_state", "message": "aula_academia_mismatch"}), 400
    
    # Validar que no hay solapamiento de horarios en la misma aula y día
    hora_inicio = effective_payload.get('hora_inicio')
    hora_fin = effective_payload.get('hora_fin')
    dia_semana = effective_payload.get('dia_semana')
    
    conflictos = HorarioCurso.query.filter(
        HorarioCurso.aula_id == aula_id,
        HorarioCurso.dia_semana == dia_semana,
        HorarioCurso.hora_inicio < hora_fin,
        HorarioCurso.hora_fin > hora_inicio
    ).count()
    
    if conflictos > 0:
        return jsonify({
            "ok": False,
            "error": "schedule_conflict",
            "message": "Ya existe un horario en esta aula que se solapa con el horario solicitado"
        }), 409
    
    # Crear horario
    try:
        horario = HorarioCurso(
            curso_id=effective_payload['curso_id'],
            aula_id=effective_payload['aula_id'],
            dia_semana=effective_payload['dia_semana'],
            hora_inicio=effective_payload['hora_inicio'],
            hora_fin=effective_payload['hora_fin']
        )
        db.session.add(horario)
        db.session.commit()
        
        result = horario_schema.dump(horario)
        return jsonify({"ok": True, "result": result}), 201
    except Exception as e:
        db.session.rollback()
        if Config.DEBUG:
            print(f"[ERROR] crear_horario: {e}")
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500


@horarios_bp.route('/<int:horario_id>', methods=['GET'])
@require_auth
@operation_id('horarios.obtener_horario')
def obtener_horario(horario_id):
    """Obtener un horario por ID."""
    user = getattr(g, 'current_user', None)
    
    horario = db.session.get(HorarioCurso, horario_id)
    if not horario:
        return jsonify({"ok": False, "error": "not_found"}), 404
    
    # Verificar permisos básicos
    allowed, _, reason = can_view_horario(user, horario)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Para admin_academia, validar que el curso pertenece a su academia
    try:
        user_role = user.rol.nombre.strip().lower() if user and user.rol else None
    except Exception:
        user_role = None
    
    if user_role in ('admin_academia', 'profesor_academia'):
        curso = db.session.get(Curso, horario.curso_id)
        if not curso:
            return jsonify({"ok": False, "error": "not_found", "message": "curso_not_found"}), 404
        
        if user_role == 'admin_academia':
            if curso.academia_id != user.academia_id:
                return jsonify({"ok": False, "error": "forbidden", "reason": "curso_not_in_academia"}), 403
        
        if user_role == 'profesor_academia':
            # Verificar que el profesor está asignado al curso
            asignacion = CursoProfesores.query.filter(
                CursoProfesores.curso_id == horario.curso_id,
                CursoProfesores.usuario_id == user.id,
                CursoProfesores.fecha_baja.is_(None)
            ).first()
            if not asignacion:
                return jsonify({"ok": False, "error": "forbidden", "reason": "not_assigned_to_course"}), 403
    
    result = horario_schema.dump(horario)
    return jsonify({"ok": True, "result": result}), 200


@horarios_bp.route('/<int:horario_id>', methods=['PUT', 'PATCH'])
@require_auth
@operation_id({'put': 'horarios.actualizar_horario_put', 'patch': 'horarios.actualizar_horario_patch'})
def actualizar_horario(horario_id):
    """Actualizar un horario.
    
    Body JSON (campos opcionales):
    - aula_id: Nuevo ID del aula
    - dia_semana: Nuevo día de la semana
    - hora_inicio: Nueva hora de inicio
    - hora_fin: Nueva hora de finalización
    """
    user = getattr(g, 'current_user', None)
    
    horario = db.session.get(HorarioCurso, horario_id)
    if not horario:
        return jsonify({"ok": False, "error": "not_found"}), 404
    
    # Parsear y validar payload
    data = request.get_json() or {}
    errors = horario_update_schema.validate(data)
    if errors:
        return jsonify({"ok": False, "error": "validation_error", "details": errors}), 400
    
    # Verificar permisos y obtener campos permitidos
    allowed, sanitized_payload, reason = can_modify_horario(user, horario, data)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Para admin_academia, validar que el curso pertenece a su academia
    try:
        user_role = user.rol.nombre.strip().lower() if user and user.rol else None
    except Exception:
        user_role = None
    
    if user_role == 'admin_academia':
        curso = db.session.get(Curso, horario.curso_id)
        if not curso or curso.academia_id != user.academia_id:
            return jsonify({"ok": False, "error": "forbidden", "reason": "curso_not_in_academia"}), 403
    
    # Si se cambia el aula, validar que pertenece a la misma academia
    if 'aula_id' in sanitized_payload:
        curso = db.session.get(Curso, horario.curso_id)
        aula = db.session.get(Aula, sanitized_payload['aula_id'])
        if not aula:
            return jsonify({"ok": False, "error": "not_found", "message": "aula_not_found"}), 404
        if aula.academia_id != curso.academia_id:
            return jsonify({"ok": False, "error": "invalid_state", "message": "aula_academia_mismatch"}), 400
    
    # Actualizar campos permitidos
    try:
        for field in ['aula_id', 'dia_semana', 'hora_inicio', 'hora_fin']:
            if field in sanitized_payload:
                setattr(horario, field, sanitized_payload[field])
        
        db.session.add(horario)
        db.session.commit()
        
        result = horario_schema.dump(horario)
        return jsonify({"ok": True, "result": result}), 200
    except Exception as e:
        db.session.rollback()
        if Config.DEBUG:
            print(f"[ERROR] actualizar_horario: {e}")
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500


@horarios_bp.route('/<int:horario_id>', methods=['DELETE'])
@require_auth
@operation_id('horarios.eliminar_horario')
def eliminar_horario(horario_id):
    """Eliminar un horario.
    
    Solo se permite si no tiene sesiones asociadas.
    """
    user = getattr(g, 'current_user', None)
    
    horario = db.session.get(HorarioCurso, horario_id)
    if not horario:
        return jsonify({"ok": False, "error": "not_found"}), 404
    
    # Verificar permisos
    allowed, reason = can_delete_horario(user, horario)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403
    
    # Para admin_academia, validar que el curso pertenece a su academia
    try:
        user_role = user.rol.nombre.strip().lower() if user and user.rol else None
    except Exception:
        user_role = None
    
    if user_role == 'admin_academia':
        curso = db.session.get(Curso, horario.curso_id)
        if not curso or curso.academia_id != user.academia_id:
            return jsonify({"ok": False, "error": "forbidden", "reason": "curso_not_in_academia"}), 403
    
    # Validar que no hay sesiones asociadas
    from src.profesores.infrastructure.models import Sesion
    sesiones = Sesion.query.filter(Sesion.horario_curso_id == horario_id).count()
    
    if sesiones > 0:
        return jsonify({
            "ok": False,
            "error": "has_dependents",
            "message": "No se puede eliminar el horario porque tiene sesiones asociadas",
            "details": {"sesiones": sesiones}
        }), 409
    
    # Eliminar físicamente (los horarios no tienen fecha_baja)
    try:
        db.session.delete(horario)
        db.session.commit()
        
        return jsonify({"ok": True, "result": {"id": horario_id, "deleted": True}}), 200
    except Exception as e:
        db.session.rollback()
        if Config.DEBUG:
            print(f"[ERROR] eliminar_horario: {e}")
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500
