"""Rutas Flask para gestión de Alumnos."""
from flask import Blueprint, jsonify, request, g
from webargs.flaskparser import use_args
from webargs import fields
from datetime import datetime

from src.shared.middleware.auth import require_auth
from src.shared.application.permissions import (
    can_query_alumnos,
    can_create_alumno,
    can_view_alumno,
    can_modify_alumno,
    can_delete_alumno
)
from src.shared.docs.operation_id import operation_id
from src.shared.docs.openapi_args import openapi_query_args
from src.shared.pagination import clamp_pagination, build_page_envelope, DEFAULT_PAGE, DEFAULT_SIZE, MAX_PAGE_SIZE
from src.shared.database import db
from src.schemas.alumno import (
    AlumnoSchema,
    AlumnoCreateSchema,
    AlumnoUpdateSchema
)
import logging

logger = logging.getLogger(__name__)

from sqlalchemy import Table, MetaData, select, and_, func
metadata = MetaData()

# Lazy loading de tablas
_tables_loaded = False
alumnos = None
academias = None
inscripciones = None
cursos = None
curso_profesores = None

def _load_tables():
    """Carga las tablas de forma lazy al primer uso."""
    global _tables_loaded, alumnos, academias, inscripciones, cursos, curso_profesores
    if not _tables_loaded:
        alumnos = Table('alumno', metadata, autoload_with=db.engine)
        academias = Table('academia', metadata, autoload_with=db.engine)
        inscripciones = Table('inscripcion', metadata, autoload_with=db.engine)
        cursos = Table('curso', metadata, autoload_with=db.engine)
        curso_profesores = Table('curso_profesores', metadata, autoload_with=db.engine)
        _tables_loaded = True

alumnos_bp = Blueprint('alumnos', __name__)

# Definición de parámetros de query para GET /alumnos/
alumnos_list_query_args = {
    'academia_id': fields.Int(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Filtrar por ID de academia',
            'example': 1
        }
    ),
    'nombre': fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Buscar por nombre (coincidencia parcial)',
            'example': 'Juan'
        }
    ),
    'nombre_contains': fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Buscar por nombre (coincidencia parcial - alias de nombre)',
            'example': 'Pérez'
        }
    ),
    'email': fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Buscar por email exacto',
            'example': 'juan.perez@email.com'
        }
    ),
    'email_contains': fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Buscar por email (coincidencia parcial)',
            'example': '@email.com'
        }
    ),
    'dni': fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Buscar por DNI exacto',
            'example': '12345678A'
        }
    ),
    'curso_id': fields.Int(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Filtrar alumnos inscritos en un curso específico',
            'example': 5
        }
    ),
    'page': fields.Int(
        required=False,
        allow_none=True,
        load_default=DEFAULT_PAGE,
        metadata={
            'description': f'Número de página (por defecto {DEFAULT_PAGE})',
            'example': 1
        }
    ),
    'size': fields.Int(
        required=False,
        allow_none=True,
        load_default=DEFAULT_SIZE,
        metadata={
            'description': f'Tamaño de página (por defecto {DEFAULT_SIZE}, máximo {MAX_PAGE_SIZE})',
            'example': 20
        }
    ),
    'with_total': fields.Bool(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Incluir conteo total de registros (puede ser costoso)',
            'example': True
        }
    ),
    'order_by': fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Campo por el que ordenar (id, nombre, email, fecha_nacimiento)',
            'example': 'nombre'
        }
    ),
    'order_dir': fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Dirección de ordenamiento (asc o desc)',
            'example': 'asc'
        }
    ),
    'expand': fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Expandir relaciones: "academia" (añade objeto academia con id y nombre)',
            'example': 'academia'
        }
    ),
}


@alumnos_bp.route('/', methods=['GET'])
@require_auth
@operation_id('alumnos.listar_alumnos')
@openapi_query_args(alumnos_list_query_args)
def listar_alumnos():
    """
    Lista alumnos con filtros opcionales y paginación.
    
    Permisos:
    - admin_plataforma: Ve todos los alumnos de todas las academias
    - admin_academia: Ve solo alumnos de su academia
    - profesor_academia: Ve solo alumnos inscritos en sus cursos
    
    Filtros disponibles:
    - academia_id: Filtrar por academia
    - nombre/nombre_contains: Buscar por nombre
    - email/email_contains: Buscar por email
    - dni: Buscar por DNI exacto
    - curso_id: Alumnos inscritos en un curso específico
    
    Paginación:
    - page: Número de página (por defecto 1)
    - size: Tamaño de página (por defecto 20, máximo 100)
    - with_total: Incluir conteo total (true/false)
    
    Ordenamiento:
    - order_by: Campo (id, nombre, email, fecha_nacimiento)
    - order_dir: Dirección (asc, desc)
    
    Expansión de relaciones:
    - expand=academia: Incluye objeto academia completo
    """
    _load_tables()
    
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'ok': False, 'error': 'user_not_authenticated'}), 401
    
    # Parsear parámetros
    params = {
        'academia_id': request.args.get('academia_id'),
        'nombre': request.args.get('nombre'),
        'nombre_contains': request.args.get('nombre_contains'),
        'email': request.args.get('email'),
        'email_contains': request.args.get('email_contains'),
        'dni': request.args.get('dni'),
        'curso_id': request.args.get('curso_id'),
        'page': request.args.get('page'),
        'size': request.args.get('size'),
        'with_total': request.args.get('with_total'),
        'order_by': request.args.get('order_by'),
        'order_dir': request.args.get('order_dir'),
    }
    
    expand_param = request.args.get('expand', '') or ''
    expand = [e.strip() for e in expand_param.split(',') if e.strip()]
    
    # Verificar permisos
    perm_result = can_query_alumnos(user, params)
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    enforced_filters = perm_result.get('enforced_filters', {})
    
    # Construir query base
    query = select(alumnos)
    
    # Si es profesor, solo ve alumnos de sus cursos
    user_role = user.rol.nombre if hasattr(user, 'rol') and user.rol else None
    if user_role == 'Profesor_academia':
        query = query.select_from(
            alumnos
            .join(inscripciones, alumnos.c.id == inscripciones.c.alumno_id)
            .join(cursos, inscripciones.c.curso_id == cursos.c.id)
            .join(curso_profesores,
                  and_(
                      curso_profesores.c.curso_id == cursos.c.id,
                      curso_profesores.c.usuario_id == user.id,
                      curso_profesores.c.fecha_baja.is_(None)
                  ))
        ).distinct()
    
    # Aplicar filtros forzados por permisos
    if 'academia_id' in enforced_filters:
        query = query.where(alumnos.c.academia_id == enforced_filters['academia_id'])
    
    # Aplicar filtros opcionales
    if params.get('academia_id'):
        try:
            aid = int(params['academia_id'])
            query = query.where(alumnos.c.academia_id == aid)
        except ValueError:
            return jsonify({'ok': False, 'error': 'invalid_academia_id'}), 400
    
    # Filtro por curso
    if params.get('curso_id'):
        try:
            cid = int(params['curso_id'])
            query = query.join(inscripciones, alumnos.c.id == inscripciones.c.alumno_id)
            query = query.where(inscripciones.c.curso_id == cid)
        except ValueError:
            return jsonify({'ok': False, 'error': 'invalid_curso_id'}), 400
    
    # Filtros de texto
    nombre_contains = params.get('nombre_contains') or params.get('nombre')
    if nombre_contains:
        query = query.where(alumnos.c.nombre.ilike(f"%{nombre_contains}%"))
    
    email_exact = params.get('email')
    email_like = params.get('email_contains')
    if email_exact:
        query = query.where(alumnos.c.email == email_exact)
    elif email_like:
        query = query.where(alumnos.c.email.ilike(f"%{email_like}%"))
    
    if params.get('dni'):
        query = query.where(alumnos.c.dni == params['dni'])
    
    # Paginación
    try:
        parsed_page = int(params['page']) if params.get('page') else None
    except (ValueError, TypeError):
        parsed_page = None
    try:
        parsed_size = int(params['size']) if params.get('size') else None
    except (ValueError, TypeError):
        parsed_size = None
    
    page, size = clamp_pagination(parsed_page, parsed_size)
    with_total = params.get('with_total') in ('1', 'true', 'True', True)
    
    # Ordenamiento
    ORDER_WHITELIST = {'id', 'nombre', 'email', 'fecha_nacimiento'}
    order_by = params.get('order_by') if params.get('order_by') in ORDER_WHITELIST else 'id'
    order_dir = params.get('order_dir') if params.get('order_dir') in ('asc', 'desc') else 'asc'
    
    # Aplicar ordenamiento
    order_col = alumnos.c[order_by] if order_by in alumnos.c else alumnos.c.id
    if order_dir == 'asc':
        query = query.order_by(order_col.asc(), alumnos.c.id.asc())
    else:
        query = query.order_by(order_col.desc(), alumnos.c.id.desc())
    
    # Ejecutar query con LIMIT+1 para detectar has_more
    offset = (page - 1) * size
    
    try:
        with db.engine.connect() as conn:
            rows = conn.execute(query.offset(offset).limit(size + 1)).mappings().fetchall()
            
            # Determinar has_more
            has_more = len(rows) > size
            rows = rows[:size]
            
            # Serializar resultados
            schema = AlumnoSchema(many=True)
            result = schema.dump(rows)
            
            # Expandir academia si se solicita
            if 'academia' in expand:
                for item in result:
                    if item.get('academia_id'):
                        acad = conn.execute(
                            select(academias).where(academias.c.id == item['academia_id'])
                        ).mappings().fetchone()
                        if acad:
                            item['academia'] = {'id': acad['id'], 'nombre': acad['nombre']}
                        else:
                            item['academia'] = None
                    else:
                        item['academia'] = None
            
            # Calcular total si se solicita
            total = None
            if with_total:
                count_query = select(alumnos.c.id)
                # Aplicar los mismos filtros que la query principal
                if 'academia_id' in enforced_filters:
                    count_query = count_query.where(alumnos.c.academia_id == enforced_filters['academia_id'])
                if params.get('academia_id'):
                    count_query = count_query.where(alumnos.c.academia_id == int(params['academia_id']))
                if nombre_contains:
                    count_query = count_query.where(alumnos.c.nombre.ilike(f"%{nombre_contains}%"))
                if email_exact:
                    count_query = count_query.where(alumnos.c.email == email_exact)
                elif email_like:
                    count_query = count_query.where(alumnos.c.email.ilike(f"%{email_like}%"))
                if params.get('dni'):
                    count_query = count_query.where(alumnos.c.dni == params['dni'])
                
                total = conn.execute(select([func.count()]).select_from(count_query.alias())).scalar()
            
            envelope = build_page_envelope(result, page, size, with_total=with_total, total=total)
            return jsonify(envelope), 200
            
    except Exception as e:
        logger.error(f"Error al listar alumnos: {str(e)}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@alumnos_bp.route('/', methods=['POST'])
@require_auth
@operation_id('alumnos.crear_alumno')
def crear_alumno():
    """
    Crea un nuevo alumno.
    
    Permisos:
    - admin_plataforma: Puede crear alumnos en cualquier academia
    - admin_academia: Puede crear alumnos solo en su academia
    
    Campos obligatorios:
    - nombre: Nombre completo del alumno
    - email: Email único (se valida que no exista)
    - dni: DNI/NIE (formato español: 12345678A o X1234567A)
    - telefono: Teléfono de contacto
    - fecha_nacimiento: Fecha de nacimiento
    - direccion: Dirección completa
    - academia_id: ID de la academia (obligatorio para admin_plataforma)
    
    Campos obligatorios si es menor de edad (<18 años):
    - nombre_tutor: Nombre completo del tutor
    - telefono_tutor: Teléfono del tutor
    - relaccion_tutor_alumno: Relación (Padre, Madre, Tutor legal, etc.)
    - email_tutor: Email del tutor (opcional)
    
    Ejemplo de request:
    ```json
    {
        "academia_id": 1,
        "nombre": "Juan Pérez García",
        "email": "juan.perez@email.com",
        "dni": "12345678A",
        "telefono": "+34 600123456",
        "fecha_nacimiento": "2005-03-15",
        "direccion": "Calle Mayor 123, 28001 Madrid",
        "nombre_tutor": "María García López",
        "relaccion_tutor_alumno": "Madre",
        "telefono_tutor": "+34 600654321",
        "email_tutor": "maria.garcia@email.com"
    }
    ```
    """
    _load_tables()
    
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'ok': False, 'error': 'user_not_authenticated'}), 401
    
    try:
        schema = AlumnoCreateSchema()
        payload = schema.load(request.get_json() or {})
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Validation error: {str(e)}'}), 400
    
    perm_result = can_create_alumno(user, payload)
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    sanitized = perm_result.get('sanitized_payload', payload)
    
    # Validar que academia_id existe y está activa
    with db.engine.connect() as conn:
        academia = conn.execute(
            select(academias).where(academias.c.id == sanitized['academia_id'])
        ).mappings().fetchone()
        
        if not academia:
            return jsonify({'ok': False, 'error': 'academia_id no existe'}), 404
        
        # Verificar email único
        alumno_existente = conn.execute(
            select(alumnos).where(alumnos.c.email == sanitized['email'])
        ).mappings().fetchone()
        
        if alumno_existente:
            return jsonify({'ok': False, 'error': 'El email ya está registrado'}), 409
    
    try:
        insert_stmt = alumnos.insert().values(**sanitized)
        
        with db.engine.connect() as conn:
            result = conn.execute(insert_stmt)
            conn.commit()
            alumno_id = result.inserted_primary_key[0]
            
            alumno = conn.execute(
                select(alumnos).where(alumnos.c.id == alumno_id)
            ).mappings().fetchone()
            
            schema = AlumnoSchema()
            logger.info(f"Alumno creado: ID={alumno_id}, email={sanitized['email']}, academia_id={sanitized['academia_id']}")
            return jsonify({'ok': True, 'result': schema.dump(alumno)}), 201
    except Exception as e:
        logger.error(f"Error al crear alumno: {str(e)}")
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@alumnos_bp.route('/<int:alumno_id>', methods=['GET'])
@require_auth
@operation_id('alumnos.obtener_alumno')
def obtener_alumno(alumno_id):
    """
    Obtiene un alumno por ID.
    
    Permisos:
    - admin_plataforma: Puede ver cualquier alumno
    - admin_academia: Puede ver alumnos de su academia
    - profesor_academia: Puede ver alumnos inscritos en sus cursos
    
    Query params opcionales:
    - expand: "academia" para incluir objeto academia completo
    
    Ejemplo de respuesta con expand=academia:
    ```json
    {
        "ok": true,
        "result": {
            "id": 1,
            "academia_id": 1,
            "academia": {
                "id": 1,
                "nombre": "Academia Central"
            },
            "nombre": "Juan Pérez García",
            "email": "juan.perez@email.com",
            "dni": "12345678A",
            "telefono": "+34 600123456",
            "fecha_nacimiento": "2005-03-15",
            "direccion": "Calle Mayor 123, 28001 Madrid"
        }
    }
    ```
    """
    _load_tables()
    
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'ok': False, 'error': 'user_not_authenticated'}), 401
    
    expand_param = request.args.get('expand', '') or ''
    expand = [e.strip() for e in expand_param.split(',') if e.strip()]
    
    with db.engine.connect() as conn:
        alumno = conn.execute(
            select(alumnos).where(alumnos.c.id == alumno_id)
        ).mappings().fetchone()
        
        if not alumno:
            return jsonify({'ok': False, 'error': 'Alumno no encontrado'}), 404
    
    perm_result = can_view_alumno(user, dict(alumno))
    
    if not perm_result['allowed']:
        # Verificar si el profesor tiene al alumno en sus cursos
        user_role = user.rol.nombre if hasattr(user, 'rol') and user.rol else None
        if user_role == 'Profesor_academia':
            with db.engine.connect() as conn:
                inscripcion = conn.execute(
                    select(inscripciones)
                    .select_from(
                        inscripciones
                        .join(cursos, inscripciones.c.curso_id == cursos.c.id)
                        .join(curso_profesores,
                              and_(
                                  curso_profesores.c.curso_id == cursos.c.id,
                                  curso_profesores.c.usuario_id == user.id,
                                  curso_profesores.c.fecha_baja.is_(None)
                              ))
                    )
                    .where(inscripciones.c.alumno_id == alumno_id)
                ).mappings().fetchone()
                
                if not inscripcion:
                    return jsonify({'ok': False, 'error': 'No autorizado para ver este alumno'}), 403
        else:
            return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    schema = AlumnoSchema()
    result = schema.dump(alumno)
    
    # Expandir academia si se solicita
    if 'academia' in expand and result.get('academia_id'):
        with db.engine.connect() as conn:
            acad = conn.execute(
                select(academias).where(academias.c.id == result['academia_id'])
            ).mappings().fetchone()
            if acad:
                result['academia'] = {'id': acad['id'], 'nombre': acad['nombre']}
            else:
                result['academia'] = None
    
    return jsonify({'ok': True, 'result': result}), 200


@alumnos_bp.route('/<int:alumno_id>', methods=['PATCH', 'PUT'])
@require_auth
@operation_id('alumnos.actualizar_alumno')
def actualizar_alumno(alumno_id):
    """
    Actualiza un alumno existente (actualización parcial).
    
    Permisos:
    - admin_plataforma: Puede actualizar cualquier alumno
    - admin_academia: Puede actualizar alumnos de su academia
    
    Campos actualizables:
    - nombre: Nombre completo
    - email: Email (se valida unicidad)
    - dni: DNI/NIE
    - telefono: Teléfono
    - fecha_nacimiento: Fecha de nacimiento
    - direccion: Dirección
    - nombre_tutor, relaccion_tutor_alumno, telefono_tutor, email_tutor: Datos del tutor
    
    Campos NO actualizables:
    - academia_id: No se puede cambiar la academia de un alumno
    - id: Inmutable
    
    Ejemplo de request:
    ```json
    {
        "telefono": "+34 600999888",
        "direccion": "Nueva Dirección 456, 28002 Madrid"
    }
    ```
    
    Nota: Solo se deben enviar los campos que se desean actualizar.
    """
    _load_tables()
    
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'ok': False, 'error': 'user_not_authenticated'}), 401
    
    with db.engine.connect() as conn:
        alumno = conn.execute(
            select(alumnos).where(alumnos.c.id == alumno_id)
        ).mappings().fetchone()
        
        if not alumno:
            return jsonify({'ok': False, 'error': 'Alumno no encontrado'}), 404
    
    try:
        schema = AlumnoUpdateSchema()
        payload = schema.load(request.get_json() or {})
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Validation error: {str(e)}'}), 400
    
    perm_result = can_modify_alumno(user, dict(alumno), payload)
    
    if not perm_result['allowed']:
        return jsonify({'ok': False, 'error': perm_result.get('reason', 'No autorizado')}), 403
    
    sanitized = perm_result.get('sanitized_payload', payload)
    
    if not sanitized:
        return jsonify({'ok': False, 'error': 'No hay campos para actualizar'}), 400
    
    # Validar email único si se cambia
    if 'email' in sanitized:
        with db.engine.connect() as conn:
            alumno_existente = conn.execute(
                select(alumnos).where(
                    and_(
                        alumnos.c.email == sanitized['email'],
                        alumnos.c.id != alumno_id
                    )
                )
            ).mappings().fetchone()
            
            if alumno_existente:
                return jsonify({'ok': False, 'error': 'El email ya está registrado'}), 409
    
    try:
        update_stmt = alumnos.update().where(alumnos.c.id == alumno_id).values(**sanitized)
        
        with db.engine.connect() as conn:
            conn.execute(update_stmt)
            conn.commit()
            
            alumno_updated = conn.execute(
                select(alumnos).where(alumnos.c.id == alumno_id)
            ).mappings().fetchone()
            
            schema = AlumnoSchema()
            logger.info(f"Alumno actualizado: ID={alumno_id}, campos={list(sanitized.keys())}")
            return jsonify({'ok': True, 'result': schema.dump(alumno_updated)}), 200
    except Exception as e:
        logger.error(f"Error al actualizar alumno: {str(e)}")
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@alumnos_bp.route('/<int:alumno_id>', methods=['DELETE'])
@require_auth
@operation_id('alumnos.eliminar_alumno')
def eliminar_alumno(alumno_id):
    """
    Elimina un alumno (hard delete solo si no tiene inscripciones).
    
    Permisos:
    - admin_plataforma: Puede eliminar cualquier alumno
    - admin_academia: Puede eliminar alumnos de su academia
    
    Comportamiento:
    - Si el alumno NO tiene inscripciones: Eliminación física (hard delete)
    - Si el alumno tiene inscripciones: Retorna error 409 (Conflict)
    
    Razón: Los alumnos con historial de inscripciones deben conservarse para
    mantener la integridad referencial y el historial académico.
    
    Respuesta exitosa:
    ```json
    {
        "ok": true,
        "result": "Alumno eliminado correctamente"
    }
    ```
    
    Error si tiene inscripciones:
    ```json
    {
        "ok": false,
        "error": "No se puede eliminar el alumno porque tiene inscripciones asociadas"
    }
    ```
    """
    _load_tables()
    
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'ok': False, 'error': 'user_not_authenticated'}), 401
    
    with db.engine.connect() as conn:
        alumno = conn.execute(
            select(alumnos).where(alumnos.c.id == alumno_id)
        ).mappings().fetchone()
        
        if not alumno:
            return jsonify({'ok': False, 'error': 'Alumno no encontrado'}), 404
    
    perm_result = can_delete_alumno(user, dict(alumno))
    
    if not perm_result[0]:  # can_delete_alumno retorna (bool, reason)
        return jsonify({'ok': False, 'error': perm_result[1] or 'No autorizado'}), 403
    
    # Verificar si tiene inscripciones
    with db.engine.connect() as conn:
        inscripcion = conn.execute(
            select(inscripciones).where(inscripciones.c.alumno_id == alumno_id).limit(1)
        ).mappings().fetchone()
        
        if inscripcion:
            return jsonify({
                'ok': False,
                'error': 'No se puede eliminar el alumno porque tiene inscripciones asociadas'
            }), 409
    
    try:
        delete_stmt = alumnos.delete().where(alumnos.c.id == alumno_id)
        
        with db.engine.connect() as conn:
            conn.execute(delete_stmt)
            conn.commit()
            
            logger.info(f"Alumno eliminado: ID={alumno_id}")
            return jsonify({'ok': True, 'result': 'Alumno eliminado correctamente'}), 200
    except Exception as e:
        logger.error(f"Error al eliminar alumno: {str(e)}")
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500
