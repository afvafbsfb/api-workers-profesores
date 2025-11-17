"""Rutas Flask para gestión de asignaciones Curso-Profesores."""
from flask import Blueprint, jsonify, request, g
from webargs.flaskparser import use_args
from webargs import fields
from marshmallow import Schema, validates, ValidationError
from datetime import datetime

from src.shared.middleware.auth import require_auth
from src.shared.application.permissions import (
    can_query_curso_profesores,
    can_create_curso_profesor,
    can_view_curso_profesor,
    can_modify_curso_profesor,
    can_delete_curso_profesor
)
from src.shared.docs.operation_id import operation_id
from src.shared.docs.openapi_args import openapi_query_args
from src.shared.pagination import clamp_pagination, build_page_envelope, DEFAULT_PAGE, DEFAULT_SIZE, MAX_PAGE_SIZE
from src.shared.database import db
import logging

logger = logging.getLogger(__name__)

from sqlalchemy import Table, MetaData, select, and_
metadata = MetaData()

# Lazy loading de tablas
_tables_loaded = False
curso_profesores = None
cursos = None
usuarios = None

def _load_tables():
    """Carga las tablas de forma lazy al primer uso."""
    global _tables_loaded, curso_profesores, cursos, usuarios
    if not _tables_loaded:
        curso_profesores = Table('curso_profesores', metadata, autoload_with=db.engine)
        cursos = Table('curso', metadata, autoload_with=db.engine)
        usuarios = Table('usuario', metadata, autoload_with=db.engine)
        _tables_loaded = True

curso_profesores_bp = Blueprint('curso_profesores', __name__)


# Schemas simples para Curso_Profesores
class CursoProfesorSchema(Schema):
    """Schema para serialización de Curso_Profesores."""
    id = fields.Int(dump_only=True, metadata={'example': 1})
    curso_id = fields.Int(required=True, metadata={'example': 1})
    usuario_id = fields.Int(required=True, metadata={'example': 5})
    fecha_alta = fields.DateTime(dump_only=True, metadata={'example': '2024-09-01T10:00:00'})
    fecha_baja = fields.DateTime(allow_none=True, metadata={'example': None})
    fecha_ult_modificacion = fields.DateTime(dump_only=True, metadata={'example': '2024-09-01T10:00:00'})
    motivo_baja = fields.Str(allow_none=True, metadata={'example': None})


class CursoProfesorCreateSchema(Schema):
    """Schema para creación de asignación Curso-Profesor.
    
    Ejemplo de JSON para crear asignación:
    {
        "curso_id": 1,
        "usuario_id": 5
    }
    """
    curso_id = fields.Int(required=True, metadata={'example': 1, 'description': 'ID del curso'})
    usuario_id = fields.Int(required=True, metadata={'example': 5, 'description': 'ID del profesor (usuario)'})
    
    @validates('curso_id')
    def validate_curso_id(self, value, **kwargs):
        if value is None or value <= 0:
            raise ValidationError('El curso_id debe ser un número positivo.')
    
    @validates('usuario_id')
    def validate_usuario_id(self, value, **kwargs):
        if value is None or value <= 0:
            raise ValidationError('El usuario_id debe ser un número positivo.')


class CursoProfesorUpdateSchema(Schema):
    """Schema para actualización (típicamente para dar de baja).
    
    Ejemplo de JSON para dar de baja:
    {
        "fecha_baja": "2024-12-31T23:59:59",
        "motivo_baja": "Fin de contrato"
    }
    """
    fecha_baja = fields.DateTime(required=False, allow_none=True, metadata={'example': '2024-12-31T23:59:59'})
    motivo_baja = fields.Str(required=False, allow_none=True, metadata={'example': 'Fin de contrato'})


@curso_profesores_bp.route('/', methods=['GET'])
@require_auth
@operation_id('curso_profesores.listar_asignaciones')
@use_args({
    'curso_id': fields.Int(required=False),
    'usuario_id': fields.Int(required=False),
    'activas': fields.Bool(required=False, load_default=True),
    'page': fields.Int(required=False, load_default=1),
    'size': fields.Int(required=False, load_default=20)
}, location='query')
def listar_asignaciones(args, current_user):
    """Lista asignaciones de profesores a cursos."""
    page, size = clamp_pagination(args.get('page', 1), args.get('size', 20))
    
    perm_result = can_query_curso_profesores(current_user, args)
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    query = select(curso_profesores)
    
    enforced_filters = perm_result.get('enforced_filters', {})
    
    # Filtro de academia para admin_academia
    if 'academia_id' in enforced_filters:
        query = query.select_from(
            curso_profesores.join(cursos, curso_profesores.c.curso_id == cursos.c.id)
        ).where(cursos.c.academia_id == enforced_filters['academia_id'])
    
    # Si es profesor, solo ve sus propias asignaciones
    if 'profesor_academia' in current_user['roles']:
        query = query.where(curso_profesores.c.usuario_id == current_user['usuario_id'])
    
    # Filtros opcionales
    if args.get('curso_id'):
        query = query.where(curso_profesores.c.curso_id == args['curso_id'])
    
    if args.get('usuario_id'):
        query = query.where(curso_profesores.c.usuario_id == args['usuario_id'])
    
    if args.get('activas'):
        query = query.where(curso_profesores.c.fecha_baja.is_(None))
    else:
        query = query.where(curso_profesores.c.fecha_baja.isnot(None))
    
    query = query.order_by(curso_profesores.c.fecha_alta.desc())
    
    offset = (page - 1) * size
    query = query.limit(size).offset(offset)
    
    try:
        with db.engine.connect() as conn:
            rows = conn.execute(query).mappings().fetchall()
            schema = CursoProfesorSchema(many=True)
            result = schema.dump(rows)
            
            return jsonify({'ok': True, 'result': result, 'page': page, 'size': size}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@curso_profesores_bp.route('/', methods=['POST'])
@require_auth
@operation_id('curso_profesores.crear_asignacion')
def crear_asignacion(current_user):
    """Asigna un profesor a un curso."""
    try:
        schema = CursoProfesorCreateSchema()
        payload = schema.load(request.get_json() or {})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    
    perm_result = can_create_curso_profesor(current_user, payload)
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    # Validar que curso existe
    with db.engine.connect() as conn:
        curso = conn.execute(
            select(cursos).where(cursos.c.id == payload['curso_id'])
        ).mappings().fetchone()
        
        if not curso:
            return jsonify({'ok': False, 'error': 'curso_id no existe'}), 404
        
        # Si es admin_academia, validar que el curso es de su academia
        if 'admin_academia' in current_user['roles']:
            if curso['academia_id'] != current_user.get('academia_id'):
                return jsonify({'ok': False, 'error': 'El curso no pertenece a su academia'}), 403
        
        # Validar que usuario existe y tiene rol profesor_academia
        usuario = conn.execute(
            select(usuarios).where(usuarios.c.id == payload['usuario_id'])
        ).mappings().fetchone()
        
        if not usuario:
            return jsonify({'ok': False, 'error': 'usuario_id no existe'}), 404
        
        # Verificar que no existe asignación activa duplicada
        asignacion_existente = conn.execute(
            select(curso_profesores).where(
                and_(
                    curso_profesores.c.curso_id == payload['curso_id'],
                    curso_profesores.c.usuario_id == payload['usuario_id'],
                    curso_profesores.c.fecha_baja.is_(None)
                )
            )
        ).mappings().fetchone()
        
        if asignacion_existente:
            return jsonify({'ok': False, 'error': 'Ya existe una asignación activa de este profesor a este curso'}), 409
    
    try:
        insert_stmt = curso_profesores.insert().values(
            curso_id=payload['curso_id'],
            usuario_id=payload['usuario_id'],
            fecha_alta=datetime.now()
        )
        
        with db.engine.connect() as conn:
            result = conn.execute(insert_stmt)
            conn.commit()
            cp_id = result.inserted_primary_key[0]
            
            cp = conn.execute(
                select(curso_profesores).where(curso_profesores.c.id == cp_id)
            ).mappings().fetchone()
            
            schema = CursoProfesorSchema()
            return jsonify({'ok': True, 'result': schema.dump(cp)}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@curso_profesores_bp.route('/<int:cp_id>', methods=['GET'])
@require_auth
@operation_id('curso_profesores.obtener_asignacion')
def obtener_asignacion(cp_id, current_user):
    """Obtiene una asignación por ID."""
    with db.engine.connect() as conn:
        cp = conn.execute(
            select(curso_profesores).where(curso_profesores.c.id == cp_id)
        ).mappings().fetchone()
        
        if not cp:
            return jsonify({'ok': False, 'error': 'Asignación no encontrada'}), 404
    
    perm_result = can_view_curso_profesor(current_user, {'curso_profesor_id': cp_id})
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    schema = CursoProfesorSchema()
    return jsonify({'ok': True, 'result': schema.dump(cp)}), 200


@curso_profesores_bp.route('/<int:cp_id>', methods=['PATCH', 'PUT'])
@require_auth
@operation_id('curso_profesores.actualizar_asignacion')
def actualizar_asignacion(cp_id, current_user):
    """Actualiza una asignación (típicamente para dar de baja)."""
    with db.engine.connect() as conn:
        cp = conn.execute(
            select(curso_profesores).where(curso_profesores.c.id == cp_id)
        ).mappings().fetchone()
        
        if not cp:
            return jsonify({'ok': False, 'error': 'Asignación no encontrada'}), 404
    
    try:
        schema = CursoProfesorUpdateSchema()
        payload = schema.load(request.get_json() or {})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    
    perm_result = can_modify_curso_profesor(current_user, {'curso_profesor_id': cp_id, **payload})
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    sanitized = perm_result.get('sanitized_payload', payload)
    
    # Si se proporciona motivo_baja sin fecha_baja, añadir fecha actual
    if 'motivo_baja' in sanitized and sanitized['motivo_baja']:
        if 'fecha_baja' not in sanitized or not sanitized.get('fecha_baja'):
            sanitized['fecha_baja'] = datetime.now()
    
    try:
        update_stmt = curso_profesores.update().where(curso_profesores.c.id == cp_id).values(**sanitized)
        
        with db.engine.connect() as conn:
            conn.execute(update_stmt)
            conn.commit()
            
            cp_updated = conn.execute(
                select(curso_profesores).where(curso_profesores.c.id == cp_id)
            ).mappings().fetchone()
            
            schema = CursoProfesorSchema()
            return jsonify({'ok': True, 'result': schema.dump(cp_updated)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@curso_profesores_bp.route('/<int:cp_id>', methods=['DELETE'])
@require_auth
@operation_id('curso_profesores.eliminar_asignacion')
def eliminar_asignacion(cp_id, current_user):
    """Elimina (da de baja) una asignación."""
    with db.engine.connect() as conn:
        cp = conn.execute(
            select(curso_profesores).where(curso_profesores.c.id == cp_id)
        ).mappings().fetchone()
        
        if not cp:
            return jsonify({'ok': False, 'error': 'Asignación no encontrada'}), 404
    
    perm_result = can_delete_curso_profesor(current_user, {'curso_profesor_id': cp_id})
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    try:
        update_stmt = curso_profesores.update().where(curso_profesores.c.id == cp_id).values(
            fecha_baja=datetime.now(),
            motivo_baja='Eliminación manual'
        )
        
        with db.engine.connect() as conn:
            conn.execute(update_stmt)
            conn.commit()
            
            return jsonify({'ok': True, 'result': 'Asignación eliminada correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500
